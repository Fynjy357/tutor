import asyncio
import logging
from aiogram import Bot
from .trial_notifications import TrialNotificationManager

logger = logging.getLogger(__name__)

async def start_trial_notification_task(bot: Bot):
    """Запускает задачу проверки уведомлений о пробном периоде"""
    notification_manager = TrialNotificationManager(bot)
    
    logger.info("Задача уведомлений о пробном периоде запущена")
    
    while True:
        try:
            # Очищаем старые уведомления
            await notification_manager.cleanup_expired_notifications()
            # Отправляем новые уведомления
            await notification_manager.check_and_send_trial_notifications()
        except Exception as e:
            logger.error(f"Ошибка в задаче уведомлений: {e}")
        
        # Проверяем каждые 6 часов
        await asyncio.sleep(6 * 60 * 60)