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

class EditLessonStates(StatesGroup):
    choosing_date = State()           # Выбор даты
    choosing_lesson = State()         # Выбор конкретного занятия
    choosing_action = State()         # Выбор действия для занятия
    choosing_group_action = State()   # Выбор действия для группового занятия
    
    # Состояния для редактирования
    editing_date = State()            # Редактирование даты
    editing_time = State()            # Редактирование времени
    editing_price = State()           # Редактирование цены
    editing_duration = State()        # Редактирование длительности
    
    # Состояния для группового редактирования
    editing_group_date = State()      # Редактирование даты группы
    editing_group_time = State()      # Редактирование времени группы
    editing_group_price = State()     # Редактирование цены группы
    editing_group_duration = State()  # Редактирование длительности группы
    
    # Состояния подтверждения удаления
    confirming_delete = State()       # Подтверждение удаления занятия
    confirming_group_delete = State() # Подтверждение удаления группы занятий