# handlers/students/states.py
from aiogram.fsm.state import StatesGroup, State

class AddStudentStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_phone = State()
    waiting_for_parent_phone = State()

class EditStudentStates(StatesGroup):
    waiting_for_edit_choice = State()
    waiting_for_name = State()
    waiting_for_phone = State()
    waiting_for_parent_phone = State()