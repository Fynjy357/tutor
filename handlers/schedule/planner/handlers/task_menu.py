# handlers/schedule/planner/handlers/task_menu.py
from aiogram import Router, F
from aiogram.types import CallbackQuery
import logging

from handlers.schedule.planner.utils.task_helpers import get_task_by_id, show_task_edit_menu
from database import db


router = Router()
logger = logging.getLogger(__name__)

@router.callback_query(F.data.startswith("planner_menu_"))
async def planner_edit_task_menu(callback: CallbackQuery):
    """Открывает меню редактирования конкретной задачи"""
    logger.debug(f"DEBUG: callback.data = {callback.data}")
    try:
        # Безопасное извлечение task_id
        parts = callback.data.split("_")
        if len(parts) < 3:
            await callback.answer("❌ Неверный формат данных", show_alert=True)
            return
        
        task_id_str = parts[2]
        if not task_id_str.isdigit():
            await callback.answer("❌ Неверный ID задачи", show_alert=True)
            return
            
        task_id = int(task_id_str)
        
        # Получаем информацию о задаче
        task = get_task_by_id(task_id)
        if not task:
            await callback.answer("❌ Задача не найдена", show_alert=True)
            return
        
        await show_task_edit_menu(callback, task)
        
    except Exception as e:
        logger.error(f"Ошибка при обработке редактирования задачи: {e}")
        await callback.answer("❌ Ошибка при открытии задачи", show_alert=True)

@router.callback_query(F.data.startswith("planner_deactivate_"))
async def planner_deactivate(callback: CallbackQuery):
    """Деактивирует задачу и обновляет меню на месте"""
    try:
        task_id = int(callback.data.split("_")[2])
        
        # Обновляем статус задачи в базе данных
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE planner_actions SET is_active = FALSE WHERE id = ?",
                (task_id,)
            )
            conn.commit()
        
        # Получаем обновленную задачу и показываем обновленное меню
        task = get_task_by_id(task_id)
        if task:
            await show_task_edit_menu(callback, task)
            await callback.answer("✅ Задача приостановлена")
        else:
            await callback.answer("❌ Ошибка: задача не найдена", show_alert=True)
        
    except Exception as e:
        logger.error(f"Ошибка при деактивации задачи: {e}")
        await callback.answer("❌ Ошибка при приостановке задачи", show_alert=True)

@router.callback_query(F.data.startswith("planner_activate_"))
async def planner_activate(callback: CallbackQuery):
    """Активирует задачу и обновляет меню на месте"""
    try:
        task_id = int(callback.data.split("_")[2])
        
        # Обновляем статус задачи в базе данных
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE planner_actions SET is_active = TRUE WHERE id = ?",
                (task_id,)
            )
            conn.commit()
        
        # Получаем обновленную задачу и показываем обновленное меню
        task = get_task_by_id(task_id)
        if task:
            await show_task_edit_menu(callback, task)
            await callback.answer("✅ Задача активирована")
        else:
            await callback.answer("❌ Ошибка: задача не найдена", show_alert=True)
        
    except Exception as e:
        logger.error(f"Ошибка при активации задачи: {e}")
        await callback.answer("❌ Ошибка при активации задачи", show_alert=True)
