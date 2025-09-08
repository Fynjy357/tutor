import logging
from aiogram import Dispatcher
from database import Database


logger = logging.getLogger(__name__)

def setup_notification_handlers(dp: Dispatcher, db: Database, notification_manager, bot):
    """Настройка обработчиков уведомлений"""
    # Здесь могут быть другие обработчики уведомлений
    
    # Импортируем и регистрируем обработчики подтверждений
    from .confirmation_handlers import register_confirmation_handlers
    register_confirmation_handlers(dp, notification_manager, bot)
    logger.info("✅ Обработчики уведомлений настроены")