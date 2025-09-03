# handlers/schedule/handlers_add.py
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import logging
from datetime import datetime, timedelta

from handlers.schedule.add_lesson import utils
from handlers.schedule.add_lesson import confirm_lesson
from handlers.schedule.add_lesson import student_choice
from handlers.schedule.add_lesson import frequency_of_lesson
from handlers.schedule.add_lesson.type_lesson import add_lesson_start
from handlers.schedule.states import AddLessonStates
from handlers.schedule.keyboards_schedule import get_schedule_keyboard
from .type_lesson import router as type_lesson
from database import db

router = Router()
router.include_router(type_lesson)
router.include_router(frequency_of_lesson)
router.include_router(student_choice)
router.include_router(confirm_lesson)
router.include_router(utils)
logger = logging.getLogger(__name__)