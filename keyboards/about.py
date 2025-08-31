# keyboards/about.py
from aiogram import types
from aiogram.utils.keyboard import InlineKeyboardBuilder

def get_about_keyboard():
    builder = InlineKeyboardBuilder()
    builder.row(
        types.InlineKeyboardButton(
            text="Назад",
            callback_data="back_to_main"
        )
    )
    return builder.as_markup()