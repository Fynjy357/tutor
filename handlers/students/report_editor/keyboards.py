# handlers/report_editor/keyboards.py
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def get_dates_keyboard(dates, page=0, total_pages=1):
    """Клавиатура для выбора дат с пагинацией"""
    keyboard = []
    
    # Показываем 6 дат на странице
    start_idx = page * 6
    end_idx = min(start_idx + 6, len(dates))
    
    for i in range(start_idx, end_idx):
        date = dates[i]
        keyboard.append([
            InlineKeyboardButton(
                text=date.strftime('%d.%m.%Y'),
                callback_data=f"report_date_{date.strftime('%Y-%m-%d')}"
            )
        ])
    
    # Пагинация
    pagination_buttons = []
    if page > 0:
        pagination_buttons.append(InlineKeyboardButton(text="⬅️", callback_data=f"reports_page_{page-1}"))
    
    # pagination_buttons.append(InlineKeyboardButton(text=f"{page+1}/{total_pages}", callback_data="current_page"))
    
    if page < total_pages - 1:
        pagination_buttons.append(InlineKeyboardButton(text="➡️", callback_data=f"reports_page_{page+1}"))
    
    if pagination_buttons:
        keyboard.append(pagination_buttons)
    
    keyboard.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="statistics_menu")])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_reports_keyboard(reports, page=0, total_pages=1):
    """Клавиатура для выбора отчетов с пагинацией"""
    keyboard = []
    
    # Показываем 6 отчетов на странице
    start_idx = page * 6
    end_idx = min(start_idx + 6, len(reports))
    
    for i in range(start_idx, end_idx):
        report = reports[i]
        keyboard.append([
            InlineKeyboardButton(
                text=f"{report['student_name']}",
                callback_data=f"select_report:{report['id']}"
            )
        ])
    
    # Пагинация
    pagination_buttons = []
    if page > 0:
        pagination_buttons.append(InlineKeyboardButton(text="⬅️", callback_data=f"reports_list_page_{page-1}"))
    
    # pagination_buttons.append(InlineKeyboardButton(text=f"{page+1}/{total_pages}", callback_data="current_page"))
    
    if page < total_pages - 1:
        pagination_buttons.append(InlineKeyboardButton(text="➡️", callback_data=f"reports_list_page_{page+1}"))
    
    if pagination_buttons:
        keyboard.append(pagination_buttons)
    
    keyboard.append([InlineKeyboardButton(text="📅 К датам", callback_data="back_to_dates")])
    keyboard.append([InlineKeyboardButton(text="⬅️ В меню", callback_data="statistics_menu")])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_cancel_edit_keyboard():
    """Клавиатура для отмены редактирования"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_edit")]
    ])

def get_students_menu_keyboard():
    """Клавиатура главного меню учеников"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Редактировать отчеты", callback_data="edit_reports")],
        [InlineKeyboardButton(text="📊 Посмотреть статистику", callback_data="view_statistics")],
        [InlineKeyboardButton(text="👨‍🎓 Управление учениками", callback_data="manage_students")],
        [InlineKeyboardButton(text="🏠 В главное меню", callback_data="main_menu")]
    ])

def get_report_edit_keyboard(report_id):
    """Клавиатура для редактирования отчета"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Присутствие", callback_data=f"toggle_attendance_{report_id}"),
            InlineKeyboardButton(text="💰 Оплата", callback_data=f"toggle_payment_{report_id}")
        ],
        [
            InlineKeyboardButton(text="📚 ДЗ", callback_data=f"toggle_homework_{report_id}"),
            InlineKeyboardButton(text="📝 Коммент ученику", callback_data=f"edit_student_comment_{report_id}")
        ],
        [
            InlineKeyboardButton(text="👨‍👩‍👧‍👦 Заметка родителям", callback_data=f"edit_parent_comment_{report_id}")
        ],
        [
            InlineKeyboardButton(text="⬅️ Назад к отчетам", callback_data="back_to_reports"),
            InlineKeyboardButton(text="📅 К датам", callback_data="back_to_dates")
        ],
        [
            InlineKeyboardButton(text="🏠 В меню", callback_data="statistics_menu")
        ]
    ])
