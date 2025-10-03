# handlers/schedule/planner/handlers/delete_tasks.py
from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
import logging

from handlers.schedule.planner.utils.task_helpers import get_planner_tasks, get_task_by_id
from database import db


router = Router()
logger = logging.getLogger(__name__)

@router.callback_query(F.data.startswith("planner_delete_confirm_"))
async def planner_delete_confirm(callback: CallbackQuery):
    """Показывает подтверждение удаления задачи"""
    task_id = int(callback.data.split("_")[3])
    
    # Получаем информацию о задаче для подтверждения
    task = get_task_by_id(task_id)
    if not task:
        await callback.answer("❌ Задача не найдена", show_alert=True)
        return
    
    task_type = "Индивидуальное" if task['lesson_type'] == 'individual' else "Групповое"
    target = task['student_name'] if task['student_name'] else task['group_name']
    
    await callback.message.edit_text(
        f"🗑️ <b>Подтверждение удаления</b>\n\n"
        f"Вы уверены, что хотите удалить задачу?\n\n"
        f"<b>Тип:</b> {task_type}\n"
        f"<b>Ученик/Группа:</b> {target}\n"
        f"<b>Время:</b> {task['time']}\n"
        f"<b>День:</b> {task['weekday']}\n\n"
        f"<i>Это действие нельзя отменить!</i>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Да, удалить", callback_data=f"planner_delete_{task_id}"),
                InlineKeyboardButton(text="❌ Отмена", callback_data=f"planner_menu_{task_id}")
            ]
        ])
    )
    await callback.answer()

@router.callback_query(F.data.startswith("planner_delete_"))
async def planner_delete_task(callback: CallbackQuery):
    """Удаляет задачу и все связанные занятия, возвращает к списку задач"""
    try:
        task_id = int(callback.data.split("_")[2])
        
        # Сохраняем информацию о задаче перед удалением
        task = get_task_by_id(task_id)
        if not task:
            await callback.answer("❌ Задача не найдена", show_alert=True)
            return
        
        # Удаляем все занятия, созданные этим планером
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            # Сначала получаем количество УНИКАЛЬНЫХ занятий для удаления
            # Группируем по уникальным идентификаторам занятий (group_id или student_id)
            cursor.execute('''
                SELECT COUNT(DISTINCT 
                    CASE 
                        WHEN group_id IS NOT NULL THEN 'group_' || group_id || '_' || lesson_date
                        ELSE 'individual_' || student_id || '_' || lesson_date
                    END
                ) 
                FROM lessons 
                WHERE planner_action_id = ? AND status != 'completed'
            ''', (task_id,))
            unique_lessons_count = cursor.fetchone()[0]
            
            # Получаем информацию о типах удаляемых занятий для отчета
            cursor.execute('''
                SELECT 
                    COUNT(DISTINCT group_id) as group_lessons_count,
                    COUNT(DISTINCT CASE WHEN group_id IS NULL THEN student_id END) as individual_lessons_count
                FROM lessons 
                WHERE planner_action_id = ? AND status != 'completed'
            ''', (task_id,))
            stats = cursor.fetchone()
            group_lessons_count = stats[0] if stats[0] else 0
            individual_lessons_count = stats[1] if stats[1] else 0
            
            # Удаляем занятия
            cursor.execute('''
                DELETE FROM lessons 
                WHERE planner_action_id = ? AND status != 'completed'
            ''', (task_id,))
            
            # Удаляем саму задачу планера
            cursor.execute("DELETE FROM planner_actions WHERE id = ?", (task_id,))
            
            conn.commit()
        
        # Возвращаемся к списку задач
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
            
            delete_message = (
                "🔄 <b>Регулярные занятия</b>\n\n"
                "✅ Задача успешно удалена\n"
            )
            
            if unique_lessons_count > 0:
                delete_message += f"🗑️ Удалено занятий: <b>{unique_lessons_count}</b>\n"
                if group_lessons_count > 0:
                    delete_message += f"👥 Групповых: <b>{group_lessons_count}</b>\n"
                if individual_lessons_count > 0:
                    delete_message += f"👤 Индивидуальных: <b>{individual_lessons_count}</b>\n"
                delete_message += "\n"
            else:
                delete_message += "\n"
                
            delete_message += (
                "У вас больше нет регулярных занятий.\n\n"
                "Добавьте первое регулярное занятие, чтобы автоматически создавать занятия по расписанию."
            )
            
            await callback.message.edit_text(
                delete_message,
                reply_markup=keyboard_without_tasks.as_markup()
            )
            await callback.answer("✅ Задача удалена")
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
        
        success_message = (
            f"📋 <b>Выберите занятие для дальнейшего редактирования</b>\n\n"
            f"✅ Задача успешно удалена\n"
        )
        
        if unique_lessons_count > 0:
            success_message += f"🗑️ Удалено занятий: <b>{unique_lessons_count}</b>\n"
            if group_lessons_count > 0:
                success_message += f"👥 Групповых: <b>{group_lessons_count}</b>\n"
            if individual_lessons_count > 0:
                success_message += f"👤 Индивидуальных: <b>{individual_lessons_count}</b>\n"
            success_message += "\n"
        else:
            success_message += "\n"
            
        success_message += (
            f"🟢 Активных: <b>{active_count}</b>\n"
            f"🔴 Неактивных: <b>{inactive_count}</b>\n"
            f"📊 Всего: <b>{len(tasks)}</b>\n\n"
        )
        
        await callback.message.edit_text(
            success_message,
            reply_markup=builder.as_markup()
        )
        await callback.answer("✅ Задача удалена")
        
    except Exception as e:
        logger.error(f"Ошибка при удалении задачи: {e}")
        await callback.answer("❌ Ошибка при удалении задачи", show_alert=True)


