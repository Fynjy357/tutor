# handlers/schedule/planner/timer/planner_commands.py
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
import logging
from datetime import datetime

from commands.config import SUPER_ADMIN_ID
from .planner_manager import planner_manager
from database import db

router = Router()
logger = logging.getLogger(__name__)

@router.message(Command("planner_status"))
async def planner_status(message: Message):
    """Показывает статус планера с информацией о задачах"""
    if message.from_user.id != SUPER_ADMIN_ID:
        await message.answer("❌ Эта команда доступна только супер-администратору")
        return
    
    status = planner_manager.get_planner_status()
    tasks_info = await _get_planner_tasks_info()
    
    status_text = "🟢 <b>Планер активен</b>" if status['is_running'] else "🔴 <b>Планер остановлен</b>"
    status_text += f"\n📊 Активных задач: <b>{tasks_info['active_count']}</b>"
    status_text += f"\n🔄 Последнее создание: <b>{tasks_info['last_created_info']}</b>"
    
    if status['last_check']:
        status_text += f"\n📅 Последняя проверка: {status['last_check']}"
    
    await message.answer(status_text)

@router.message(Command("start_planner"))
async def start_planner_command(message: Message):
    """Запускает планер"""
    if message.from_user.id != SUPER_ADMIN_ID:
        await message.answer("❌ Эта команда доступна только супер-администратору")
        return
    
    success = await planner_manager.start_planner()
    if success:
        await message.answer("✅ Планер успешно запущен")
    else:
        await message.answer("❌ Ошибка при запуске планера")

@router.message(Command("stop_planner"))
async def stop_planner_command(message: Message):
    """Останавливает планер"""
    if message.from_user.id != SUPER_ADMIN_ID:
        await message.answer("❌ Эта команда доступна только супер-администратору")
        return
    
    success = await planner_manager.stop_planner()
    if success:
        await message.answer("✅ Планер успешно остановлен")
    else:
        await message.answer("❌ Ошибка при остановке планера")

@router.message(Command("force_planner_check"))
async def force_planner_check(message: Message):
    """Принудительная проверка планера"""
    if message.from_user.id != SUPER_ADMIN_ID:
        await message.answer("❌ Эта команда доступна только супер-администратору")
        return
    
    success = await planner_manager.force_check()
    if success:
        await message.answer("✅ Принудительная проверка планера выполнена")
    else:
        await message.answer("❌ Ошибка при принудительной проверке")

async def _get_planner_tasks_info() -> dict:
    """Получает информацию о задачах планера"""
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
            SELECT COUNT(*) as active_count,
                   MAX(last_created) as latest_creation
            FROM planner_actions 
            WHERE is_active = TRUE
            ''')
            result = cursor.fetchone()
            
            last_created = result[0] if isinstance(result, tuple) else result['latest_creation']
            if last_created:
                # Форматируем дату для читаемости
                last_created_dt = datetime.fromisoformat(last_created.replace('Z', '+00:00'))
                last_created_info = last_created_dt.strftime('%d.%m.%Y %H:%M')
            else:
                last_created_info = "никогда"
            
            active_count = result[0] if isinstance(result, tuple) else result['active_count']
            
            return {
                'active_count': active_count,
                'last_created_info': last_created_info
            }
    except Exception as e:
        logger.error(f"Ошибка при получении информации о задачах: {e}")
        return {'active_count': 0, 'last_created_info': 'ошибка'}
