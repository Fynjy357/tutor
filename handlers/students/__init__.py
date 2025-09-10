from aiogram import Router

router = Router()

from .invitations import router as invitations_router
from .edit_handlers import router as edit_students_router
from .main import router as students_router
from .handlers import router as add_students_router
from .report_editor import router as report_editor_router  # Добавьте эту строку

# Подключаем все роутеры
router.include_router(students_router)
router.include_router(invitations_router)
router.include_router(edit_students_router)
router.include_router(add_students_router)
router.include_router(report_editor_router)  # Добавьте эту строку

__all__ = [
    'students_router', 
    'invitations_router', 
    'edit_students_router',
    'add_students_router',
    'report_editor_router'  # Добавьте эту строку
]