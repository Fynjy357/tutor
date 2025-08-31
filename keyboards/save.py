# keyboards/save.py
from aiogram import types
from aiogram.utils.keyboard import InlineKeyboardBuilder

def get_save_keyboard():
    builder = InlineKeyboardBuilder()
    builder.row(
        types.InlineKeyboardButton(
            text="Подтвердить",
            callback_data="confirm_data"
        )
    )
    return builder.as_markup()