from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage
import asyncio
import logging

from config import BOT_TOKEN
from handlers.start import start_router
from handlers.start import about_router
from handlers.registration import registration_router
from handlers.students.edit_handlers import router as edit_students_router
from handlers.students.handlers import router as add_students_router
from handlers.students.main import router as students_router
from handlers.students.invitations import router as invitations_router
from handlers.groups.handlers import router as groups_router
from handlers.schedule import setup_schedule_handlers


from database import db 

# Настройка логирования
logging.basicConfig(level=logging.INFO)


async def main():
    if not BOT_TOKEN:
        logging.error("Токен бота не найден!")
        return

    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
    dp = Dispatcher(storage=MemoryStorage())

    dp.include_router(start_router)
    dp.include_router(registration_router)
    dp.include_router(edit_students_router)
    dp.include_router(about_router)
    dp.include_router(students_router)
    dp.include_router(invitations_router)
    dp.include_router(add_students_router)
    # ТОЛЬКО ОДИН роутер расписания (включает все подмодули)
    schedule_router = setup_schedule_handlers()
    dp.include_router(schedule_router)
    dp.include_router(groups_router)

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())