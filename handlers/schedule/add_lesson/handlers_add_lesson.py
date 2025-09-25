# handlers/schedule/handlers_add.py
from aiogram import Router
import logging


from handlers.schedule.add_lesson import utils
from handlers.schedule.add_lesson import confirm_lesson
from handlers.schedule.add_lesson import student_choice
from handlers.schedule.add_lesson import frequency_of_lesson
from .type_lesson import router as type_lesson
logger = logging.getLogger(__name__)
router = Router()

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



