from aiogram import Router, types, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest
import logging
import re

from handlers.registration.states import RegistrationStates
from handlers.registration.utils import show_confirmation, save_tutor_data
from handlers.schedule.schedule_utils import get_today_schedule_text
from handlers.start.config import WELCOME_BACK_TEXT
from keyboards.keyboard_phone import get_phone_keyboard
from handlers.registration.keyboards import get_cancel_keyboard
from handlers.start.keyboards_start import get_registration_keyboard
from keyboards.main_menu import get_main_menu_keyboard
from handlers.registration.utils import validate_phone_number, handle_invalid_phone
from database import db

router = Router()
logger = logging.getLogger(__name__)

@router.callback_query(F.data == "start_registration")
async def start_registration(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.answer()
    
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

@router.callback_query(F.data == "confirm_data")
async def confirm_data(callback_query: types.CallbackQuery, state: FSMContext, bot: Bot):
    await callback_query.answer()
    
    # Получаем текущее состояние
    current_state = await state.get_state()
    logger.info(f"Текущее состояние: {current_state}")
    
    # Получаем данные из состояния
    user_data = await state.get_data()
    logger.info(f"Данные состояния: {user_data}")
    
    # Проверяем, есть ли необходимые данные
    if not user_data.get('name') or not user_data.get('phone'):
        await callback_query.message.edit_text(
            "Ошибка: данные не найдены. Пожалуйста, начните регистрацию заново."
        )
        await state.clear()
        return
    
    # Сохраняем данные в базу
    try:
        tutor_id, success = await save_tutor_data(callback_query, user_data, bot)
        
        if not success:
            raise Exception("Не удалось сохранить данные репетитора")
        
        logger.info(f"Репетитор добавлен с ID: {tutor_id}")
        
        # Получаем данные репетитора из базы
        tutor = db.get_tutor_by_telegram_id(callback_query.from_user.id)
        
        if not tutor:
            await callback_query.message.edit_text(
                "❌ Ошибка: не найдены данные репетитора после регистрации"
            )
            await state.clear()
            return
        
        # Получаем расписание на сегодня
        schedule_text = await get_today_schedule_text(tutor_id)
        
        # Формируем приветственное сообщение
        welcome_text = WELCOME_BACK_TEXT.format(
            tutor_name=tutor[2],  # Имя репетитора
            schedule_text=schedule_text
        )
        
        # Удаляем сообщение с подтверждением
        try:
            await callback_query.message.delete()
        except TelegramBadRequest:
            logger.warning("Не удалось удалить сообщение подтверждения")
        
        # Отправляем приветственное сообщение с главным меню
        await callback_query.message.answer(
            welcome_text,
            reply_markup=get_main_menu_keyboard(),
            parse_mode="HTML"
        )
        
    except Exception as e:
        logger.error(f"Ошибка при сохранении данных: {e}")
        await callback_query.message.edit_text(
            f"Произошла ошибка при сохранении данных: {str(e)}\n\n"
            "Пожалуйста, попробуйте позже или обратитесь к администратору."
        )
    
    await state.clear()

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

# УДАЛЕНО: Дублирующиеся обработчики сообщений для телефонов
# Эти обработчики уже есть в messages.py и правильно форматируют номера
# Удаляем их, чтобы избежать конфликта и передачи неформатированных номеров