from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage
import asyncio
import logging

from config import BOT_TOKEN
from handlers.start import router as start_router
from handlers.registration import router as registration_router
from handlers.about import router as about_router

# Настройка логирования
logging.basicConfig(level=logging.INFO)

async def main():
    # Проверяем, установлен ли токен
    if not BOT_TOKEN:
        logging.error("Токен бота не найден! Убедитесь, что файл .env существует и содержит BOT_TOKEN")
        return

    # Инициализация бота и диспетчера
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
    dp = Dispatcher(storage=MemoryStorage())

    # Регистрируем обработчики
    dp.include_router(start_router)
    dp.include_router(registration_router)
    dp.include_router(about_router)

    # Запускаем бота
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())