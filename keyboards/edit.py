# keyboards/edit.py
from aiogram import types
from aiogram.utils.keyboard import InlineKeyboardBuilder

def get_edit_keyboard():
    builder = InlineKeyboardBuilder()
    builder.row(
        types.InlineKeyboardButton(
            text="Изменить ФИО",
            callback_data="change_name"
        ),
        types.InlineKeyboardButton(
            text="Изменить телефон",
            callback_data="change_phone"
        )
    )
    return builder.as_markup()