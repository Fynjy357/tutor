# handlers/schedule/planner/handlers/view_tasks.py
from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
import logging

from handlers.schedule.planner.keyboards_planner import get_planner_keyboard
from handlers.schedule.planner.utils.task_helpers import get_planner_tasks
from database import db


router = Router()
logger = logging.getLogger(__name__)

@router.callback_query(F.data == "back_to_planner")
async def back_to_planner_handler(callback: CallbackQuery):
    """Возвращает в главное меню планера"""
    try:
        await callback.message.edit_text(
            "📅 <b>Планировщик занятий</b>\n\n"
            "Автоматически создавайте занятия по расписанию.\n\n"
            "Выберите действие:",
            reply_markup=get_planner_keyboard()
        )
        await callback.answer()
    except Exception as e:
        logger.error(f"Ошибка при возврате в планер: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)

@router.callback_query(F.data == "planner_view_tasks")
async def planner_view_tasks(callback: CallbackQuery):
    """Показывает список активных задач в планере с кнопками для редактирования"""
    tutor_id = db.get_tutor_id_by_telegram_id(callback.from_user.id)
    if not tutor_id:
        await callback.answer("❌ Ошибка: репетитор не найден", show_alert=True)
        return
    
    tasks = get_planner_tasks(tutor_id)
    
    if not tasks:
        # Создаем клавиатуру БЕЗ кнопки "Мои регулярные задачи"
        keyboard_without_tasks = InlineKeyboardBuilder()
        keyboard_without_tasks.row(
            InlineKeyboardButton(text="➕ Добавить задачу", callback_data="planner_add_task")
        )
        keyboard_without_tasks.row(
            InlineKeyboardButton(text="◀️ Назад в меню", callback_data="back_to_main_menu")
        )
        
        await callback.message.edit_text(
            "🔄 <b>Регулярные занятия</b>\n\n"
            "У вас пока нет регулярных занятий.\n\n"
            "Добавьте первое регулярное занятие, чтобы автоматически создавать занятия по расписанию.",
            reply_markup=keyboard_without_tasks.as_markup()
        )
        await callback.answer()
        return
    
    # Создаем клавиатуру с задачами
    builder = InlineKeyboardBuilder()
    
    weekdays_ru = {
        'monday': 'Пн', 'tuesday': 'Вт', 'wednesday': 'Ср',
        'thursday': 'Чт', 'friday': 'Пт', 'saturday': 'Сб', 'sunday': 'Вс'
    }
    
    # Группируем задачи по дням недели для лучшего отображения
    tasks_by_day = {}
    for task in tasks:
        day = task['weekday']
        if day not in tasks_by_day:
            tasks_by_day[day] = []
        tasks_by_day[day].append(task)
    
    # Сортируем дни по порядку
    weekdays_order = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
    
    active_count = 0
    inactive_count = 0
    
    for day in weekdays_order:
        if day in tasks_by_day:
            # Добавляем заголовок дня
            builder.row(
                InlineKeyboardButton(
                    text=f"📅 {weekdays_ru[day].upper()}",
                    callback_data=f"planner_day_header_{day}"
                )
            )
            
            # Добавляем задачи этого дня
            day_tasks = sorted(tasks_by_day[day], key=lambda x: x['time'])
            for task in day_tasks:
                # Определяем индикатор активности
                status_icon = "🟢" if task['is_active'] else "🔴"
                task_type = "👤" if task['lesson_type'] == 'individual' else "👥"
                target = task['student_name'] if task['student_name'] else task['group_name']
                time_display = task['time']
                
                # Считаем активные/неактивные задачи
                if task['is_active']:
                    active_count += 1
                else:
                    inactive_count += 1
                
                builder.row(
                    InlineKeyboardButton(
                        text=f"{status_icon} {time_display} | {task_type} {target}",
                        callback_data=f"planner_menu_{task['id']}"
                    )
                )
    
    builder.row(
        InlineKeyboardButton(
            text="◀️ Назад",
            callback_data="back_to_planner"
        )
    )
    
    await callback.message.edit_text(
        f"📋 <b>Выберите занятие для дальнейшего редактирования</b>\n\n"
        f"🟢 Активных: <b>{active_count}</b>\n"
        f"🔴 Неактивных: <b>{inactive_count}</b>\n"
        f"📊 Всего: <b>{len(tasks)}</b>\n\n",
        reply_markup=builder.as_markup()
    )
    await callback.answer()
