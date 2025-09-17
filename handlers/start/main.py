from aiogram import Router, types
from aiogram.types import Message
from aiogram.filters import CommandStart
import logging

from handlers.start.deep_links import handle_deep_link
from handlers.start.welcome import show_welcome_message

router = Router()
logger = logging.getLogger(__name__)

@router.message(CommandStart())
async def handle_start(message: Message):
    """Единый обработчик для команды /start"""
    logger.info(f"Обработчик /start вызван для пользователя {message.from_user.id}")
    
    if len(message.text.split()) > 1:
        # Это deep link - обрабатываем приглашения
        is_deep_link_processed = await handle_deep_link(message)
        if is_deep_link_processed:
            return  # ⬅️ ВАЖНО: завершаем выполнение если deep link обработан
    
    # Обычная команда /start (или нераспознанный deep link)
    await show_welcome_message(message)