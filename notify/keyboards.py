"""Клавиатуры для уведомлений"""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def get_confirmation_keyboard(lesson_id, confirmation_id):
    """Создает клавиатуру для подтверждения занятия"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton("✅ Подтвердить", callback_data=f"confirm_{lesson_id}_{confirmation_id}"),
            InlineKeyboardButton("❌ Отменить", callback_data=f"cancel_{lesson_id}_{confirmation_id}")
        ],
        [
            InlineKeyboardButton("🔄 Перенести", callback_data=f"reschedule_{lesson_id}_{confirmation_id}")
        ]
    ])
    return keyboard