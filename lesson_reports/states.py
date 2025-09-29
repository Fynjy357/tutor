from aiogram.fsm.state import State, StatesGroup

class IndividualLessonStates(StatesGroup):
    LESSON_HELD = State()
    LESSON_PAID = State()
    HOMEWORK_DONE = State()
    STUDENT_PERFORMANCE = State()
    PARENT_PERFORMANCE = State()

class GroupLessonStates(StatesGroup):
    LESSON_HELD = State()
    STUDENT_ATTENDANCE = State()
    STUDENT_PAID = State()
    STUDENT_HOMEWORK = State()
    STUDENT_PERFORMANCE = State()
    PARENT_PERFORMANCE = State()
