from aiogram import types
from database import db
from handlers.start.keyboards_start import get_registration_keyboard
from keyboards.main_menu import get_main_menu_keyboard
from handlers.start.config import WELCOME_BACK_TEXT, REGISTRATION_TEXT

async def show_welcome_message(message: types.Message):
    """Показ приветственного сообщения"""
    existing_tutor = db.get_tutor_by_telegram_id(message.from_user.id)
    
    if existing_tutor:
        await show_welcome_back(message, existing_tutor)
    else:
        await show_registration_message(message)

async def show_welcome_back(message: types.Message, tutor: tuple):
    """Приветствие для зарегистрированного репетитора"""
    welcome_text = WELCOME_BACK_TEXT.format(tutor_name=tutor[2])
    
    await message.answer(
        welcome_text,
        reply_markup=get_main_menu_keyboard(),
        parse_mode="HTML"
    )

async def show_registration_message(message: types.Message):
    """Приветствие для нового пользователя"""
    await message.answer(
        REGISTRATION_TEXT,
        reply_markup=get_registration_keyboard(),
        parse_mode="HTML"
    )