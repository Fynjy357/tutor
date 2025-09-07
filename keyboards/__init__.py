from .save import get_save_keyboard
from .edit import get_edit_keyboard
from .confirmation import get_confirmation_keyboard
from .students_edit import get_edit_student_keyboard
from .main_menu import router as main_menu


__all__ = [
    'get_save_keyboard',
    'get_edit_keyboard',
    'get_confirmation_keyboard',
    'get_edit_student_keyboard',
    'main_menu'
]