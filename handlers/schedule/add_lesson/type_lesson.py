from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from handlers.schedule.states import AddLessonStates
import logging


router = Router()
logger = logging.getLogger(__name__)

# Экран 1: Выбор типа занятия
@router.callback_query(F.data == "add_lesson")
async def add_lesson_start(callback_query: types.CallbackQuery, state: FSMContext):
    """Начало добавления занятия - выбор типа"""
    await callback_query.answer()
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👤 Индивидуальное", callback_data="lesson_type_individual")],
        [InlineKeyboardButton(text="👥 Групповое", callback_data="lesson_type_group")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_schedule")]
    ])
    
    await callback_query.message.edit_text(
        "📝 <b>Какое занятие добавить?</b>",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await state.set_state(AddLessonStates.choosing_lesson_type)

# Обработчик выбора типа занятия
@router.callback_query(AddLessonStates.choosing_lesson_type, F.data.startswith("lesson_type_"))
async def process_lesson_type(callback_query: types.CallbackQuery, state: FSMContext):
    """Обработка выбора типа занятия"""
    await callback_query.answer()

    await state.update_data(lesson_type="individual")
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📅 Единоразовое", callback_data="frequency_single")],
        [InlineKeyboardButton(text="🔄 Регулярное", callback_data="frequency_regular")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_lesson_type")]
    ])
    
    await callback_query.message.edit_text(
        "📅 <b>Регулярное или единоразовое занятие добавить?</b>",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await state.set_state(AddLessonStates.choosing_frequency)

# Обработчик выбора типа занятия - ГРУППОВОЕ
@router.callback_query(F.data == "lesson_type_group", AddLessonStates.choosing_lesson_type)
async def process_group_lesson_type(callback_query: types.CallbackQuery, state: FSMContext):
    """Обработка выбора группового занятия"""
    await callback_query.answer()
    
    await state.update_data(lesson_type="group")
    
    # Для групповых занятий сразу переходим к выбору группы
    from handlers.schedule.add_lesson.group_lesson import choose_group_for_lesson
    await choose_group_for_lesson(callback_query, state)