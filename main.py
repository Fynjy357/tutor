from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage
import asyncio
import logging
import signal
import sys
import traceback

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
from lesson_reports.handlers import LessonReportHandlers
from keyboards import main_menu # на время разработки кнопок
from database import db 
from payment.middleware import SubscriptionMiddleware
from payment.handlers import router as payment_router
from handlers.admin.admin import router as admin_router
from handlers.start.handlers_parent import parent_router
from handlers.start.handlers_student_by_student import student_router

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class BotApp:
    def __init__(self):
        self.bot = None
        self.dp = None
        self.notification_manager = None
        self.lesson_report_handlers = None
        self.tasks = []
        self.is_running = False

    async def startup(self):
        """Инициализация приложения"""
        if not BOT_TOKEN:
            logger.error("Токен бота не найден!")
            return False

        try:
            self.bot = Bot(
                token=BOT_TOKEN,
                default=DefaultBotProperties(parse_mode="HTML")
            )
            self.dp = Dispatcher(storage=MemoryStorage())

            # Инициализация менеджера уведомлений
            self.notification_manager = NotificationManager(db)
            
            # Инициализация обработчиков отчетов
            self.lesson_report_handlers = LessonReportHandlers(db)

            # Проверка формата дат
            self.notification_manager.check_lesson_dates_format()

            # Настройка обработчиков уведомлений
            setup_notification_handlers(self.dp, db, self.notification_manager, self.bot)
            #register_confirmation_handlers(self.dp, self.notification_manager, self.bot)
            
            # Регистрация обработчиков отчетов
            self.dp.include_router(self.lesson_report_handlers.router)

            # Регистрация роутеров
            self.dp.include_router(start_router)
            self.dp.include_router(registration_router)
            self.dp.include_router(edit_students_router)
            self.dp.include_router(about_router)
            self.dp.include_router(students_router)
            self.dp.include_router(invitations_router)
            self.dp.include_router(add_students_router)
            self.dp.include_router(parent_router)
            self.dp.include_router(student_router)
            
            # Роутер расписания
            schedule_router = setup_schedule_handlers()
            self.dp.include_router(schedule_router)
            self.dp.include_router(groups_router)
            self.dp.include_router(main_menu) # на время разработки кнопок

            # Роутер ЮКасса
            self.dp.update.middleware(SubscriptionMiddleware()) # Middleware для проверки подписки
            self.dp.include_router(payment_router)  # Роутер оплаты

            #Роутер ролей
            self.dp.include_router(admin_router)


            self.is_running = True
            logger.info("Бот успешно инициализирован")
            return True

        except Exception as e:
            logger.error(f"Ошибка при запуске бота: {e}")
            logger.error(traceback.format_exc())
            return False

    async def shutdown(self):
        """Корректное завершение работы приложения"""
        if not self.is_running:
            return
            
        logger.info("Завершение работы бота...")
        self.is_running = False

        # Отмена всех фоновых задач
        for task in self.tasks:
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
                except Exception as e:
                    logger.error(f"Ошибка при отмене задачи: {e}")

        # Закрытие соединения с ботом
        if self.bot:
            try:
                await self.bot.session.close()
            except Exception as e:
                logger.error(f"Ошибка при закрытии сессии бота: {e}")

        # Закрытие соединения с базой данных (если требуется)
        if hasattr(db, 'close'):
            try:
                db.close()
            except Exception as e:
                logger.error(f"Ошибка при закрытии БД: {e}")

        logger.info("Бот успешно остановлен")

    async def run(self):
        """Основной цикл работы бота"""
        if not await self.startup():
            return

        # Регистрация обработчиков сигналов
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            try:
                loop.add_signal_handler(
                    sig, 
                    lambda: asyncio.create_task(self.shutdown())
                )
            except NotImplementedError:
                # Сигналы не поддерживаются на этой платформе (например, Windows)
                pass

        try:
            # Запуск фоновых задач
            self.tasks.append(asyncio.create_task(lesson_notification_scheduler(self.bot, self.notification_manager)))
            self.tasks.append(asyncio.create_task(self.lesson_report_handlers.notify_tutor_about_lesson_end(self.bot)))

            logger.info("Бот запущен и готов к работе")
            await self.dp.start_polling(self.bot)
        except asyncio.CancelledError:
            logger.info("Получен сигнал остановки")
        except Exception as e:
            logger.error(f"Ошибка в основном цикле: {e}")
            logger.error(traceback.format_exc())
        finally:
            if self.is_running:
                await self.shutdown()


async def main():
    """Точка входа в приложение"""
    logger.info("Запуск приложения...")
    app = BotApp()
    try:
        await app.run()
    except KeyboardInterrupt:
        logger.info("Приложение остановлено пользователем")
    except Exception as e:
        logger.error(f"Неожиданная ошибка: {e}")
        logger.error(traceback.format_exc())
    finally:
        # Дополнительная гарантия очистки ресурсов
        await app.shutdown()


if __name__ == "__main__":
    # Запуск приложения
    try:
        # Создаем новый цикл событий и запускаем основную корутину
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Приложение остановлено")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
        logger.error(traceback.format_exc())