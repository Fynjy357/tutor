# handlers/schedule/planner/timer/__init__.py
from .planner_commands import router as planner_commands_router

# Экспортируем все роутеры
__all__ = ['planner_commands_router']
