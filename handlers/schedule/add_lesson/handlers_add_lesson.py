# handlers/schedule/handlers_add.py
from aiogram import Router
import logging


from handlers.schedule.add_lesson import group_lesson, utils
from handlers.schedule.add_lesson import confirm_lesson
from handlers.schedule.add_lesson import student_choice
from handlers.schedule.add_lesson import frequency_of_lesson
from handlers.schedule.add_lesson.type_lesson import add_lesson_start
from handlers.schedule.keyboards_schedule import get_schedule_keyboard
from .type_lesson import router as type_lesson
logger = logging.getLogger(__name__)
router = Router()
# router.include_router(group_lesson)
# router.include_router(type_lesson)
# router.include_router(frequency_of_lesson)
# router.include_router(student_choice)
# router.include_router(confirm_lesson)
# router.include_router(utils)
# logger = logging.getLogger(__name__)

logger.info("🔥 Including routers in order:")
logger.info("🔥 1. type_lesson")
router.include_router(type_lesson)

logger.info("🔥 2. frequency_of_lesson")
router.include_router(frequency_of_lesson)

logger.info("🔥 3. student_choice")
router.include_router(student_choice)

logger.info("🔥 4. confirm_lesson")
router.include_router(confirm_lesson)

logger.info("🔥 5. utils")
router.include_router(utils)



