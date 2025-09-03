# handlers/about.py
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.exceptions import TelegramBadRequest

from handlers.start.config import ABOUT_TEXT, REGISTRATION_TEXT
from keyboards.about import get_about_keyboard
from handlers.start.keyboards_start import get_registration_keyboard

router = Router()

# Обработчик нажатия на кнопку "О боте"
@router.callback_query(F.data == "about_bot")
async def about_bot(callback_query: types.CallbackQuery):
    await callback_query.answer()
    about_text = ABOUT_TEXT
    try:
        await callback_query.message.edit_text(
            about_text,
            reply_markup=get_about_keyboard(),
            parse_mode="HTML"
        )
    except TelegramBadRequest:
        # Если сообщение уже удалено, отправляем новое
        await callback_query.message.answer(
            about_text,
            reply_markup=get_about_keyboard(),
            parse_mode="HTML"
        )

# Обработчик нажатия на кнопку "Назад"
@router.callback_query(F.data == "back_to_main")
async def back_to_main(callback_query: types.CallbackQuery):
    await callback_query.answer()
    welcome_text = REGISTRATION_TEXT
    
    try:
        await callback_query.message.edit_text(
            welcome_text,
            reply_markup=get_registration_keyboard(),
            parse_mode="HTML"
        )
    except TelegramBadRequest:
        # Если сообщение уже удалено, отправляем новое
        await callback_query.message.answer(
            welcome_text,
            reply_markup=get_registration_keyboard(),
            parse_mode="HTML"
        )