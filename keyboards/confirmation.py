# keyboards/confirmation.py
from aiogram import types
from aiogram.utils.keyboard import InlineKeyboardBuilder

from keyboards.save import get_save_keyboard
from keyboards.edit import get_edit_keyboard

def get_confirmation_keyboard():
    # Создаем основного строителя
    builder = InlineKeyboardBuilder()
    
    # Добавляем кнопку "Подтвердить" из save.py
    save_button = types.InlineKeyboardButton(
        text="Подтвердить",
        callback_data="confirm_data"
    )
    builder.add(save_button)
    
    # Добавляем кнопки "Изменить ФИО" и "Изменить телефон" из edit.py
    edit_buttons = [
        types.InlineKeyboardButton(
            text="Изменить ФИО",
            callback_data="change_name"
        ),
        types.InlineKeyboardButton(
            text="Изменить телефон",
            callback_data="change_phone"
        )
    ]
    builder.row(*edit_buttons)
    
    return builder.as_markup()