# handlers/schedule/planner/__init__.py
from aiogram import Router

from .handlers.main_menu import router as main_menu_router
from .handlers.add_task import router as add_task_router
from .handlers.view_tasks import router as view_tasks_router
from .handlers.task_menu import router as task_menu_router
from .handlers.edit_fields import router as edit_fields_router
from .handlers.delete_tasks import router as delete_tasks_router

planner_router = Router()
planner_router.include_router(main_menu_router)
planner_router.include_router(add_task_router)
planner_router.include_router(view_tasks_router)
planner_router.include_router(task_menu_router)
planner_router.include_router(edit_fields_router)
planner_router.include_router(delete_tasks_router)

__all__ = ['planner_router']
