# handlers/schedule/planner/timer/planner_commands.py
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
import logging
from datetime import datetime

from commands.config import SUPER_ADMIN_ID
from .planner_manager import planner_manager
from database import db
from payment.models import PaymentManager  # Добавляем импорт

router = Router()
logger = logging.getLogger(__name__)

@router.message(Command("planner_status"))
async def planner_status(message: Message):
    """Показывает статус планера с информацией о задачах и подписках"""
    if message.from_user.id != SUPER_ADMIN_ID:
        await message.answer("❌ Эта команда доступна только супер-администратору")
        return
    
    status = planner_manager.get_planner_status()
    tasks_info = await _get_planner_tasks_info()
    subscription_info = await _get_subscription_info()
    
    status_text = "🟢 <b>Планер активен</b>" if status['is_running'] else "🔴 <b>Планер остановлен</b>"
    status_text += f"\n\n📊 <b>Статистика задач:</b>"
    status_text += f"\n• Всего активных: <b>{tasks_info['active_count']}</b>"
    status_text += f"\n• С подпиской: <b>{subscription_info['with_subscription']}</b>"
    status_text += f"\n• Без подписки: <b>{subscription_info['without_subscription']}</b>"
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

@router.message(Command("update_tutor_planner"))
async def update_tutor_planner_command(message: Message):
    """Принудительно обновляет статус планера для репетитора"""
    if message.from_user.id != SUPER_ADMIN_ID:
        await message.answer("❌ Эта команда доступна только супер-администратору")
        return
    
    try:
        # Парсим аргументы команды: /update_tutor_planner <telegram_id> <1/0>
        args = message.text.split()
        if len(args) != 3:
            await message.answer("❌ Использование: /update_tutor_planner <telegram_id> <1/0>")
            return
        
        telegram_id = int(args[1])
        has_subscription = bool(int(args[2]))
        
        success = await planner_manager.update_tutor_planner_status(telegram_id, has_subscription)
        
        if success:
            status = "включен" if has_subscription else "отключен"
            await message.answer(f"✅ Планер {status} для репетитора {telegram_id}")
        else:
            await message.answer(f"❌ Ошибка при обновлении статуса для репетитора {telegram_id}")
            
    except (ValueError, IndexError) as e:
        await message.answer("❌ Ошибка в формате команды. Использование: /update_tutor_planner <telegram_id> <1/0>")
    except Exception as e:
        logger.error(f"Ошибка в команде update_tutor_planner: {e}")
        await message.answer("❌ Ошибка при выполнении команды")

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

async def _get_subscription_info() -> dict:
    """Получает информацию о подписках репетиторов с активными задачами"""
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            # Получаем всех репетиторов с активными задачами планера
            cursor.execute('''
            SELECT DISTINCT t.telegram_id 
            FROM tutors t 
            JOIN planner_actions pa ON pa.tutor_id = t.id 
            WHERE pa.is_active = TRUE
            ''')
            tutors = cursor.fetchall()
            
            with_subscription = 0
            without_subscription = 0
            
            # Проверяем подписку для каждого репетитора
            for tutor in tutors:
                telegram_id = tutor[0] if isinstance(tutor, tuple) else tutor['telegram_id']
                
                has_subscription = await PaymentManager.check_subscription(telegram_id)
                
                if has_subscription:
                    with_subscription += 1
                else:
                    without_subscription += 1
            
            return {
                'with_subscription': with_subscription,
                'without_subscription': without_subscription
            }
            
    except Exception as e:
        logger.error(f"Ошибка при получении информации о подписках: {e}")
        return {'with_subscription': 0, 'without_subscription': 0}
