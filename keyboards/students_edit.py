# keyboards/students_edit.py
from aiogram import types
from aiogram.utils.keyboard import InlineKeyboardBuilder

def get_edit_student_keyboard(student_id):
    """Клавиатура для редактирования ученика"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        types.InlineKeyboardButton(
            text="✏️ ФИО",
            callback_data=f"edit_name_{student_id}"
        ),
        types.InlineKeyboardButton(
            text="📞 Телефон ученика",
            callback_data=f"edit_phone_{student_id}"
        )
    )
    
    builder.row(
        types.InlineKeyboardButton(
            text="👨‍👩‍👧‍👦 Телефон родителя",
            callback_data=f"edit_parent_phone_{student_id}"
        ),
        types.InlineKeyboardButton(
            text="📊 Статус",
            callback_data=f"edit_status_{student_id}"
        )
    )
    
    builder.row(
        types.InlineKeyboardButton(
            text="◀️ Назад к ученику",
            callback_data=f"student_{student_id}"
        )
    )
    
    return builder.as_markup()

def get_status_keyboard(student_id):
    """Клавиатура для выбора статуса"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        types.InlineKeyboardButton(
            text="✅ Активный",
            callback_data=f"set_status_active_{student_id}"
        )
    )
    
    # builder.row(
    #     types.InlineKeyboardButton(
    #         text="⏸️ На паузе",
    #         callback_data=f"set_status_paused_{student_id}"
    #     )
    # )
    
    builder.row(
        types.InlineKeyboardButton(
            text="❌ Неактивный",
            callback_data=f"status_inactive_{student_id}"
        )
    )
    
    builder.row(
        types.InlineKeyboardButton(
            text="◀️ Назад к редактированию",
            callback_data=f"edit_student_{student_id}"
        )
    )
    
    return builder.as_markup()

def get_cancel_edit_keyboard(student_id):
    """Клавиатура отмены редактирования"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        types.InlineKeyboardButton(
            text="❌ Отменить редактирование",
            callback_data=f"student_{student_id}"
        )
    )
    
    return builder.as_markup()