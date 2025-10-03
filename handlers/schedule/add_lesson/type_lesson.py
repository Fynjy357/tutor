# type_lesson.py - добавьте логирование
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database import db

from handlers.schedule.states import AddLessonStates
import logging

router = Router()
logger = logging.getLogger(__name__)

# Экран 1: Выбор типа занятия
@router.callback_query(F.data == "add_lesson")
async def add_lesson_start(callback_query: types.CallbackQuery, state: FSMContext):
    """Начало добавления занятия - выбор типа"""
    logger.info(f"🔥 ADD_LESSON START: User {callback_query.from_user.id}, data: {callback_query.data}")
    logger.info(f"🔥 Current state before: {await state.get_state()}")
    
    await callback_query.answer()
    
    # Принудительно устанавливаем состояние
    await state.set_state(AddLessonStates.choosing_lesson_type)
    logger.info(f"🔥 State set to: {await state.get_state()}")
    
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
    logger.info("🔥 ADD_LESSON screen shown successfully")

# Обработчик выбора типа занятия - ИНДИВИДУАЛЬНОЕ
@router.callback_query(F.data == "lesson_type_individual", AddLessonStates.choosing_lesson_type)
async def process_individual_lesson_type(callback_query: types.CallbackQuery, state: FSMContext):
    """Обработка выбора индивидуального занятия"""
    logger.info(f"🔥 INDIVIDUAL LESSON TYPE: User {callback_query.from_user.id}, data: {callback_query.data}")
    logger.info(f"🔥 Current state: {await state.get_state()}")
    
    await callback_query.answer()
    
    await state.update_data(lesson_type="individual")
    logger.info("🔥 Lesson type set to: individual")
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📅 Единоразовое", callback_data="frequency_single")],
        # [InlineKeyboardButton(text="🔄 Регулярное", callback_data="frequency_regular")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_lesson_type")]
    ])
    
    await callback_query.message.edit_text(
        "📅 <b>Какое занятие добавить?</b>",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await state.set_state(AddLessonStates.choosing_frequency)
    logger.info(f"🔥 State changed to: {await state.get_state()}")

# Обработчик выбора типа занятия - ГРУППОВОЕ
@router.callback_query(F.data == "lesson_type_group", AddLessonStates.choosing_lesson_type)
async def process_group_lesson_type(callback_query: types.CallbackQuery, state: FSMContext):
    """Обработка выбора группового занятия"""
    logger.info(f"🔥 GROUP LESSON TYPE: User {callback_query.from_user.id}, data: {callback_query.data}")
    logger.info(f"🔥 Current state: {await state.get_state()}")
    
    await callback_query.answer()
    
    await state.update_data(lesson_type="group")
    logger.info("🔥 Lesson type set to: group")
    
    # Получаем ID репетитора
    tutor_id = db.get_tutor_id_by_telegram_id(callback_query.from_user.id)
    groups = db.get_groups_by_tutor(tutor_id)
    logger.info(f"🔥 Found {len(groups)} groups for tutor {tutor_id}")
    
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
        logger.info("🔥 No groups found, showing create group option")
        return
    
    # Создаем клавиатуру с группами
    buttons = []
    for group in groups:
        buttons.append([InlineKeyboardButton(
            text=f"👥 {group['name']}",
            callback_data=f"select_group_{group['id']}"
        )])
    
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_lesson_type")])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
    await callback_query.message.edit_text(
        "👥 <b>Выберите группу для занятия:</b>",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await state.set_state(AddLessonStates.choosing_group)
    logger.info(f"🔥 State changed to: {await state.get_state()}")
@router.callback_query(F.data.startswith("select_group_"), AddLessonStates.choosing_group)
async def group_selected_for_lesson(callback_query: types.CallbackQuery, state: FSMContext):
    """Группа выбрана для занятия"""
    logger.info(f"🔥 GROUP SELECTED: User {callback_query.from_user.id}, data: {callback_query.data}")
    logger.info(f"🔥 Current state: {await state.get_state()}")
    
    await callback_query.answer()
    
    group_id = int(callback_query.data.split("_")[2])
    logger.info(f"🔥 Selected group ID: {group_id}")
    
    # Получаем информацию о группе
    group = db.get_group_by_id(group_id)
    
    if not group:
        await callback_query.message.answer("❌ Группа не найдена")
        return
    
    # Сохраняем выбранную группу в состоянии
    await state.update_data(
        group_id=group_id,
        group_name=group['name'],
        lesson_type='group'
    )
    logger.info(f"🔥 Group data saved: {group['name']}")
    
    # Переходим к выбору частоты занятия
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📅 Единоразовое", callback_data="frequency_single")],
        # [InlineKeyboardButton(text="🔄 Регулярное", callback_data="frequency_regular")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_group_selection")]
    ])
    
    await callback_query.message.edit_text(
        f"✅ <b>Группа выбрана:</b> {group['name']}\n\n",
        # "📅 <b>Регулярное или единоразовое занятие добавить?</b>",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await state.set_state(AddLessonStates.choosing_frequency)
    logger.info(f"🔥 State changed to: {await state.get_state()}")
@router.callback_query(F.data == "create_group_for_lesson")
async def create_group_from_lesson(callback_query: types.CallbackQuery, state: FSMContext):
    """Создание группы из процесса добавления занятия"""
    logger.info(f"🔥 CREATE GROUP FROM LESSON: User {callback_query.from_user.id}, data: {callback_query.data}")
    
    await callback_query.answer()
    
    # Сохраняем, что мы в процессе добавления занятия
    await state.update_data(creating_group_for_lesson=True)
    logger.info("🔥 Flag set: creating_group_for_lesson = True")
    
    # Переходим к созданию группы
    from handlers.groups.handlers import add_group_start
    await add_group_start(callback_query.message, state)