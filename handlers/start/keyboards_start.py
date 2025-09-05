# keyboards/registration.py
from aiogram import types
from aiogram.utils.keyboard import InlineKeyboardBuilder
def get_registration_keyboard():
    builder = InlineKeyboardBuilder()
    builder.row(
        types.InlineKeyboardButton(
            text="Зарегистрироваться",
            callback_data="start_registration"
        )
    )
    builder.row(
        types.InlineKeyboardButton(
            text="О боте",
            callback_data="about_bot"
        )
    )
    return builder.as_markup()

def get_cancel_keyboard():
    builder = InlineKeyboardBuilder()
    builder.row(
        types.InlineKeyboardButton(
            text="Отменить регистрацию",
            callback_data="cancel_registration"
        )
    )
    return builder.as_markup()
def get_promo_keyboard():
    builder = InlineKeyboardBuilder()
    builder.row(
        types.InlineKeyboardButton(
            text="Пропустить",
            callback_data="skip_promo"
        )
    )
    return builder.as_markup()
