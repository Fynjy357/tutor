from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime

def get_date_selection_keyboard(lessons_by_date):
    """Клавиатура для выбора даты"""
    keyboard_buttons = []
    for date_str in sorted(lessons_by_date.keys()):
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        display_date = date_obj.strftime("%d.%m.%Y")
        keyboard_buttons.append([InlineKeyboardButton(
            text=f"📅 {display_date} ({len(lessons_by_date[date_str])} занятий)",
            callback_data=f"edit_date_{date_str}"
        )])
    
    keyboard_buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="schedule")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)

def get_lesson_selection_keyboard(grouped_lessons, selected_date):
    """Клавиатура для выбора занятия"""
    keyboard_buttons = []
    for key, lesson_info in sorted(grouped_lessons.items(), key=lambda x: x[1]['time']):
        if lesson_info.get('is_group', True):  # Групповое занятие
            display_text = f"{lesson_info['time']} - 👥 {lesson_info['group_name']} ({lesson_info['count']} чел.)"
            callback_data = f"select_group_{lesson_info['group_id']}_{selected_date}_{lesson_info['time']}"
        else:  # Индивидуальное занятие
            display_text = f"{lesson_info['time']} - 👤 {lesson_info['student_name']}"
            callback_data = f"select_lesson_{lesson_info['lesson_id']}"
        
        keyboard_buttons.append([InlineKeyboardButton(
            text=display_text,
            callback_data=callback_data
        )])
    
    keyboard_buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="edit_lesson")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)

def get_individual_edit_keyboard(lesson_date, is_group=False):
    """Клавиатура для редактирования индивидуального занятия"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Изменить дату/время", callback_data="edit_datetime")],
        [InlineKeyboardButton(text="💰 Изменить стоимость", callback_data="edit_price")],
        [InlineKeyboardButton(text="⏱️ Изменить длительность", callback_data="edit_duration")],
        [InlineKeyboardButton(text="❌ Удалить занятие", callback_data="delete_lesson")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data=f"edit_date_{lesson_date}")]
    ])

def get_group_edit_keyboard(selected_date):
    """Клавиатура для редактирования группового занятия"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Изменить дату/время", callback_data="edit_group_datetime")],
        [InlineKeyboardButton(text="💰 Изменить стоимость", callback_data="edit_group_price")],
        [InlineKeyboardButton(text="⏱️ Изменить длительность", callback_data="edit_group_duration")],
        [InlineKeyboardButton(text="❌ Удалить все занятия группы", callback_data="delete_group_lessons")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data=f"edit_date_{selected_date}")]
    ])

def get_back_keyboard(callback_data):
    """Клавиатура с кнопкой назад"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад", callback_data=callback_data)]
    ])

def get_confirmation_keyboard(confirm_callback, cancel_callback):
    """Клавиатура подтверждения"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Да", callback_data=confirm_callback)],
        [InlineKeyboardButton(text="❌ Нет", callback_data=cancel_callback)]
    ])