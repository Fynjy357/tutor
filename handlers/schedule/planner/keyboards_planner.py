# handlers/schedule/planner/keyboards_planner.py
from aiogram import types
from aiogram.utils.keyboard import InlineKeyboardBuilder

def get_planner_keyboard():
    """Основная клавиатура планера"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        types.InlineKeyboardButton(
            text="➕ Добавить регулярное занятие",
            callback_data="planner_add_task"
        )
    )
    builder.row(
        types.InlineKeyboardButton(
            text="📋 Мои регулярные занятия",
            callback_data="planner_view_tasks"
        )
    )
    # builder.row(
    #     types.InlineKeyboardButton(
    #         text="⚙️ Управление задачами",
    #         callback_data="planner_manage_tasks"
    #     )
    # )
    builder.row(
        types.InlineKeyboardButton(
            text="◀️ Назад к расписанию",
            callback_data="back_to_schedule"
        )
    )
    
    return builder.as_markup()

def get_management_keyboard(has_tasks: bool = False):
    """Клавиатура управления задачами"""
    builder = InlineKeyboardBuilder()
    
    if has_tasks:
        builder.row(
            types.InlineKeyboardButton(
                text="❌ Деактивировать задачу",
                callback_data="planner_deactivate_task"
            )
        )
        builder.row(
            types.InlineKeyboardButton(
                text="🗑️ Удалить задачу",
                callback_data="planner_delete_task"
            )
        )
    
    builder.row(
        types.InlineKeyboardButton(
            text="📋 Посмотреть задачи",
            callback_data="planner_view_tasks"
        )
    )
    builder.row(
        types.InlineKeyboardButton(
            text="◀️ Назад",
            callback_data="back_to_planner"
        )
    )
    
    return builder.as_markup()

def get_back_to_planner_keyboard():
    """Клавиатура с кнопкой назад в планер"""
    builder = InlineKeyboardBuilder()
    builder.row(
        types.InlineKeyboardButton(
            text="◀️ Назад",
            callback_data="back_to_planner"
        )
    )
    return builder.as_markup()
