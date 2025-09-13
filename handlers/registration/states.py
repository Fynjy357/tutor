from aiogram.fsm.state import State, StatesGroup

class RegistrationStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_phone = State()
    confirmation = State()
    editing_name = State()
    editing_phone = State()