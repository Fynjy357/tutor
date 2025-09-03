from aiogram import Router, types
from aiogram.filters import CommandStart
import logging

from handlers.start.deep_links import handle_deep_link
from handlers.start.welcome import show_welcome_message

router = Router()
logger = logging.getLogger(__name__)

@router.message(CommandStart())
async def handle_start(message: types.Message):
    """Единый обработчик для команды /start"""
    
    args = message.text.split()
    
    if len(args) > 1:
        # Это deep link - обрабатываем приглашения
        await handle_deep_link(message, args[1])
    else:
        # Обычная команда /start
        await show_welcome_message(message)