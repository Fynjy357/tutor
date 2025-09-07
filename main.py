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
from notify import NotificationManager, lesson_notification_scheduler, setup_notification_handlers, register_confirmation_handlers
# Импортируем систему отчетов по занятиям
from lesson_reports.handlers import LessonReportHandlers


from database import db 

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

async def main():
    if not BOT_TOKEN:
        logging.error("Токен бота не найден!")
        return

    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode="HTML")
        )
    dp = Dispatcher(storage=MemoryStorage())

    # ИНИЦИАЛИЗАЦИЯ МЕНЕДЖЕРА УВЕДОМЛЕНИЙ - создаем экземпляр менеджера уведомлений
    notification_manager = NotificationManager(db)

    # ИНИЦИАЛИЗАЦИЯ ОБРАБОТЧИКОВ ОТЧЕТОВ ПО ЗАНЯТИЯМ
    lesson_report_handlers = LessonReportHandlers(db)

    # ПРОВЕРКА ФОРМАТА ДАТ - добавляем эту проверку
    notification_manager.check_lesson_dates_format()

    # НАСТРОЙКА ОБРАБОТЧИКОВ УВЕДОМЛЕНИЙ - регистрируем обработчики подтверждений
    setup_notification_handlers(dp, db, notification_manager, bot)

    register_confirmation_handlers(dp, notification_manager, bot)
    
    # РЕГИСТРАЦИЯ ОБРАБОТЧИКОВ ОТЧЕТОВ
    dp.include_router(lesson_report_handlers.router)


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

    

    # ЗАПУСК ПЛАНИРОВЩИКА УВЕДОМЛЕНИЙ - запускаем фоновую задачу для уведомлений
    asyncio.create_task(lesson_notification_scheduler(bot, notification_manager))

    # ЗАПУСК ФОНОВОЙ ЗАДАЧИ ДЛЯ УВЕДОМЛЕНИЙ О ЗАВЕРШЕНИИ ЗАНЯТИЙ
    asyncio.create_task(lesson_report_handlers.notify_tutor_about_lesson_end(bot))



    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())