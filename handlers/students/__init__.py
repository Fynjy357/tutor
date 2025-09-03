from .invitations import router as invitations_router
from .edit_handlers import router as edit_students_router
from .main import router as students_router
from .handlers import router as add_students_router

__all__ = [
    'students_router', 
    'invitations_router', 
    'edit_students_router',
    'add_students_router'
    ]