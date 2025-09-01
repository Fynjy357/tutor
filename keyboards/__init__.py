# keyboards/__init__.py
from .registration import get_registration_keyboard, get_cancel_keyboard, get_phone_keyboard
from .save import get_save_keyboard
from .edit import get_edit_keyboard
from .confirmation import get_confirmation_keyboard
from .students import get_students_menu_keyboard

__all__ = [
    'get_registration_keyboard',
    'get_cancel_keyboard',
    'get_phone_keyboard',
    'get_save_keyboard',
    'get_edit_keyboard',
    'get_confirmation_keyboard'
    'get_students_menu_keyboard'
]