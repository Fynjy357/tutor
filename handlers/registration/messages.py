from aiogram import Router, types, F, Bot
from aiogram.fsm.context import FSMContext
import logging

from handlers.registration.states import RegistrationStates
from handlers.registration.utils import show_confirmation
from handlers.registration.keyboards import get_cancel_keyboard, get_promo_keyboard
from keyboards.keyboard_phone import get_phone_keyboard

router = Router()
logger = logging.getLogger(__name__)

@router.message(RegistrationStates.waiting_for_name)
async def process_name(message: types.Message, state: FSMContext, bot: Bot):
    """Обработка введенного ФИО"""
    # Проверяем, что сообщение содержит текст
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

@router.message(RegistrationStates.waiting_for_phone, F.text)
async def process_phone(message: types.Message, state: FSMContext, bot: Bot):
    """Обработка введенного телефона (только текстовые сообщения)"""
    phone = message.text.strip()
    
    # Базовая валидация телефона
    if not any(char.isdigit() for char in phone) or len(phone) < 5:
        await message.answer("Пожалуйста, введите корректный номер телефона:")
        return
    
    # Сохраняем телефон и ID сообщения
    data = await state.get_data()
    registration_messages = data.get('registration_messages', [])
    registration_messages.append(message.message_id)
    
    await state.update_data(phone=phone, registration_messages=registration_messages)
    
    # Запрашиваем промокод
    promo_message = await message.answer(
        "Если у вас есть промокод, введите его. Или нажмите 'Пропустить':",
        reply_markup=get_promo_keyboard()
    )
    
    registration_messages.append(promo_message.message_id)
    await state.update_data(registration_messages=registration_messages)
    await state.set_state(RegistrationStates.waiting_for_promo)

@router.message(RegistrationStates.waiting_for_promo)
async def process_promo(message: types.Message, state: FSMContext, bot: Bot):
    """Обработка введенного промокода"""
    # Проверяем, что сообщение содержит текст
    if not message.text:
        await message.answer("Пожалуйста, введите промокод текстом:")
        return
    
    promo = message.text.strip()
    
    # Сохраняем промокод и ID сообщения
    data = await state.get_data()
    registration_messages = data.get('registration_messages', [])
    registration_messages.append(message.message_id)
    
    await state.update_data(promo=promo, registration_messages=registration_messages)
    await show_confirmation(message, state, bot)

@router.message(RegistrationStates.editing_name)
async def process_edited_name(message: types.Message, state: FSMContext, bot: Bot):
    """Обработка измененного ФИО"""
    # Проверяем, что сообение содержит текст
    if not message.text:
        await message.answer("Пожалуйста, введите ФИО текстом:")
        return
    
    name = message.text.strip()
    
    # Сохраняем новое имя и ID сообщения
    data = await state.get_data()
    registration_messages = data.get('registration_messages', [])
    registration_messages.append(message.message_id)
    
    await state.update_data(name=name, registration_messages=registration_messages)
    await show_confirmation(message, state, bot)

@router.message(RegistrationStates.editing_phone)
async def process_edited_phone(message: types.Message, state: FSMContext, bot: Bot):
    """Обработка измененного телефона"""
    # Проверяем, что сообщение содержит текст
    if not message.text:
        await message.answer("Пожалуйста, введите номер телефона текстом:")
        return
    
    phone = message.text.strip()
    
    # Базовая валидация телефона
    if not any(char.isdigit() for char in phone) or len(phone) < 5:
        await message.answer("Пожалуйста, введите корректный номер телефона:")
        return
    
    # Сохраняем новый телефон и ID сообщения
    data = await state.get_data()
    registration_messages = data.get('registration_messages', [])
    registration_messages.append(message.message_id)
    
    await state.update_data(phone=phone, registration_messages=registration_messages)
    await show_confirmation(message, state, bot)

@router.message(RegistrationStates.waiting_for_phone, F.contact)
async def process_contact(message: types.Message, state: FSMContext, bot: Bot):
    """Обработка отправленного контакта"""
    if message.contact:
        phone = message.contact.phone_number
        
        # Сохраняем телефон и ID сообщения
        data = await state.get_data()
        registration_messages = data.get('registration_messages', [])
        registration_messages.append(message.message_id)
        
        await state.update_data(phone=phone, registration_messages=registration_messages)
        
        # Запрашиваем промокод
        promo_message = await message.answer(
            "Если у вас есть промокод, введите его. Или нажмите 'Пропустить':",
            reply_markup=get_promo_keyboard()
        )
        
        registration_messages.append(promo_message.message_id)
        await state.update_data(registration_messages=registration_messages)
        await state.set_state(RegistrationStates.waiting_for_promo)