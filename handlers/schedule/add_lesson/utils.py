from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime
from database import db
from handlers.schedule.add_lesson.type_lesson import add_lesson_start
from handlers.schedule.keyboards_schedule import get_schedule_keyboard
from handlers.schedule.states import AddLessonStates
from handlers.schedule.schedule_utils import get_upcoming_lessons_text
import logging


router = Router()
logger = logging.getLogger(__name__)

@router.callback_query(F.data == "back_to_lesson_type")
async def back_to_lesson_type(callback_query: types.CallbackQuery, state: FSMContext):
    """Возврат к выбору типа занятия"""
    await add_lesson_start(callback_query, state)

@router.callback_query(F.data == "back_to_frequency")
async def back_to_frequency(callback_query: types.CallbackQuery, state: FSMContext):
    """Возврат к выбору частоты"""
    data = await state.get_data()
    lesson_type = data.get('lesson_type')
    await state.update_data(lesson_type=lesson_type)
    
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

@router.callback_query(F.data == "back_to_weekday")
async def back_to_weekday(callback_query: types.CallbackQuery, state: FSMContext):
    """Возврат к выбору дня недели"""
    data = await state.get_data()
    if data.get('frequency') == 'regular':
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Понедельник", callback_data="weekday_0")],
            [InlineKeyboardButton(text="Вторник", callback_data="weekday_1")],
            [InlineKeyboardButton(text="Среда", callback_data="weekday_2")],
            [InlineKeyboardButton(text="Четверг", callback_data="weekday_3")],
            [InlineKeyboardButton(text="Пятница", callback_data="weekday_4")],
            [InlineKeyboardButton(text="Суббота", callback_data="weekday_5")],
            [InlineKeyboardButton(text="Воскресенье", callback_data="weekday_6")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_frequency")]
        ])
        
        await callback_query.message.edit_text(
            "📅 <b>Выберите день недели для регулярного занятия:</b>",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        await state.set_state(AddLessonStates.choosing_weekday)

@router.callback_query(F.data == "back_to_date_input")
async def back_to_date_input(callback_query: types.CallbackQuery, state: FSMContext):
    """Возврат к вводу даты"""
    await callback_query.message.edit_text(
        "📅 <b>Введите дату занятия в формате ДД.ММ.ГГГГ:</b>\n\n"
        "Например: 15.01.2024",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_frequency")]
        ]),
        parse_mode="HTML"
    )
    await state.set_state(AddLessonStates.entering_date)

@router.callback_query(F.data == "back_to_time_input")
async def back_to_time_input(callback_query: types.CallbackQuery, state: FSMContext):
    """Возврат к вводу времени"""
    data = await state.get_data()
    if data.get('frequency') == 'regular':
        await callback_query.message.edit_text(
            "⏰ <b>Введите время занятия в формате ЧЧ:ММ:</b>\n\n"
            "Например: 14:30",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_weekday")]
            ]),
            parse_mode="HTML"
        )
    else:
        await callback_query.message.edit_text(
            "⏰ <b>Введите время занятия в формате ЧЧ:ММ:</b>\n\n"
            "Например: 14:30",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_date_input")]
            ]),
            parse_mode="HTML"
        )
    await state.set_state(AddLessonStates.entering_time)

@router.callback_query(F.data == "back_to_students")
async def back_to_students(callback_query: types.CallbackQuery, state: FSMContext):
    """Возврат к выбору ученика"""
    data = await state.get_data()
    tutor_id = db.get_tutor_id_by_telegram_id(callback_query.from_user.id)
    
    if data.get('lesson_type') == 'individual':
        students = db.get_students_by_tutor(tutor_id)
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[])
        for student in students:
            keyboard.inline_keyboard.append([
                InlineKeyboardButton(text=f"👤 {student['full_name']}", callback_data=f"add_lesson_student_{student['id']}")
            ])
        keyboard.inline_keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_time_input")])
        
        await callback_query.message.edit_text(
            "👤 <b>Выберите ученика:</b>",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        await state.set_state(AddLessonStates.choosing_students)

@router.callback_query(F.data == "back_to_schedule")
async def back_to_schedule(callback_query: types.CallbackQuery, state: FSMContext):
    """Возврат к расписанию"""
    await state.clear()
    
    # Получаем ID репетитора
    tutor_id = db.get_tutor_id_by_telegram_id(callback_query.from_user.id)
    if not tutor_id:
        await callback_query.message.edit_text("❌ Ошибка: не найден ID репетитора.")
        return
    
    # Получаем актуальное расписание
    schedule_text = await get_upcoming_lessons_text(tutor_id)
    
    await callback_query.message.edit_text(
        schedule_text,
        reply_markup=get_schedule_keyboard(),
        parse_mode="HTML"
    )