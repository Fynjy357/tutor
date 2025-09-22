from aiogram import types
from aiogram.utils.keyboard import InlineKeyboardBuilder

def get_inactive_students_keyboard(students: list, page: int = 0):
    """Клавиатура с неактивными учениками"""
    builder = InlineKeyboardBuilder()
    
    # Показываем по 5 учеников на странице
    page_size = 5
    start_idx = page * page_size
    end_idx = start_idx + page_size
    current_students = students[start_idx:end_idx]
    
    # Кнопки учеников
    for student in current_students:
        builder.row(
            types.InlineKeyboardButton(
                text=f"👤 {student.get('full_name', 'Без имени')}",
                callback_data=f"inactive_student_{student['id']}"
            )
        )
    
    # Кнопки пагинации
    total_pages = (len(students) + page_size - 1) // page_size
    pagination_buttons = []
    
    if page > 0:
        pagination_buttons.append(
            types.InlineKeyboardButton(
                text="⬅️ Назад",
                callback_data=f"inactive_page_{page-1}"
            )
        )
    
    if page < total_pages - 1:
        pagination_buttons.append(
            types.InlineKeyboardButton(
                text="Вперед ➡️",
                callback_data=f"inactive_page_{page+1}"
            )
        )
    
    if pagination_buttons:
        builder.row(*pagination_buttons)
    
    # Кнопка назад
    builder.row(
        types.InlineKeyboardButton(
            text="◀️ Назад к ученикам",
            callback_data="students"
        )
    )
    
    return builder.as_markup()

def get_activate_student_keyboard(student_id: int):
    """Клавиатура для активации ученика"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        types.InlineKeyboardButton(
            text="✅ Сделать активным",
            callback_data=f"activate_student_{student_id}"
        )
    )
    
    builder.row(
        types.InlineKeyboardButton(
            text="⬅️ Назад к списку",
            callback_data="show_inactive_menu"
        )
    )
    
    return builder.as_markup()

def get_back_to_students_keyboard():
    """Клавиатура для возврата в меню учеников"""
    builder = InlineKeyboardBuilder()
    builder.row(
        types.InlineKeyboardButton(
            text="◀️ Назад к ученикам",
            callback_data="students"
        )
    )
    return builder.as_markup()