import re
from aiogram import Router, types, F, Bot
from aiogram.fsm.context import FSMContext
import logging

from handlers.registration.states import RegistrationStates
from handlers.registration.utils import handle_invalid_phone, show_confirmation, validate_phone_number
from keyboards.keyboard_phone import get_phone_keyboard

router = Router()
logger = logging.getLogger(__name__)

@router.message(F.contact)
async def process_contact(message: types.Message, state: FSMContext, bot: Bot):
    logger.info("=== ОБРАБОТЧИК КОНТАКТА ВЫЗВАН ===")
    
    # Получаем текущее состояние
    current_state = await state.get_state()
    logger.info(f"Текущее состояние: {current_state}")
    
    # Проверяем, что мы в правильном состоянии для обработки контакта
    valid_states = [
        RegistrationStates.waiting_for_phone.state,
        RegistrationStates.editing_phone.state
    ]
    
    if current_state not in valid_states:
        logger.warning(f"Контакт получен в неожиданном состоянии: {current_state}")
        # Игнорируем контакт, если не в нужном состоянии
        return
    
    contact = message.contact
    logger.info(f"Контакт получен: {contact}")
    logger.info(f"Номер телефона: {contact.phone_number if contact else 'None'}")
    
    # Проверяем, что контакт существует и имеет номер
    if not contact or not contact.phone_number:
        error_text = """
    ❌ <b>Контакт не найден</b>

    Пожалуйста, убедитесь, что нажали кнопку "Отправить номер телефона"
    """
        await message.answer(
            error_text,
            parse_mode="HTML",
            reply_markup=get_phone_keyboard()
        )
        return
    
    phone = contact.phone_number
    logger.info(f"Исходный номер: '{phone}'")
    
    # Проверяем, что номер не None и не пустой
    if not phone:
        logger.warning("Номер телефона пустой")
        await handle_invalid_phone(message, state)
        return
    
    # Убираем все нецифровые символы (кроме + в начале)
    cleaned_phone = re.sub(r'[^\d+]', '', phone)
    logger.info(f"Очищенный номер: '{cleaned_phone}'")
    
    # Форматируем номер
    if cleaned_phone.startswith('+'):
        formatted_phone = cleaned_phone
    elif cleaned_phone.startswith('8'):
        formatted_phone = '+7' + cleaned_phone[1:]
    elif cleaned_phone.startswith('7'):
        formatted_phone = '+' + cleaned_phone
    else:
        formatted_phone = '+7' + cleaned_phone
    
    logger.info(f"Форматированный номер: '{formatted_phone}'")
    
    # Проверяем валидность
    if not validate_phone_number(formatted_phone):
        logger.warning(f"Номер не прошел валидацию: {formatted_phone}")
        await handle_invalid_phone(message, state)
        return
    
    await state.update_data(phone=formatted_phone)
    await show_confirmation(message, state, bot)
    logger.info("=== УСПЕШНО ОБРАБОТАН КОНТАКТ ===")

@router.message(RegistrationStates.waiting_for_name)
async def process_name(message: types.Message, state: FSMContext, bot: Bot):
    """Обработка введенного ФИО"""
    if not message.text:
        await message.answer("Пожалуйста, введите ФИО текстом:")
        return
    
    name = message.text.strip()
    
    if len(name) < 2:
        await message.answer("Пожалуйста, введите корректное ФИО (минимум 2 символа):")
        return
    
    # Сохраняем имя и ID сообщения
    data = await state.get_data()
    registration_messages = data.get('registration_messages', [])
    registration_messages.append(message.message_id)
    
    await state.update_data(name=name, registration_messages=registration_messages)
    
    # Запрашиваем телефон
    phone_message = await message.answer(
        "Отлично! Теперь введите ваш номер телефона. "
        "Вы можете использовать кнопку ниже для быстрой отправки:",
        reply_markup=get_phone_keyboard()
    )
    
    registration_messages.append(phone_message.message_id)
    await state.update_data(registration_messages=registration_messages)
    await state.set_state(RegistrationStates.waiting_for_phone)

@router.message(RegistrationStates.waiting_for_phone)
async def process_phone(message: types.Message, state: FSMContext, bot: Bot):
    # Обрабатываем ТОЛЬКО текстовый ввод
    if not message.text:
        await handle_invalid_phone(message, state)
        return
    
    phone = message.text
    
    # Дополнительная проверка на None и пустую строку
    if not phone:
        await handle_invalid_phone(message, state)
        return
    
    # ФОРМАТИРУЕМ номер перед валидацией
    cleaned_phone = re.sub(r'[^\d+]', '', phone)
    
    # Форматируем номер
    if cleaned_phone.startswith('+'):
        formatted_phone = cleaned_phone
    elif cleaned_phone.startswith('8'):
        formatted_phone = '+7' + cleaned_phone[1:]
    elif cleaned_phone.startswith('7'):
        formatted_phone = '+' + cleaned_phone
    else:
        formatted_phone = '+7' + cleaned_phone
    
    logger.info(f"Форматированный номер: {formatted_phone}")
    
    # Проверяем валидность номера
    if not validate_phone_number(formatted_phone):
        await handle_invalid_phone(message, state)
        return
    
    # Если номер валиден, сохраняем и показываем подтверждение
    await state.update_data(phone=formatted_phone)
    await show_confirmation(message, state, bot)

@router.message(RegistrationStates.editing_name)
async def process_edited_name(message: types.Message, state: FSMContext, bot: Bot):
    """Обработка измененного ФИО"""
    if not message.text:
        await message.answer("Пожалуйста, введите ФИО текстом:")
        return
    
    name = message.text.strip()
    
    data = await state.get_data()
    registration_messages = data.get('registration_messages', [])
    registration_messages.append(message.message_id)
    
    await state.update_data(name=name, registration_messages=registration_messages)
    await show_confirmation(message, state, bot)

@router.message(RegistrationStates.editing_phone)
async def process_edited_phone(message: types.Message, state: FSMContext, bot: Bot):
    # Обрабатываем ТОЛЬКО текстовый ввод
    if not message.text:
        await handle_invalid_phone(message, state)
        return
    
    phone = message.text
    
    # Дополнительная проверка на None и пустую строку
    if not phone:
        await handle_invalid_phone(message, state)
        return
    
    # ФОРМАТИРУЕМ номер перед валидацией
    cleaned_phone = re.sub(r'[^\d+]', '', phone)
    
    # Форматируем номер
    if cleaned_phone.startswith('+'):
        formatted_phone = cleaned_phone
    elif cleaned_phone.startswith('8'):
        formatted_phone = '+7' + cleaned_phone[1:]
    elif cleaned_phone.startswith('7'):
        formatted_phone = '+' + cleaned_phone
    else:
        formatted_phone = '+7' + cleaned_phone
    
    logger.info(f"Форматированный номер: {formatted_phone}")
    
    # Проверяем валидность номера
    if not validate_phone_number(formatted_phone):
        await handle_invalid_phone(message, state)
        return
    
    # Если номер валиден, обновляем и показываем подтверждение
    await state.update_data(phone=formatted_phone)
    await show_confirmation(message, state, bot)

