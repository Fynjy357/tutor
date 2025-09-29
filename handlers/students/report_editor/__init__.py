# handlers/report_editor/__init__.py
from aiogram import Router

# Импортируем роутеры из отдельных файлов
from .navigation_handlers import router as navigation_router
from .report_handlers import router as reports_router
from .comment_handlers import router as comments_router

router = Router()

# Подключаем все обработчики
router.include_router(navigation_router)
router.include_router(reports_router)
router.include_router(comments_router)
