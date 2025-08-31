from aiogram import types
from aiogram.utils.keyboard import InlineKeyboardBuilder

def get_main_menu_keyboard():
    builder = InlineKeyboardBuilder()
    
    # Первый ряд
    builder.row(
        types.InlineKeyboardButton(
            text="📅 Расписание занятий",
            callback_data="schedule"
        )
    )
    
    # Второй ряд
    builder.row(
        types.InlineKeyboardButton(
            text="👥 Учет учеников",
            callback_data="students"
        ),
        types.InlineKeyboardButton(
            text="👨‍👩‍👧‍👦 Управление группами",
            callback_data="groups"
        )
    )
    
    # Третий ряд
    builder.row(
        types.InlineKeyboardButton(
            text="💰 Оплаты",
            callback_data="payments"
        ),
        types.InlineKeyboardButton(
            text="⚙️ Настройки",
            callback_data="settings"
        )
    )
    
    return builder.as_markup()