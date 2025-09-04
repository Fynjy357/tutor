# handlers/schedule/states.py
from aiogram.fsm.state import State, StatesGroup

class AddLessonStates(StatesGroup):
    choosing_lesson_type = State()          # Индивидуальное/Групповое
    choosing_frequency = State()            # Регулярное/Единоразовое
    choosing_weekday = State()              # День недели (для регулярных)
    entering_date = State()                 # Дата (для единоразовых)
    entering_time = State()                 # Время
    choosing_students = State()             # Выбор учеников
    confirmation = State()                  # Подтверждение
    choosing_group = State()                # Выбор группы
    confirming_lesson = State()