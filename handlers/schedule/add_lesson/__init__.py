# handlers/schedule/add_lesson/__init__.py
from .type_lesson import router as type_lesson
from.frequency_of_lesson import router as frequency_of_lesson
from.student_choice import router as student_choice
from.confirm_lesson import router as confirm_lesson
from.utils import router as utils
from.group_lesson import router as group_lesson

__all__ = ['type_lesson', 'frequency_of_lesson', 'student_choice', 'confirm_lesson', 'utils', 'group_lesson']