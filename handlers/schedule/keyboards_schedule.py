# handlers/schedule/keyboards_schedule.py
from aiogram import types
from aiogram.utils.keyboard import InlineKeyboardBuilder

def get_schedule_keyboard():
    """Клавиатура для управления расписанием"""
    builder = InlineKeyboardBuilder()
    
    # Первый ряд - две кнопки в одной строке
    builder.row(
        types.InlineKeyboardButton(
            text="➕ Единоразовое",
            callback_data="add_lesson"
        ),
        types.InlineKeyboardButton(
            text="🔄 Регулярное",
            callback_data="planer_lessons"
        ),
        width=2  # Две кнопки в строке
    )

    # Второй ряд
    builder.row(
        types.InlineKeyboardButton(
            text="✏️ Редактировать занятие",
            callback_data="edit_lesson"
        )
    )
    
    # Третий ряд - кнопка назад
    builder.row(
        types.InlineKeyboardButton(
            text="◀️ Назад в главное меню",
            callback_data="back_from_schedule"
        )
    )
    
    return builder.as_markup()
