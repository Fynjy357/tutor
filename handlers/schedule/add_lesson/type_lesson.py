from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from handlers.schedule.states import AddLessonStates
import logging
from database import db



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
    
    # Получаем ID репетитора
    tutor_id = db.get_tutor_id_by_telegram_id(callback_query.from_user.id)
    groups = db.get_groups_by_tutor(tutor_id)  # Предполагается, что эта функция есть в database.py
    
    if not groups:
        # Если нет групп, предлагаем создать новую
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➕ Создать новую группу", callback_data="create_group_for_lesson")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_lesson_type")]
        ])
        
        await callback_query.message.edit_text(
            "❌ <b>У вас нет групп</b>\n\nСначала создайте группу, чтобы добавить групповое занятие",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        return
    
    # Создаем клавиатуру с группами
    buttons = []
    for group in groups:
        buttons.append([InlineKeyboardButton(
            text=f"👥 {group['name']}",  # название группы
            callback_data=f"select_group_{group['id']}"  # ID группы
        )])
    
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_lesson_type")])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    await callback_query.message.edit_text(
        "👥 <b>Выберите группу для занятия:</b>",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await state.set_state(AddLessonStates.choosing_group)