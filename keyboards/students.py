# keyboards/students.py
from aiogram import types
from aiogram.utils.keyboard import InlineKeyboardBuilder

def get_students_menu_keyboard():
    builder = InlineKeyboardBuilder()
    
    builder.row(
        types.InlineKeyboardButton(
            text="➕ Добавить ученика",
            callback_data="add_student"
        )
    )
    
    builder.row(
        types.InlineKeyboardButton(
            text="📋 Список учеников",
            callback_data="students_list"
        )
    )
    
    builder.row(
        types.InlineKeyboardButton(
            text="◀️ Назад в главное меню",
            callback_data="back_to_main"
        )
    )
    
    return builder.as_markup()

def get_cancel_keyboard():
    builder = InlineKeyboardBuilder()
    builder.row(
        types.InlineKeyboardButton(
            text="❌ Отменить",
            callback_data="cancel_operation"
        )
    )
    return builder.as_markup()

# Добавим временные клавиатуры для будущего функционала
def get_students_list_keyboard():
    builder = InlineKeyboardBuilder()
    
    builder.row(
        types.InlineKeyboardButton(
            text="📋 Список всех учеников",
            callback_data="all_students"
        )
    )
    
    builder.row(
        types.InlineKeyboardButton(
            text="👤 Активные ученики",
            callback_data="active_students"
        )
    )
    
    builder.row(
        types.InlineKeyboardButton(
            text="◀️ Назад к меню учеников",
            callback_data="back_to_students_menu"
        )
    )
    
    return builder.as_markup()

def get_students_list_keyboard(students, page=0, page_size=5):
    builder = InlineKeyboardBuilder()
    
    # Добавляем кнопки для учеников на текущей странице
    start_idx = page * page_size
    end_idx = start_idx + page_size
    current_page_students = students[start_idx:end_idx]
    
    for student in current_page_students:
        builder.row(
            types.InlineKeyboardButton(
                text=f"👤 {student['full_name']}",
                callback_data=f"student_{student['id']}"
            )
        )
    
    # Добавляем кнопки навигации, если нужно
    if len(students) > page_size:
        navigation_buttons = []
        
        if page > 0:
            navigation_buttons.append(
                types.InlineKeyboardButton(
                    text="⬅️ Назад",
                    callback_data=f"students_page_{page-1}"
                )
            )
        
        if end_idx < len(students):
            navigation_buttons.append(
                types.InlineKeyboardButton(
                    text="➡️ Вперед",
                    callback_data=f"students_page_{page+1}"
                )
            )
        
        if navigation_buttons:
            builder.row(*navigation_buttons)
    
    # Кнопка возврата
    builder.row(
        types.InlineKeyboardButton(
            text="◀️ Назад к меню учеников",
            callback_data="back_to_students_menu"
        )
    )
    
    return builder.as_markup()