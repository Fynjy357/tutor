from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage
import asyncio
import logging
import signal
import traceback

from config import BOT_TOKEN
from handlers.start import start_router
from handlers.start import about_router
from handlers.registration import registration_router
from handlers.groups.handlers import router as groups_router
from handlers.schedule import setup_schedule_handlers
from notify import NotificationManager, lesson_notification_scheduler, setup_notification_handlers
from lesson_reports.handlers import LessonReportHandlers
from keyboards import main_menu # на время разработки кнопок
from database import db
from payment.middleware import SubscriptionMiddleware
from payment.handlers import router as payment_router
from commands.admin.admin import router as admin_router
from handlers.start.handlers_parent import parent_router
from handlers.start.handlers_student_by_student import student_router
from handlers.students import router as students_module_router
from notify.notify_tutors.reminder_scheduler import ReminderScheduler
from handlers.freedback.feedback_handlers import router as feedback
from commands.ref.take_ref import router as take_ref
from commands.ref.take_ref_pay import router as take_ref_pay
from commands.admin_help import router as admin_help
from commands.last_users.last_users import router as last_users
from commands.payments.admin_payments import router as admin_payments
from commands.logs.logs import router as logs
from commands.backup.backup import router as backup
from commands.system_info.system_info import router as system_help
from important_doc.handlers import consent_router, ConsentMiddleware
from commands.message.message import message_router
from commands.message import broadcast_router
from payment.notifications.trial_notification_task import start_trial_notification_task
from handlers.schedule.planner.timer.planner_manager import planner_manager
from handlers.schedule.planner.timer.planner_commands import router as planner_commands_router
from report_pdf.handlers import router as report_router
from handlers.debt import payment_debts_router
from handlers.homework import homework_debts_router
from commands.time_commands.time_commands import time_router
from mailing.handlers import mailing_router
from mailing.sender import mailing_scheduler

# Настройка логирования
from logging.handlers import RotatingFileHandler
import os

# Создаем папку для логов если её нет
log_dir = 'logs'
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

# Настройка логирования
def setup_logging():
    # Основной логгер
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    # Форматтер
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Файловый обработчик с ротацией
    file_handler = RotatingFileHandler(
        filename=os.path.join(log_dir, 'bot.log'),
        maxBytes=10*1024*1024,  # 10 MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.INFO)
    
    # Консольный обработчик
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.INFO)
    
    # Очищаем существующие обработчики и добавляем новые
    logger.handlers.clear()
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    # Устанавливаем уровень для библиотек
    logging.getLogger('aiogram').setLevel(logging.WARNING)
    logging.getLogger('asyncio').setLevel(logging.WARNING)
    
    return logger

# Инициализируем логирование
setup_logging()
logger = logging.getLogger(__name__)

class BotApp:
    def __init__(self):
        self.bot = None
        self.dp = None
        self.notification_manager = None
        self.lesson_report_handlers = None
        self.reminder_scheduler = None
        self.mailing_handler = None # Рассылка файлов
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
            
            # Инициализация планировщика напоминаний  # ← ДОБАВЛЕНО
            self.reminder_scheduler = ReminderScheduler(self.bot)  # ← ДОБАВЛЕНО

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
            # self.dp.include_router(edit_students_router)
            self.dp.include_router(about_router)
            # self.dp.include_router(students_router)
            # self.dp.include_router(invitations_router)
            # self.dp.include_router(add_students_router)
            self.dp.include_router(parent_router)
            self.dp.include_router(student_router)
            # self.dp.include_router(report_editor_router)
            self.dp.include_router(students_module_router)
            self.dp.include_router(feedback)
            self.dp.include_router(take_ref)
            self.dp.include_router(take_ref_pay)
            self.dp.include_router(admin_help)
            self.dp.include_router(last_users)
            self.dp.include_router(admin_payments)
            self.dp.include_router(logs)
            self.dp.include_router(backup)
            self.dp.include_router(system_help)
            self.dp.include_router(message_router)
            self.dp.include_router(broadcast_router)
            self.dp.include_router(report_router)
            self.dp.include_router(payment_debts_router)
            self.dp.include_router(homework_debts_router)
            self.dp.include_router(time_router)
            self.dp.include_router(mailing_router)
            
            # роутер планера регулярных занятий
            self.dp.include_router(planner_commands_router)

            
            
            
            # Роутер расписания
            schedule_router = setup_schedule_handlers()
            self.dp.include_router(schedule_router)
            self.dp.include_router(groups_router)
            self.dp.include_router(main_menu) # на время разработки кнопок

            # Роутер ЮКасса
            self.dp.update.middleware(SubscriptionMiddleware()) # Middleware для проверки подписки
            self.dp.include_router(payment_router)  # Роутер оплаты

            # Добавляем middleware для проверки согласий
            self.dp.include_router(consent_router)
            self.dp.message.middleware(ConsentMiddleware())
            self.dp.callback_query.middleware(ConsentMiddleware())

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
        # останавливаем планер регулярных задач
        try:
            await planner_manager.stop_planner()
            logger.info("Планер успешно остановлен")
        except Exception as e:
            logger.error(f"Ошибка при остановке планера: {e}")

        # Остановка планировщика напоминаний  # ← ДОБАВЛЕНО
        if self.reminder_scheduler:  # ← ДОБАВЛЕНО
            try:  # ← ДОБАВЛЕНО
                await self.reminder_scheduler.stop()  # ← ДОБАВЛЕНО
                logger.info("Планировщик напоминаний остановлен")  # ← ДОБАВЛЕНО
            except Exception as e:  # ← ДОБАВЛЕНО
                logger.error(f"Ошибка при остановке планировщика: {e}")  # ← ДОБАВЛЕНО

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
            
            # Запуск планировщика напоминаний 
            if self.reminder_scheduler: 
                self.tasks.append(asyncio.create_task(self.reminder_scheduler.start()))
                logger.info("Планировщик напоминаний запущен") 

            # ЗАПУСК ЗАДАЧИ УВЕДОМЛЕНИЙ О ПРОБНОМ ПЕРИОДЕ ← ДОБАВЬТЕ ЭТО
            self.tasks.append(asyncio.create_task(start_trial_notification_task(self.bot)))
            logger.info("Задача уведомлений о пробном периоде запущена")

            # ЗАПУСК ПЛАНИРОВЩИКА бонусов
            self.tasks.append(asyncio.create_task(mailing_scheduler(self.bot)))
            logger.info("Планировщик рассылки бонусов запущен")

            # запуск планера регулярных занятий
            try:
                await planner_manager.start_planner()
                logger.info("Планер успешно запущен")
            except Exception as e:
                logger.error(f"Ошибка при запуске планера: {e}")

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