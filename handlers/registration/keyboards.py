from aiogram import types
from aiogram.utils.keyboard import InlineKeyboardBuilder

def get_cancel_keyboard():
    builder = InlineKeyboardBuilder()
    builder.row(
        types.InlineKeyboardButton(
            text="Отменить регистрацию",
            callback_data="cancel_registration"
        )
    )
    return builder.as_markup()

def get_confirmation_keyboard():
    builder = InlineKeyboardBuilder()
    builder.row(
        types.InlineKeyboardButton(
            text="✅ Всё верно",
            callback_data="confirm_data"
        )
    )
    builder.row(
        types.InlineKeyboardButton(
            text="✏️ Изменить ФИО",
            callback_data="change_name"
        ),
        types.InlineKeyboardButton(
            text="✏️ Изменить телефон",
            callback_data="change_phone"
        )
    )
    return builder.as_markup()