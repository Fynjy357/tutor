from .general_handlers import router as general_handlers
from.name_groups_handler import router as name_groups_handler
from.save_handlers import router as save_handlers
from.list_groups import router as list_groups
from.add_students_groups import router as add_students_groups


__all__ = ['general_handlers','name_groups_handler','save_handlers','list_groups','add_students_groups']