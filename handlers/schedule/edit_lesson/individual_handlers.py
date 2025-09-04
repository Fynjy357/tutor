from aiogram import Router
from aiogram import types, F
from aiogram.fsm.context import FSMContext
from database import db
from .keyboards import *
from .utils import *
from handlers.schedule.states import EditLessonStates

router = Router()

async def show_edit_options(callback_query: types.CallbackQuery, state: FSMContext):
    """Показ опций редактирования для выбранного занятия"""
    await callback_query.answer()
    
    lesson_id = int(callback_query.data.split("_")[2])
    lesson = db.get_lesson_by_id(lesson_id)
    
    if not lesson:
        await callback_query.message.answer("❌ Занятие не найдено.")
        await state.clear()
        return
    
    await state.update_data(lesson_id=lesson_id, original_lesson=lesson)
    
    lesson_date = lesson['lesson_date'].split()[0]
    lesson_time = lesson['lesson_date'].split()[1][:5]
    
    # Определяем тип занятия
    if lesson['group_id']:
        student_name = f"👥 {lesson['group_name'] or 'Групповое занятие'}"
        is_group = True
    else:
        student_name = f"👤 {lesson['student_name'] or 'Ученик'}"
        is_group = False
    
    keyboard = get_individual_edit_keyboard(lesson_date, is_group)
    
    await callback_query.message.edit_text(
        f"📋 <b>Редактирование занятия:</b>\n\n"
        f"📅 Дата: {lesson_date}\n"
        f"⏰ Время: {lesson_time}\n"
        f"👤 Ученик/Группа: {student_name}\n"
        f"💰 Стоимость: {lesson['price']} руб.\n"
        f"⏱️ Длительность: {lesson['duration']} мин.\n\n"
        f"{'⚠️ Изменения применятся ко ВСЕМ занятиям группы' if is_group else ''}",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await state.set_state(EditLessonStates.choosing_action)

async def edit_datetime_start(callback_query: types.CallbackQuery, state: FSMContext):
    """Начало изменения даты/времени"""
    await callback_query.answer()
    
    await callback_query.message.edit_text(
        "📅 <b>Введите новую дату в формате ДД.ММ.ГГГГ:</b>\n\n"
        "Например: 15.12.2024",
        reply_markup=get_back_keyboard("back_to_edit_options"),
        parse_mode="HTML"
    )
    await state.set_state(EditLessonStates.editing_date)

async def process_new_date(message: types.Message, state: FSMContext):
    """Обработка новой даты"""
    is_valid, error_msg = validate_date(message.text)
    if not is_valid:
        await message.answer(error_msg)
        return
    
    await state.update_data(new_date=message.text)
    
    await message.answer(
        "⏰ <b>Теперь введите новое время в формате ЧЧ:ММ:</b>\n\n"
        "Например: 14:30",
        reply_markup=get_back_keyboard("back_to_date_input"),
        parse_mode="HTML"
    )
    await state.set_state(EditLessonStates.editing_time)

async def process_new_time(message: types.Message, state: FSMContext):
    """Обработка нового времени"""
    is_valid, error_msg = validate_time(message.text)
    if not is_valid:
        await message.answer(error_msg)
        return
    
    data = await state.get_data()
    new_date = data.get('new_date')
    lesson_id = data.get('lesson_id')
    lesson = data.get('original_lesson')
    
    db_datetime = format_datetime_for_db(new_date, message.text)
    
    # Обновляем в БД
    success = False
    if lesson['group_id']:
        success = db.update_group_lesson_datetime(lesson['group_id'], db_datetime)
        if success:
            await message.answer("✅ Дата и время ВСЕХ занятий группы успешно изменены!")
    else:
        success = db.update_lesson_datetime(lesson_id, db_datetime)
        if success:
            await message.answer("✅ Дата и время занятия успешно изменены!")
    
    if success:
        updated_lesson = db.get_lesson_by_id(lesson_id)
        await state.update_data(original_lesson=updated_lesson)
        await show_edit_options_after_update(message, state)
    else:
        await message.answer("❌ Ошибка при изменении даты/времени.")

async def edit_price_start(callback_query: types.CallbackQuery, state: FSMContext):
    """Начало изменения стоимости"""
    await callback_query.answer()
    
    await callback_query.message.edit_text(
        "💰 <b>Введите новую стоимость занятия:</b>\n\n"
        "Например: 1500",
        reply_markup=get_back_keyboard("back_to_edit_options"),
        parse_mode="HTML"
    )
    await state.set_state(EditLessonStates.editing_price)

async def process_new_price(message: types.Message, state: FSMContext):
    """Обработка новой стоимости"""
    is_valid, result = validate_price(message.text)
    if not is_valid:
        await message.answer(result)
        return
    
    price = result
    data = await state.get_data()
    lesson_id = data.get('lesson_id')
    lesson = data.get('original_lesson')
    
    success = False
    if lesson['group_id']:
        success = db.update_group_lesson_price(lesson['group_id'], price)
        if success:
            await message.answer(f"✅ Стоимость ВСЕХ занятий группы изменена на {price} руб.!")
    else:
        success = db.update_lesson_price(lesson_id, price)
        if success:
            await message.answer(f"✅ Стоимость изменена на {price} руб.!")
    
    if success:
        updated_lesson = db.get_lesson_by_id(lesson_id)
        await state.update_data(original_lesson=updated_lesson)
        await show_edit_options_after_update(message, state)
    else:
        await message.answer("❌ Ошибка при изменении стоимости.")

async def edit_duration_start(callback_query: types.CallbackQuery, state: FSMContext):
    """Начало изменения длительности"""
    await callback_query.answer()
    
    await callback_query.message.edit_text(
        "⏱️ <b>Введите новую длительность занятия (в минутах):</b>\n\n"
        "Например: 90 (для 1.5 часа)",
        reply_markup=get_back_keyboard("back_to_edit_options"),
        parse_mode="HTML"
    )
    await state.set_state(EditLessonStates.editing_duration)

async def process_new_duration(message: types.Message, state: FSMContext):
    """Обработка новой длительности"""
    is_valid, result = validate_duration(message.text)
    if not is_valid:
        await message.answer(result)
        return
    
    duration = result
    data = await state.get_data()
    lesson_id = data.get('lesson_id')
    lesson = data.get('original_lesson')
    
    success = False
    if lesson['group_id']:
        success = db.update_group_lesson_duration(lesson['group_id'], duration)
        if success:
            await message.answer(f"✅ Длительность ВСЕХ занятий группы изменена на {duration} минут!")
    else:
        success = db.update_lesson_duration(lesson_id, duration)
        if success:
            await message.answer(f"✅ Длительность изменена на {duration} минут!")
    
    if success:
        updated_lesson = db.get_lesson_by_id(lesson_id)
        await state.update_data(original_lesson=updated_lesson)
        await show_edit_options_after_update(message, state)
    else:
        await message.answer("❌ Ошибка при изменении длительности.")

async def delete_lesson_confirm(callback_query: types.CallbackQuery, state: FSMContext):
    """Подтверждение удаления занятия"""
    await callback_query.answer()
    
    data = await state.get_data()
    lesson = data.get('original_lesson')
    
    keyboard = get_confirmation_keyboard("confirm_delete", "back_to_edit_options")
    
    lesson_date = lesson['lesson_date'].split()[0]
    lesson_time = lesson['lesson_date'].split()[1][:5]
    student_name = lesson['student_name'] if lesson['student_name'] else "Групповое занятие"
    
    await callback_query.message.edit_text(
        f"⚠️ <b>Вы уверены, что хотите удалить это занятие?</b>\n\n"
        f"📅 Дата: {lesson_date}\n"
        f"⏰ Время: {lesson_time}\n"
        f"👤 Ученик: {student_name}\n\n"
        f"Это действие нельзя отменить!",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await state.set_state(EditLessonStates.confirming_delete)

async def confirm_delete_lesson(callback_query: types.CallbackQuery, state: FSMContext):
    """Подтвержденное удаление занятия"""
    await callback_query.answer()
    
    data = await state.get_data()
    lesson_id = data.get('lesson_id')
    
    if db.delete_lesson(lesson_id):
        await callback_query.message.edit_text(
            "✅ Занятие успешно удалено!",
            parse_mode="HTML"
        )
    else:
        await callback_query.message.edit_text(
            "❌ Ошибка при удалении занятия!",
            parse_mode="HTML"
        )
    
    await state.clear()

async def back_to_edit_options(callback_query: types.CallbackQuery, state: FSMContext):
    """Возврат к опциям редактирования"""
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
                f"{'⚠️ Изменения применятся ко ВСЕМ занятиям группы' if lesson['group_id'] else ''}",
                reply_markup=keyboard,
                parse_mode="HTML"
            )
            await state.set_state(EditLessonStates.choosing_action)

async def show_edit_options_after_update(message: types.Message, state: FSMContext):
    """Показать опции редактирования после обновления"""
    data = await state.get_data()
    lesson = data.get('original_lesson')
    
    lesson_date = lesson['lesson_date'].split()[0]
    lesson_time = lesson['lesson_date'].split()[1][:5]
    student_name = lesson['student_name'] if lesson['student_name'] else "Групповое занятие"
    
    keyboard = get_individual_edit_keyboard(lesson_date, lesson['group_id'])
    
    await message.answer(
        f"📋 <b>Редактирование занятия:</b>\n\n"
        f"📅 Дата: {lesson_date}\n"
        f"⏰ Время: {lesson_time}\n"
        f"👤 Ученик: {student_name}\n"
        f"💰 Стоимость: {lesson['price']} руб.\n"
        f"⏱️ Длительность: {lesson['duration']} мин.",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await state.set_state(EditLessonStates.choosing_action)

__all__ = ['router']