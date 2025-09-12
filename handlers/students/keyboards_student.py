# keyboards/keyboards_student.py
from aiogram import types
from aiogram.utils.keyboard import InlineKeyboardBuilder
from datetime import datetime
import math
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

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
            text="📝 Редактировать отчеты",
            callback_data="edit_reports"
        )
    )
    
    builder.row(
        types.InlineKeyboardButton(
            text="◀️ Назад в главное меню",
            callback_data="back_to_main_students"
        )
    )
    
    return builder.as_markup()

def get_cancel_keyboard_add_students():
    builder = InlineKeyboardBuilder()
    builder.row(
        types.InlineKeyboardButton(
            text="❌ Отменить",
            callback_data="cancel_operation"
        )
    )
    return builder.as_markup()

def get_students_list_menu_keyboard():  # ИЗМЕНЕНО ИМЯ ФУНКЦИИ
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

def get_students_pagination_keyboard(students, page=0, page_size=5):
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

# Клавиатуры для редактирования отчетов
def get_dates_keyboard(dates, page=0, total_pages=1):
    """Клавиатура с датами занятий"""
    builder = InlineKeyboardBuilder()
    
    # Добавляем кнопки с датами (максимум 6 на страницу)
    for date in dates[page*6:(page+1)*6]:
        builder.row(
            types.InlineKeyboardButton(
                text=date.strftime("%d.%m.%Y"),
                callback_data=f"report_date_{date.strftime('%Y-%m-%d')}"
            )
        )
    
    # Кнопки навигации
    nav_buttons = []
    if page > 0:
        nav_buttons.append(
            types.InlineKeyboardButton(
                text="◀️ Назад",
                callback_data=f"reports_page_{page-1}"
            )
        )
    if page < total_pages - 1:
        nav_buttons.append(
            types.InlineKeyboardButton(
                text="Вперед ▶️",
                callback_data=f"reports_page_{page+1}"
            )
        )
    
    if nav_buttons:
        builder.row(*nav_buttons)
    
    builder.row(
        types.InlineKeyboardButton(
            text="◀️ Главное меню",
            callback_data="back_to_students_menu"
        )
    )
    
    return builder.as_markup()

def get_reports_keyboard(reports: list, page: int, total_pages: int) -> InlineKeyboardMarkup:
    """Клавиатура для выбора отчета с пагинацией"""
    keyboard = InlineKeyboardBuilder()
    
    # ДОБАВЬТЕ ПАГИНАЦИЮ ДЛЯ ОТЧЕТОВ!
    start_idx = page * 6
    end_idx = start_idx + 6
    current_page_reports = reports[start_idx:end_idx]
    
    for report in current_page_reports:  # Используем current_page_reports вместо reports
        # Безопасное получение данных отчета
        time_str = report.get('time', 'Не указано')
        student_name = report.get('student_name', 'Неизвестный ученик')
        
        keyboard.row(
            InlineKeyboardButton(
                text=f"{time_str} - {student_name}",
                callback_data=f"select_report:{report['id']}"
            )
        )
    
    # Добавляем кнопки пагинации
    pagination_buttons = []
    if page > 0:
        pagination_buttons.append(
            InlineKeyboardButton(text="⬅️ Назад", callback_data=f"reports_list_page_{page-1}")
        )
    if page < total_pages - 1:
        pagination_buttons.append(
            InlineKeyboardButton(text="Вперед ➡️", callback_data=f"reports_list_page_{page+1}")
        )
    
    if pagination_buttons:
        keyboard.row(*pagination_buttons)
    
    keyboard.row(
        InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_dates")
    )
    
    return keyboard.as_markup()

def get_report_edit_keyboard(report_id):
    """Клавиатура для редактирования отчета"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        types.InlineKeyboardButton(
            text="✅ Присутствие на занятии",
            callback_data=f"toggle_attendance_{report_id}"
        )
    )
    
    builder.row(
        types.InlineKeyboardButton(
            text="💰 Оплата занятия",
            callback_data=f"toggle_payment_{report_id}"
        )
    )
    
    builder.row(
        types.InlineKeyboardButton(
            text="📚 Домашнее задание",
            callback_data=f"toggle_homework_{report_id}"
        )
    )
    
    builder.row(
        types.InlineKeyboardButton(
            text="✏️ Редактировать комментарий",
            callback_data=f"edit_comment_{report_id}"
        )
    )
    
    builder.row(
        types.InlineKeyboardButton(
            text="◀️ Назад к отчетам",
            callback_data="back_to_reports"
        )
    )
    
    return builder.as_markup()

def get_cancel_edit_keyboard():
    """Клавиатура для отмена редактирования"""
    builder = InlineKeyboardBuilder()
    builder.row(
        types.InlineKeyboardButton(
            text="❌ Отменить редактирование",
            callback_data="cancel_edit"
        )
    )
    return builder.as_markup()