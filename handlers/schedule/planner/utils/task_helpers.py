# handlers/schedule/planner/utils/task_helpers.py
from aiogram.types import CallbackQuery, Message, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from database import db


def get_planner_tasks(tutor_id: int):
    """Получает задачи из планера"""
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
            SELECT pa.*, 
                   s.full_name as student_name,
                   g.name as group_name
            FROM planner_actions pa
            LEFT JOIN students s ON pa.student_id = s.id
            LEFT JOIN groups g ON pa.group_id = g.id
            WHERE pa.tutor_id = ?
            ORDER BY pa.weekday, pa.time
            ''', (tutor_id,))
            
            return cursor.fetchall()
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Ошибка при получении задач планера: {e}")
        return []

def get_task_by_id(task_id: int):
    """Получает задачу по ID"""
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
            SELECT pa.*, 
                   s.full_name as student_name,
                   g.name as group_name
            FROM planner_actions pa
            LEFT JOIN students s ON pa.student_id = s.id
            LEFT JOIN groups g ON pa.group_id = g.id
            WHERE pa.id = ?
            ''', (task_id,))
            
            return cursor.fetchone()
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Ошибка при получении задачи: {e}")
        return None

async def show_task_edit_menu(callback: CallbackQuery, task):
    """Показывает меню редактирования задачи"""
    weekdays_ru = {
        'monday': 'Понедельник', 'tuesday': 'Вторник', 'wednesday': 'Среда',
        'thursday': 'Четверг', 'friday': 'Пятница', 'saturday': 'Суббота', 'sunday': 'Воскресенье'
    }
    
    task_type = "Индивидуальное занятие" if task['lesson_type'] == 'individual' else "Групповое занятие"
    target = task['student_name'] if task['student_name'] else task['group_name']
    
    status_emoji = "🟢" if task['is_active'] else "🔴"
    status_text = "Активно" if task['is_active'] else "Приостановлено"
    
    # НОВЫЙ ФОРМАТ СООБЩЕНИЯ
    task_info = (
        f"📋 <b>Редактирование регулярного занятия</b>\n"
        f"─────────────────────────────────────\n"
        f"{status_emoji} <b>Статус:</b> {status_text}\n"
        f"🎯 <b>Тип:</b> {task_type}\n"
        f"👤 <b>Ученик:</b> {target}\n"
        f"─────────────────────────────────────\n"
        f"📅 <b>День:</b> {weekdays_ru[task['weekday']]}\n"
        f"⏰ <b>Время:</b> {task['time']}\n"
        f"⏱️ <b>Длительность:</b> {task['duration']} минут\n"
        f"💰 <b>Стоимость:</b> {int(task['price'])} руб\n"
        f"─────────────────────────────────────"
    )
    
    builder = InlineKeyboardBuilder()
    
    # Основные действия
    builder.row(
        InlineKeyboardButton(
            text="✏️ Изменить время",
            callback_data=f"planner_time_{task['id']}"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="⏱️ Изменить длительность",
            callback_data=f"planner_duration_{task['id']}"
        ),
        InlineKeyboardButton(
            text="💰 Изменить стоимость",
            callback_data=f"planner_price_{task['id']}"
        )
    )
    
    # Управление статусом
    if task['is_active']:
        builder.row(
            InlineKeyboardButton(
                text="⏸️ Приостановить",
                callback_data=f"planner_deactivate_{task['id']}"
            )
        )
    else:
        builder.row(
            InlineKeyboardButton(
                text="▶️ Активировать",
                callback_data=f"planner_activate_{task['id']}"
            )
        )
    
    builder.row(
        InlineKeyboardButton(
            text="🗑️ Удалить задачу",
            callback_data=f"planner_delete_confirm_{task['id']}"
        )
    )
    
    builder.row(
        InlineKeyboardButton(
            text="◀️ Назад к списку",
            callback_data="planner_view_tasks"
        )
    )
    
    await callback.message.edit_text(task_info, reply_markup=builder.as_markup())
    await callback.answer()


async def show_task_edit_menu_after_edit(message: Message, task):
    """Показывает меню редактирования после успешного изменения"""
    weekdays_ru = {
        'monday': 'Понедельник', 'tuesday': 'Вторник', 'wednesday': 'Среда',
        'thursday': 'Четверг', 'friday': 'Пятница', 'saturday': 'Суббота', 'sunday': 'Воскресеньe'
    }
    
    task_type = "Индивидуальное занятие" if task['lesson_type'] == 'individual' else "Групповое занятие"
    target = task['student_name'] if task['student_name'] else task['group_name']
    
    status_emoji = "🟢" if task['is_active'] else "🔴"
    status_text = "Активно" if task['is_active'] else "Приостановлено"
    
    # НОВЫЙ ФОРМАТ СООБЩЕНИЯ
    task_info = (
        f"📋 <b>Редактирование регулярного занятия</b>\n"
        f"─────────────────────────────────────\n"
        f"{status_emoji} <b>Статус:</b> {status_text}\n"
        f"🎯 <b>Тип:</b> {task_type}\n"
        f"👤 <b>Ученик:</b> {target}\n"
        f"─────────────────────────────────────\n"
        f"📅 <b>День:</b> {weekdays_ru[task['weekday']]}\n"
        f"⏰ <b>Время:</b> {task['time']}\n"
        f"⏱️ <b>Длительность:</b> {task['duration']} минут\n"
        f"💰 <b>Стоимость:</b> {int(task['price'])} руб\n"
        f"─────────────────────────────────────"
    )
    
    builder = InlineKeyboardBuilder()
    
    # Основные действия
    builder.row(InlineKeyboardButton(text="✏️ Изменить время", callback_data=f"planner_time_{task['id']}"))
    builder.row(
        InlineKeyboardButton(text="⏱️ Изменить длительность", callback_data=f"planner_duration_{task['id']}"),
        InlineKeyboardButton(text="💰 Изменить стоимость", callback_data=f"planner_price_{task['id']}")
    )
    
    if task['is_active']:
        builder.row(InlineKeyboardButton(text="⏸️ Приостановить", callback_data=f"planner_deactivate_{task['id']}"))
    else:
        builder.row(InlineKeyboardButton(text="▶️ Активировать", callback_data=f"planner_activate_{task['id']}"))
    
    builder.row(InlineKeyboardButton(text="🗑️ Удалить задачу", callback_data=f"planner_delete_confirm_{task['id']}"))
    builder.row(InlineKeyboardButton(text="◀️ Назад к списку", callback_data="planner_view_tasks"))
    
    await message.answer(task_info, reply_markup=builder.as_markup())

