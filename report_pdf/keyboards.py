from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

def get_statistics_keyboard():
    """Клавиатура для раздела статистики"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(
            text="💰 Задолженности по оплате", 
            callback_data="new_payment_debts_menu"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="📚 Долги по домашним работам", 
            callback_data="new_homework_debts_menu"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="📝 Редактировать отчеты",
            callback_data="edit_reports"
        )
    )
    # builder.row(
    #     InlineKeyboardButton(
    #         text="📊 Отчеты", 
    #         callback_data="reports_menu"
    #     )
    # )
    # builder.row(
    #     InlineKeyboardButton(
    #         text="🗓️ Расписание", 
    #         callback_data="schedule_menu"
    #     )
    # )
    builder.row(
        InlineKeyboardButton(
            text="⬅️ Назад в главное меню", 
            callback_data="main_menu"
        )
    )

    return builder.as_markup()

def get_reports_months_keyboard(available_months):
    """Клавиатура для выбора месяца отчета"""
    builder = InlineKeyboardBuilder()
    
    for month_data in available_months:
        year = month_data.get('year')
        month = month_data.get('month')
        month_name = month_data.get('name', f'Месяц {month}')
        
        if year and month:
            builder.row(
                InlineKeyboardButton(
                    text=f"{month_name} {year}",
                    callback_data=f"report_month_{year}_{month}"
                )
            )
    
    builder.row(
        InlineKeyboardButton(
            text="⬅️ Назад", 
            callback_data="statistics_menu"
        )
    )
    
    return builder.as_markup()

def get_schedule_months_keyboard(available_months):
    """Клавиатура для выбора месяца расписания"""
    builder = InlineKeyboardBuilder()
    
    for month_data in available_months:
        year = month_data.get('year')
        month = month_data.get('month')
        month_name = month_data.get('name', f'Месяц {month}')
        
        if year and month:
            builder.row(
                InlineKeyboardButton(
                    text=f"{month_name} {year}",
                    callback_data=f"schedule_month_{year}_{month}"
                )
            )
    
    builder.row(
        InlineKeyboardButton(
            text="⬅️ Назад", 
            callback_data="statistics_menu"
        )
    )
    
    return builder.as_markup()

def get_back_to_statistics_keyboard():
    """Клавиатура для возврата в меню статистики"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(
            text="⬅️ Назад в статистику", 
            callback_data="statistics_menu"
        )
    )
    
    return builder.as_markup()


