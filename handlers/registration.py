from aiogram import Router, types, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import Contact, ReplyKeyboardRemove
import logging

from keyboards.registration import get_registration_keyboard, get_cancel_keyboard, get_phone_keyboard, get_promo_keyboard
from keyboards.confirmation import get_confirmation_keyboard
from database import db  # Импортируем нашу базу данных

router = Router()
logger = logging.getLogger(__name__)

# Состояния для регистрации
class RegistrationStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_phone = State()
    waiting_for_promo = State()
    confirmation = State()
    editing_name = State()
    editing_phone = State()

# Обработчик нажатия на кнопку "Зарегистрироваться"
@router.callback_query(F.data == "start_registration")
async def start_registration(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.answer()
    
    # Проверяем, не зарегистрирован ли пользователь уже
    existing_tutor = db.get_tutor_by_telegram_id(callback_query.from_user.id)
    if existing_tutor:
        await callback_query.message.answer(
            "Вы уже зарегистрированы в системе!\n\n"
            f"ФИО: {existing_tutor[2]}\n"
            f"Телефон: {existing_tutor[3]}\n"
            f"Промокод: {existing_tutor[4] if existing_tutor[4] != '0' else 'не указан'}"
        )
        return
    
    try:
        # Удаляем предыдущее сообщение с кнопками
        await callback_query.message.delete()
    except TelegramBadRequest:
        # Если сообщение уже удалено, игнорируем ошибку
        pass
    
    # Отправляем новое сообщение с запросом ФИО
    message = await callback_query.message.answer(
        "Начинаем процесс регистрации...\n\nПожалуйста, введите ваше ФИО:",
        reply_markup=get_cancel_keyboard()
    )
    
    # Сохраняем ID сообщения в состоянии
    await state.set_state(RegistrationStates.waiting_for_name)
    await state.update_data(registration_messages=[message.message_id])

# Обработчик ввода имени
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

# Обработчик получения номера телефона через кнопку
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

# Обработчик ввода телефона вручную
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

# Обработчик для некорректных сообщений в режиме ожидания телефона
@router.message(RegistrationStates.waiting_for_phone)
async def process_invalid_phone_input(message: types.Message):
    await message.answer("Пожалуйста, введите номер телефона текстом или используйте кнопку 'Отправить номер телефона'")

# Обработчик ввода промокода
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

# Обработчик пропуска промокода
@router.callback_query(RegistrationStates.waiting_for_promo, F.data == "skip_promo")
async def skip_promo(callback_query: types.CallbackQuery, state: FSMContext, bot: Bot):
    await callback_query.answer()
    
    # Сохраняем ID сообщения с промокодом
    data = await state.get_data()
    registration_messages = data.get('registration_messages', [])
    registration_messages.append(callback_query.message.message_id)
    
    # Устанавливаем промокод как "0"
    await state.update_data(promo="0", registration_messages=registration_messages)
    await show_confirmation(callback_query.message, state, bot)

# Обработчик для некорректных сообщений в режиме ожидания промокода
@router.message(RegistrationStates.waiting_for_promo)
async def process_invalid_promo_input(message: types.Message):
    await message.answer("Пожалуйста, введите промокод текстом или используйте кнопку 'Пропустить'")

# Показать подтверждение данных
async def show_confirmation(message: types.Message, state: FSMContext, bot: Bot):
    user_data = await state.get_data()
    
    # Удаляем все сообщения процесса регистрации
    registration_messages = user_data.get('registration_messages', [])
    for msg_id in registration_messages:
        try:
            await bot.delete_message(chat_id=message.chat.id, message_id=msg_id)
        except TelegramBadRequest:
            # Если сообщение уже удалено, игнорируем ошибку
            pass
    
    # Формируем текст с промокодом
    promo_code = user_data.get('promo', '0')
    promo_text = f"Промокод: {promo_code}" if promo_code != "0" else "Промокод: не указан"
    
    # Проверяем валидность промокода, если он указан
    if promo_code != "0":
        promo_info = db.check_promo_code(promo_code)
        if promo_info:
            discount = promo_info[2] if promo_info[2] > 0 else promo_info[3]
            discount_type = "%" if promo_info[2] > 0 else "руб."
            promo_text = f"Промокод: {promo_code} (скидка {discount}{discount_type})"
        else:
            promo_text = f"Промокод: {promo_code} (недействителен)"
    
    # Отправляем сообщение с подтверждением данных и кнопками
    confirmation_message = await message.answer(
        f"Регистрация завершена!\n\n"
        f"ФИО: {user_data['name']}\n"
        f"Телефон: {user_data['phone']}\n"
        f"{promo_text}\n\n"
        f"Подтвердите правильность данных или измените их:",
        reply_markup=get_confirmation_keyboard()
    )
    
    # Сохраняем ID сообщения с подтверждением
    await state.update_data(registration_messages=[confirmation_message.message_id])
    await state.set_state(RegistrationStates.confirmation)

# Обработчик подтверждения данных
@router.callback_query(RegistrationStates.confirmation, F.data == "confirm_data")
async def confirm_data(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.answer()
    user_data = await state.get_data()
    
    # Сохраняем данные в базу
    try:
        tutor_id = db.add_tutor(
            telegram_id=callback_query.from_user.id,
            full_name=user_data['name'],
            phone=user_data['phone'],
            promo_code=user_data.get('promo', '0')
        )
        
        # Проверяем и используем промокод, если он валидный
        promo_code = user_data.get('promo')
        if promo_code and promo_code != '0':
            promo_info = db.check_promo_code(promo_code)
            if promo_info:
                db.use_promo_code(promo_code)
                discount = promo_info[2] if promo_info[2] > 0 else promo_info[3]
                discount_type = "%" if promo_info[2] > 0 else "руб."
                promo_text = f"Промокод: {promo_code} (скидка {discount}{discount_type})"
            else:
                promo_text = f"Промокод: {promo_code} (недействителен)"
        else:
            promo_text = "Промокод: не указан"
            
        # Формируем финальное сообщение
        await callback_query.message.edit_text(
            f"Данные подтверждены!\n\n"
            f"ФИО: {user_data['name']}\n"
            f"Телефон: {user_data['phone']}\n"
            f"{promo_text}\n\n"
            f"Теперь вы можете пользоваться всеми функциями бота."
        )
        
    except Exception as e:
        logger.error(f"Ошибка при сохранении данных: {e}")
        await callback_query.message.edit_text(
            "Произошла ошибка при сохранении данных. Пожалуйста, попробуйте позже."
        )
    
    await state.clear()

# Обработчик изменения ФИО
@router.callback_query(RegistrationStates.confirmation, F.data == "change_name")
async def change_name(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.answer()
    
    # Сохраняем ID сообщения с подтверждением для последующего удаления
    data = await state.get_data()
    registration_messages = data.get('registration_messages', [])
    registration_messages.append(callback_query.message.message_id)
    
    # Отправляем сообщение с запросом нового ФИО
    name_message = await callback_query.message.answer(
        "Введите новое ФИО:",
        reply_markup=get_cancel_keyboard()
    )
    
    # Добавляем ID нового сообщения в список
    registration_messages.append(name_message.message_id)
    await state.update_data(registration_messages=registration_messages)
    await state.set_state(RegistrationStates.editing_name)

# Обработчик изменения телефона
@router.callback_query(RegistrationStates.confirmation, F.data == "change_phone")
async def change_phone(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.answer()
    
    # Сохраняем ID сообщения с подтверждением для последующего удаления
    data = await state.get_data()
    registration_messages = data.get('registration_messages', [])
    registration_messages.append(callback_query.message.message_id)
    
    # Отправляем сообщение с запросом нового телефона
    phone_message = await callback_query.message.answer(
        "Введите новый телефон. Вы можете использовать кнопку ниже для быстрой отправки:",
        reply_markup=get_phone_keyboard()
    )
    
    # Добавляем ID нового сообщения в список
    registration_messages.append(phone_message.message_id)
    await state.update_data(registration_messages=registration_messages)
    await state.set_state(RegistrationStates.editing_phone)

# Обработчик ввода нового имени (в режиме редактирования)
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
    except TelegramBadRequest:
        pass
    
    # Показываем обновленные данные для подтверждения
    await show_confirmation(message, state, bot)

# Обработчик ввода нового телефона (в режиме редактирования)
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
    except TelegramBadRequest:
        pass
    
    # Показываем обновленные данные для подтверждения
    await show_confirmation(message, state, bot)

# Обработчик получения номера телефона через кнопку (в режиме редактирования)
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
    except TelegramBadRequest:
        pass
    
    # Показываем обновленные данные для подтверждения
    await show_confirmation(message, state, bot)

# Обработчик для некорректных сообщений в режиме редактирования телефона
@router.message(RegistrationStates.editing_phone)
async def process_invalid_phone_input(message: types.Message):
    await message.answer("Пожалуйста, введите номер телефона текстом или используйте кнопку 'Отправить номер телефона'")

# Обработчик отмены регистрации - удаляет все сообщения процесса регистрации
@router.callback_query(F.data == "cancel_registration")
async def cancel_registration(callback_query: types.CallbackQuery, state: FSMContext, bot: Bot):
    # Получаем данные из состояния
    data = await state.get_data()
    registration_messages = data.get('registration_messages', [])
    
    # Удаляем все сообщения процесса регистрации
    for msg_id in registration_messages:
        try:
            await bot.delete_message(chat_id=callback_query.message.chat.id, message_id=msg_id)
        except TelegramBadRequest:
            # Если сообщение уже удалено, игнорируем ошибку
            pass
    
    # Очищаем состояние
    await state.clear()
    await callback_query.answer()
    
    welcome_text = """
<b>Ежедневник репетитора</b>

Привет! Этот бот для репетиторов

🔲 Зарегистрироваться в боте
✅ Написать сообщение...
    """
    
    # Отправляем главное меню
    await callback_query.message.answer(
        welcome_text,
        reply_markup=get_registration_keyboard(),
        parse_mode="HTML"
    )