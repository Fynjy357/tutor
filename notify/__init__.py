# notify/__init__.py
"""Модуль уведомлений о занятиях"""

from .models import NotificationManager
from .scheduler import lesson_notification_scheduler
from .handlers import setup_notification_handlers, register_confirmation_handlers
from .keyboards import get_confirmation_keyboard

__all__ = [
    'NotificationManager',
    'lesson_notification_scheduler',
    'setup_notification_handlers', 
    'register_confirmation_handlers',  # Добавьте эту строку
    'get_confirmation_keyboard'
]