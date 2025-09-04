from aiogram import Router

def setup_schedule_handlers():
    """Создает и настраивает роутер расписания"""
    router = Router()  # Создаем новый роутер каждый раз!
    
    from .handlers import router as schedule_router
    from handlers.schedule.edit_lesson import router as edit_lesson_router
    
    router.include_router(schedule_router)
    router.include_router(edit_lesson_router)
    
    return router

__all__ = ['setup_schedule_handlers']