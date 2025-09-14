from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def get_invite_keyboard(student_id):
    """Создает клавиатуру для меню приглашений"""
    keyboard = [
        [InlineKeyboardButton(text="👤 Пригласить ученика", callback_data=f"invite_student_{student_id}")],
        [InlineKeyboardButton(text="👨‍👩‍👧‍👦 Пригласить родителя", callback_data=f"invite_parent_{student_id}")],
        [InlineKeyboardButton(text="◀️ Назад к ученику", callback_data=f"back_to_student_{student_id}")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_student_detail_keyboard(student_id):
    """Создает клавиатуру для детальной информации об ученике"""
    keyboard = [
        [InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"edit_student_{student_id}")],
        [InlineKeyboardButton(text="📤 Пригласить ученика/родителя", callback_data=f"invite_{student_id}")],
        [InlineKeyboardButton(text="◀️ Назад к списку", callback_data="students_list")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

