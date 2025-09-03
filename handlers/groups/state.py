from aiogram.fsm.state import State, StatesGroup

class GroupStates(StatesGroup):
    waiting_for_group_name = State()
    editing_group = State()