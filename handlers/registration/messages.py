from aiogram import Router, types, F, Bot
from aiogram.fsm.context import FSMContext
import logging

from handlers.registration.states import RegistrationStates
from handlers.registration.utils import show_confirmation
from keyboards.registration import get_phone_keyboard, get_promo_keyboard
from database import db

router = Router()
logger = logging.getLogger(__name__)

@router.message(RegistrationStates.waiting_for_name)
async def process_name(message: types.Message, state: FSMContext, bot: Bot):
    # Сохраняем ID сообщения пользователя
    data = await state.get_data()
    registration_messages = data.get('registration_messages', [])
    registration_messages.append(message.message_id)
    
    await state.update_data(name=message.text, registration_messages=registration_messages)
    
    # Отправляем сообщение с запросом телефона
    phone_message = await message.answer(
        "Отлично! Теперь введите ваш телефон. Вы можете использовать кнопку ниже для быстрой отправки:",
        reply_markup=get_phone_keyboard()
    )
    
    # Добавляем ID нового сообщения в список
    registration_messages.append(phone_message.message_id)
    await state.update_data(registration_messages=registration_messages)
    await state.set_state(RegistrationStates.waiting_for_phone)

@router.message(RegistrationStates.waiting_for_phone, F.contact)
async def process_phone_contact(message: types.Message, state: FSMContext, bot: Bot):
    # Сохраняем ID сообщения пользователя
    data = await state.get_data()
    registration_messages = data.get('registration_messages', [])
    registration_messages.append(message.message_id)
    
    contact = message.contact
    phone_number = contact.phone_number
    
    # Если номер начинается с +, убираем его для сохранения
    if phone_number.startswith('+'):
        phone_number = phone_number[1:]
    
    await state.update_data(phone=phone_number, registration_messages=registration_messages)
    
    # Отправляем запрос промокода
    promo_message = await message.answer(
        "Введите ваш промокод, если он есть:",
        reply_markup=get_promo_keyboard()
    )
    
    # Добавляем ID нового сообщения в список
    registration_messages.append(promo_message.message_id)
    await state.update_data(registration_messages=registration_messages)
    await state.set_state(RegistrationStates.waiting_for_promo)

@router.message(RegistrationStates.waiting_for_phone, F.text)
async def process_phone_text(message: types.Message, state: FSMContext, bot: Bot):
    # Сохраняем ID сообщения пользователя
    data = await state.get_data()
    registration_messages = data.get('registration_messages', [])
    registration_messages.append(message.message_id)
    
    phone_number = message.text
    
    # Простая валидация номера телефона
    if not phone_number or not phone_number.replace('+', '').replace(' ', '').replace('-', '').replace('(', '').replace(')', '').isdigit():
        await message.answer("Пожалуйста, введите корректный номер телефона:")
        return
    
    await state.update_data(phone=phone_number, registration_messages=registration_messages)
    
    # Отправляем запрос промокода
    promo_message = await message.answer(
        "Введите ваш промокод, если он есть:",
        reply_markup=get_promo_keyboard()
    )
    
    # Добавляем ID нового сообщения в список
    registration_messages.append(promo_message.message_id)
    await state.update_data(registration_messages=registration_messages)
    await state.set_state(RegistrationStates.waiting_for_promo)

@router.message(RegistrationStates.waiting_for_promo, F.text)
async def process_promo(message: types.Message, state: FSMContext, bot: Bot):
    # Сохраняем ID сообщения пользователя
    data = await state.get_data()
    registration_messages = data.get('registration_messages', [])
    registration_messages.append(message.message_id)
    
    promo_code = message.text
    
    # Проверяем валидность промокода
    promo_info = db.check_promo_code(promo_code)
    if not promo_info:
        await message.answer("Этот промокод недействителен. Пожалуйста, введите другой промокод или нажмите 'Пропустить':")
        return
    
    await state.update_data(promo=promo_code, registration_messages=registration_messages)
    await show_confirmation(message, state, bot)

@router.message(RegistrationStates.editing_name)
async def process_edited_name(message: types.Message, state: FSMContext, bot: Bot):
    # Проверяем, что сообщение содержит текст
    if not message.text:
        await message.answer("Пожалуйста, введите ФИО:")
        return
    
    # Обновляем имя в состоянии
    await state.update_data(name=message.text)
    
    # Удаляем сообщение с запросом нового имени
    try:
        await bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
    except Exception:
        pass
    
    # Показываем обновленные данные для подтверждения
    await show_confirmation(message, state, bot)

@router.message(RegistrationStates.editing_phone, F.text)
async def process_edited_phone(message: types.Message, state: FSMContext, bot: Bot):
    # Проверяем, что сообщение содержит текст
    if not message.text:
        await message.answer("Пожалуйста, введите номер телефона:")
        return
    
    # Обновляем телефон в состоянии
    phone_number = message.text
    
    # Простая валидация номера телефона
    if not phone_number.replace('+', '').replace(' ', '').replace('-', '').replace('(', '').replace(')', '').isdigit():
        await message.answer("Пожалуйста, введите корректный номер телефона:")
        return
    
    await state.update_data(phone=phone_number)
    
    # Удаляем сообщение с запросом нового телефона
    try:
        await bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
    except Exception:
        pass
    
    # Показываем обновленные данные для подтверждения
    await show_confirmation(message, state, bot)

@router.message(RegistrationStates.editing_phone, F.contact)
async def process_edited_phone_contact(message: types.Message, state: FSMContext, bot: Bot):
    # Проверяем, что сообщение содержит контакт
    if not message.contact:
        await message.answer("Пожалуйста, используйте кнопку для отправки номера телефона:")
        return
    
    # Обновляем телефон в состоянии
    contact = message.contact
    phone_number = contact.phone_number
    
    # Если номер начинается с +, убираем его для сохранения
    if phone_number.startswith('+'):
        phone_number = phone_number[1:]
    
    await state.update_data(phone=phone_number)
    
    # Удаляем сообщение с запросом нового телефона
    try:
        await bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
    except Exception:
        pass
    
    # Показываем обновленные данные для подтверждения
    await show_confirmation(message, state, bot)

@router.message(RegistrationStates.waiting_for_phone)
async def process_invalid_phone_input(message: types.Message):
    await message.answer("Пожалуйста, введите номер телефона текстом или используйте кнопку 'Отправить номер телефона'")

@router.message(RegistrationStates.waiting_for_promo)
async def process_invalid_promo_input(message: types.Message):
    await message.answer("Пожалуйста, введите промокод текстом или используйте кнопку 'Пропустить'")

@router.message(RegistrationStates.editing_phone)
async def process_invalid_phone_edit_input(message: types.Message):
    await message.answer("Пожалуйста, введите номер телефона текстом или используйте кнопку 'Отправить номер телефона'")