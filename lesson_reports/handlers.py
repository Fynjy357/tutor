import logging
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from parent_report.handlers import ParentReportHandlers

from .states import IndividualLessonStates, GroupLessonStates
from .individual import IndividualLessonHandler
from .group import GroupLessonHandler
from .scheduler import LessonScheduler
from .utils import ReportUtils

logger = logging.getLogger(__name__)

class LessonReportHandlers:
    def __init__(self, db):
        self.db = db
        self.router = Router()
        self.parent_reports = ParentReportHandlers(db)
        
        # Инициализация компонентов
        self.individual_handler = IndividualLessonHandler(db, self.parent_reports)
        self.group_handler = GroupLessonHandler(db, self.parent_reports)
        self.scheduler = LessonScheduler(db)
        self.utils = ReportUtils()
        
        self.setup_handlers()

    def setup_handlers(self):
        """Настройка обработчиков"""
        # Индивидуальные занятия
        self.router.callback_query(F.data.startswith("individual_report:"))(
            self.individual_handler.start_individual_report
        )
        self.router.callback_query(F.data.in_(["held_yes", "held_no"]))(
            self.individual_handler.handle_lesson_held
        )
        self.router.callback_query(F.data.in_(["paid_yes", "paid_no"]))(
            self.individual_handler.handle_lesson_paid
        )
        self.router.callback_query(F.data.in_(["homework_yes", "homework_no"]))(
            self.individual_handler.handle_homework_done
        )
        # ИСПРАВЛЕНО: меняем PERFORMANCE на STUDENT_PERFORMANCE
        self.router.message(IndividualLessonStates.STUDENT_PERFORMANCE)(
            self.individual_handler.handle_performance
        )
        # ДОБАВЛЕНО: новый обработчик для заметки родителям
        self.router.message(IndividualLessonStates.PARENT_PERFORMANCE)(
            self.individual_handler.handle_parent_performance
        )

        # Групповые занятия
        self.router.callback_query(F.data.startswith("group_report:"))(
            self.group_handler.start_group_report
        )
        self.router.callback_query(F.data.in_(["group_held_yes", "group_held_no"]))(
            self.group_handler.handle_lesson_held
        )
        self.router.callback_query(F.data.startswith("attend_"))(
            self.group_handler.handle_student_attendance
        )
        self.router.callback_query(F.data.startswith("paid_"))(
            self.group_handler.handle_student_paid
        )
        self.router.callback_query(F.data.startswith("homework_"))(
            self.group_handler.handle_student_homework
        )
        self.router.message(GroupLessonStates.STUDENT_PERFORMANCE)(
            self.group_handler.handle_student_performance
        )
        # ДОБАВЛЕНО: новый обработчик для заметки родителям (групповые занятия)
        self.router.message(GroupLessonStates.PARENT_PERFORMANCE)(
            self.group_handler.handle_parent_performance
        )

        # Команда отмены
        self.router.message(Command("cancel"))(
            self.utils.cancel_report
        )

    async def notify_tutor_about_lesson_end(self, bot):
        """Прокси-метод для планировщика"""
        return await self.scheduler.notify_tutor_about_lesson_end(bot)

    def get_handlers(self):
        """Возвращает обработчики для отчетов"""
        return [self.router]
