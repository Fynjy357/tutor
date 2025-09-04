# handlers/schedule/edit_lesson/__init__.py
from aiogram import Router

router = Router()

# Прямые импорты (убрать setup функцию)
from .edit_lesson import router as edit_router
from .individual_handlers import router as individual_router  
from .group_handlers import router as group_router

router.include_router(edit_router)
router.include_router(individual_router)
router.include_router(group_router)



__all__ = ['router']