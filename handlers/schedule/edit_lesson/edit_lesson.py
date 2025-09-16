from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from datetime import datetime
from database import db
from handlers.schedule.states import EditLessonStates
from .keyboards import *
from .utils import *
from . import individual_handlers, group_handlers
import logging
import asyncio

router = Router()
logger = logging.getLogger(__name__)

# Основные обработчики
@router.callback_query(F.data == "edit_lesson")
async def edit_lesson_start(callback_query: types.CallbackQuery, state: FSMContext):
    """Начало редактирования занятия - выбор даты"""
    await callback_query.answer()
    
    tutor_id = db.get_tutor_id_by_telegram_id(callback_query.from_user.id)
    if not tutor_id:
        await callback_query.message.answer("❌ Ошибка: не найден ID репетитора.")
        return
    
    # Получаем ближайшие занятия (7 дней вперед)
    upcoming_lessons = db.get_upcoming_lessons(tutor_id, days=7)
    
    if not upcoming_lessons:
        await callback_query.message.answer("📭 У вас нет предстоящих занятий для редактирования.")
        return
    
    lessons_by_date = group_lessons_by_date(upcoming_lessons)
    keyboard = get_date_selection_keyboard(lessons_by_date)
    
    await callback_query.message.edit_text(
        "📅 <b>Выберите дату для редактирования занятий:</b>",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await state.set_state(EditLessonStates.choosing_date)

@router.callback_query(EditLessonStates.choosing_date, F.data.startswith("edit_date_"))
async def choose_lesson_to_edit(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.answer()
    selected_date = callback_query.data.split("_")[2]
    await show_lessons_for_editing(callback_query, state, selected_date)

# Индивидуальные занятия
@router.callback_query(EditLessonStates.choosing_lesson, F.data.startswith("select_lesson_"))
async def handle_select_lesson(callback_query: types.CallbackQuery, state: FSMContext):
    await individual_handlers.show_edit_options(callback_query, state)

@router.callback_query(EditLessonStates.choosing_action, F.data == "edit_datetime")
async def handle_edit_datetime(callback_query: types.CallbackQuery, state: FSMContext):
    await individual_handlers.edit_datetime_start(callback_query, state)

@router.message(EditLessonStates.editing_date)
async def handle_process_date(message: types.Message, state: FSMContext):
    await individual_handlers.process_new_date(message, state)

@router.message(EditLessonStates.editing_time)
async def handle_process_time(message: types.Message, state: FSMContext):
    await individual_handlers.process_new_time(message, state)

@router.callback_query(EditLessonStates.choosing_action, F.data == "edit_price")
async def handle_edit_price(callback_query: types.CallbackQuery, state: FSMContext):
    await individual_handlers.edit_price_start(callback_query, state)

@router.message(EditLessonStates.editing_price)
async def handle_process_price(message: types.Message, state: FSMContext):
    await individual_handlers.process_new_price(message, state)

@router.callback_query(EditLessonStates.choosing_action, F.data == "edit_duration")
async def handle_edit_duration(callback_query: types.CallbackQuery, state: FSMContext):
    await individual_handlers.edit_duration_start(callback_query, state)

@router.message(EditLessonStates.editing_duration)
async def handle_process_duration(message: types.Message, state: FSMContext):
    await individual_handlers.process_new_duration(message, state)

@router.callback_query(EditLessonStates.choosing_action, F.data == "delete_lesson")
async def handle_delete_lesson(callback_query: types.CallbackQuery, state: FSMContext):
    await individual_handlers.delete_lesson_confirm(callback_query, state)

@router.callback_query(EditLessonStates.confirming_delete, F.data == "confirm_delete")
async def handle_confirm_delete(callback_query: types.CallbackQuery, state: FSMContext):
    await individual_handlers.confirm_delete_lesson(callback_query, state)

@router.callback_query(EditLessonStates.choosing_action, F.data == "back_to_edit_options")
async def handle_back_to_options(callback_query: types.CallbackQuery, state: FSMContext):
    await individual_handlers.back_to_edit_options(callback_query, state)

# Групповые занятия
@router.callback_query(EditLessonStates.choosing_lesson, F.data.startswith("select_group_"))
async def handle_select_group(callback_query: types.CallbackQuery, state: FSMContext):
    await group_handlers.show_group_edit_options(callback_query, state)

@router.callback_query(EditLessonStates.choosing_group_action, F.data == "edit_group_datetime")
async def handle_edit_group_datetime(callback_query: types.CallbackQuery, state: FSMContext):
    await group_handlers.edit_group_datetime_start(callback_query, state)

@router.message(EditLessonStates.editing_group_date)
async def handle_process_group_date(message: types.Message, state: FSMContext):
    await group_handlers.process_new_group_date(message, state)

@router.message(EditLessonStates.editing_group_time)
async def handle_process_group_time(message: types.Message, state: FSMContext):
    await group_handlers.process_new_group_time(message, state)

@router.callback_query(EditLessonStates.choosing_group_action, F.data == "edit_group_price")
async def handle_edit_group_price(callback_query: types.CallbackQuery, state: FSMContext):
    await group_handlers.edit_group_price_start(callback_query, state)

@router.message(EditLessonStates.editing_group_price)
async def handle_process_group_price(message: types.Message, state: FSMContext):
    await group_handlers.process_new_group_price(message, state)

@router.callback_query(EditLessonStates.choosing_group_action, F.data == "edit_group_duration")
async def handle_edit_group_duration(callback_query: types.CallbackQuery, state: FSMContext):
    await group_handlers.edit_group_duration_start(callback_query, state)

@router.message(EditLessonStates.editing_group_duration)
async def handle_process_group_duration(message: types.Message, state: FSMContext):
    await group_handlers.process_new_group_duration(message, state)

@router.callback_query(EditLessonStates.choosing_group_action, F.data == "delete_group_lessons")
async def handle_delete_group_lessons(callback_query: types.CallbackQuery, state: FSMContext):
    await group_handlers.delete_group_lessons_confirm(callback_query, state)

@router.callback_query(EditLessonStates.confirming_group_delete, F.data == "confirm_group_delete")
async def handle_confirm_group_delete(callback_query: types.CallbackQuery, state: FSMContext):
    await group_handlers.confirm_delete_group_lessons(callback_query, state)

@router.callback_query(EditLessonStates.choosing_group_action, F.data == "back_to_group_options")
async def handle_back_to_group_options(callback_query: types.CallbackQuery, state: FSMContext):
    await group_handlers.back_to_group_options(callback_query, state)

# Обработчики возврата для групповых состояний
@router.callback_query(EditLessonStates.editing_group_date, F.data == "back_to_group_options")
@router.callback_query(EditLessonStates.editing_group_time, F.data == "back_to_group_date_input")
@router.callback_query(EditLessonStates.editing_group_price, F.data == "back_to_group_options")
@router.callback_query(EditLessonStates.editing_group_duration, F.data == "back_to_group_options")
async def handle_back_from_group_input(callback_query: types.CallbackQuery, state: FSMContext):
    """Возврат из состояний ввода для группы"""
    await callback_query.answer()
    
    data = await state.get_data()
    group_id = data.get('group_id')
    selected_date = data.get('selected_date')
    selected_time = data.get('selected_time')
    
    group = db.get_group_by_id(group_id)
    lessons = db.get_lessons_by_date(group['tutor_id'], selected_date)
    group_lessons = [lesson for lesson in lessons if lesson['group_id'] == group_id and 
                     lesson['lesson_date'].split()[1][:5] == selected_time]
    
    if group_lessons:
        representative_lesson = group_lessons[0]
        await state.update_data(representative_lesson=representative_lesson)
        
        keyboard = get_group_edit_keyboard(selected_date)
        
        await callback_query.message.edit_text(
            f"📋 <b>Редактирование группового занятия:</b>\n\n"
            f"👥 Группа: {group['name']}\n"
            f"📅 Дата: {selected_date}\n"
            f"⏰ Время: {selected_time}\n"
            f"👥 Количество учеников: {len(group_lessons)}\n"
            f"💰 Стоимость: {representative_lesson['price']} руб.\n"
            f"⏱️ Длительность: {representative_lesson['duration']} мин.\n\n"
            f"⚠️ Изменения применятся ко ученикам в группе",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        await state.set_state(EditLessonStates.choosing_group_action)

# Обработчики возврата для индивидуальных занятий
@router.callback_query(EditLessonStates.editing_date, F.data == "back_to_edit_options")
@router.callback_query(EditLessonStates.editing_time, F.data == "back_to_date_input")
@router.callback_query(EditLessonStates.editing_price, F.data == "back_to_edit_options")
@router.callback_query(EditLessonStates.editing_duration, F.data == "back_to_edit_options")
async def handle_back_from_individual_input(callback_query: types.CallbackQuery, state: FSMContext):
    """Возврат из состояний ввода для индивидуальных занятий"""
    await callback_query.answer()
    
    data = await state.get_data()
    lesson_id = data.get('lesson_id')
    
    if lesson_id:
        lesson = db.get_lesson_by_id(lesson_id)
        if lesson:
            await state.update_data(original_lesson=lesson)
            
            lesson_date = lesson['lesson_date'].split()[0]
            lesson_time = lesson['lesson_date'].split()[1][:5]
            
            # Определяем тип занятия
            if lesson['group_id']:
                student_name = f"👥 {lesson['group_name'] or 'Групповое занятие'}"
            else:
                student_name = f"👤 {lesson['student_name'] or 'Ученик'}"
            
            keyboard = get_individual_edit_keyboard(lesson_date, lesson['group_id'])
            
            await callback_query.message.edit_text(
                f"📋 <b>Редактирование занятия:</b>\n\n"
                f"📅 Дата: {lesson_date}\n"
                f"⏰ Время: {lesson_time}\n"
                f"👤 Ученик/Группа: {student_name}\n"
                f"💰 Стоимость: {lesson['price']} руб.\n"
                f"⏱️ Длительность: {lesson['duration']} мин.\n\n"
                f"{'⚠️ Изменения применятся ко ученикам в группе' if lesson['group_id'] else ''}",
                reply_markup=keyboard,
                parse_mode="HTML"
            )
            await state.set_state(EditLessonStates.choosing_action)

# Обработчики возврата к выбору даты
@router.callback_query(EditLessonStates.choosing_lesson, F.data == "back_to_date_selection")
async def handle_back_to_date_selection(callback_query: types.CallbackQuery, state: FSMContext):
    """Возврат к выбору даты"""
    await callback_query.answer()
    
    tutor_id = db.get_tutor_id_by_telegram_id(callback_query.from_user.id)
    upcoming_lessons = db.get_upcoming_lessons(tutor_id, days=7)
    
    if not upcoming_lessons:
        await callback_query.message.edit_text("📭 У вас нет предстоящих занятий для редактирования.")
        await state.clear()
        return
    
    lessons_by_date = group_lessons_by_date(upcoming_lessons)
    keyboard = get_date_selection_keyboard(lessons_by_date)
    
    await callback_query.message.edit_text(
        "📅 <b>Выберите дату для редактирования занятий:</b>",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await state.set_state(EditLessonStates.choosing_date)

# Обработчики отмены
@router.callback_query(F.data == "cancel_edit")
async def handle_cancel_edit(callback_query: types.CallbackQuery, state: FSMContext):
    """Отмена редактирования"""
    await callback_query.answer()
    await callback_query.message.edit_text("❌ Редактирование отменено.")
    await state.clear()

# Обработчики любых других сообщений в состояниях редактирования
@router.message(EditLessonStates.editing_date)
@router.message(EditLessonStates.editing_time)
@router.message(EditLessonStates.editing_price)
@router.message(EditLessonStates.editing_duration)
@router.message(EditLessonStates.editing_group_date)
@router.message(EditLessonStates.editing_group_time)
@router.message(EditLessonStates.editing_group_price)
@router.message(EditLessonStates.editing_group_duration)
async def handle_invalid_input(message: types.Message):
    """Обработка невалидного ввода в состояниях редактирования"""
    await message.answer("❌ Пожалуйста, введите корректные данные или используйте кнопки для навигации.")



__all__ = ['router']