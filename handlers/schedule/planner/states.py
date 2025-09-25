# handlers/schedule/planner/states.py
from aiogram.fsm.state import State, StatesGroup

class PlannerStates(StatesGroup):
    waiting_for_lesson_type = State()
    waiting_for_student_or_group = State()
    waiting_for_target = State()
    waiting_for_weekday = State()
    waiting_for_time = State()
    waiting_for_duration = State()
    waiting_for_price = State()

class PlannerEditStates(StatesGroup):
    editing_time = State()
    editing_duration = State()
    editing_price = State()

