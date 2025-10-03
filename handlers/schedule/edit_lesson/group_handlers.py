from aiogram import Router
from aiogram import types, F
from aiogram.fsm.context import FSMContext
from database import db

from .keyboards import *
from .utils import *
from handlers.schedule.states import EditLessonStates

router = Router()

async def show_group_edit_options(callback_query: types.CallbackQuery, state: FSMContext):
    """Показ опций редактирования для группового занятия"""
    await callback_query.answer()
    
    parts = callback_query.data.split('_')
    group_id = int(parts[2])
    selected_date = parts[3]
    selected_time = parts[4]
    
    group = db.get_group_by_id(group_id)
    if not group:
        await callback_query.message.answer("❌ Группа не найдена.")
        await state.clear()
        return
    
    # Получаем все занятия этой группы на эту дату и время
    lessons = db.get_lessons_by_date(group['tutor_id'], selected_date)
    group_lessons = [lesson for lesson in lessons if lesson['group_id'] == group_id and 
                     lesson['lesson_date'].split()[1][:5] == selected_time]
    
    if not group_lessons:
        await callback_query.message.answer("❌ Занятия группы не найдены.")
        await state.clear()
        return
    
    # Берем первое занятие как представитель группы
    representative_lesson = group_lessons[0]
    
    await state.update_data(
        group_id=group_id,
        group_lessons=group_lessons,
        selected_date=selected_date,
        selected_time=selected_time,
        representative_lesson=representative_lesson
    )
    
    keyboard = get_group_edit_keyboard(selected_date)
    
    await callback_query.message.edit_text(
        f"📋 <b>Редактирование группового занятия:</b>\n\n"
        f"👥 Группа: {group['name']}\n"
        f"📅 Дата: {selected_date}\n"
        f"⏰ Время: {selected_time}\n"
        f"👥 Количество учеников: {len(group_lessons)}\n"
        f"💰 Стоимость: {representative_lesson['price']} руб.\n"
        f"⏱️ Длительность: {representative_lesson['duration']} мин.\n\n",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await state.set_state(EditLessonStates.choosing_group_action)

@router.callback_query(F.data.startswith("edit_date_"))
async def handle_group_back_button(callback_query: types.CallbackQuery, state: FSMContext):
    """Обработчик кнопки Назад в групповом редактировании"""
    try:
        await callback_query.answer()
        selected_date = callback_query.data.split("_")[2]
        
        # Импортируем функцию из того же пакета
        from .utils import show_lessons_for_editing
        await show_lessons_for_editing(callback_query, state, selected_date)
    except Exception as e:
        print(f"Ошибка в handle_group_back_button: {e}")
        await callback_query.answer("⚠️ Произошла ошибка при загрузке занятий", show_alert=True)

async def edit_group_datetime_start(callback_query: types.CallbackQuery, state: FSMContext):
    """Начало изменения даты/времени для группы"""
    await callback_query.answer()
    
    await callback_query.message.edit_text(
        "📅 <b>Введите новую дату в формате ДД.ММ.ГГГГ:</b>\n\n"
        "Например: 15.12.2024",
        reply_markup=get_back_keyboard("back_to_group_options"),
        parse_mode="HTML"
    )
    await state.set_state(EditLessonStates.editing_group_date)

async def process_new_group_date(message: types.Message, state: FSMContext):
    """Обработка новой даты для группы"""
    is_valid, error_msg = validate_date(message.text)
    if not is_valid:
        await message.answer(error_msg)
        return
    
    await state.update_data(new_date=message.text)
    
    await message.answer(
        "⏰ <b>Теперь введите новое время в формате ЧЧ:ММ:</b>\n\n"
        "Например: 14:30",
        reply_markup=get_back_keyboard("back_to_group_date_input"),
        parse_mode="HTML"
    )
    await state.set_state(EditLessonStates.editing_group_time)

async def process_new_group_time(message: types.Message, state: FSMContext):
    """Обработка нового времени для группы"""
    is_valid, error_msg = validate_time(message.text)
    if not is_valid:
        await message.answer(error_msg)
        return
    
    data = await state.get_data()
    new_date = data.get('new_date')
    group_id = data.get('group_id')
    
    db_datetime = format_datetime_for_db(new_date, message.text)
    
    # Обновляем в БД
    success = db.update_group_lesson_datetime(group_id, db_datetime)
    
    if success:
        await message.answer("✅ Дата и время ВСЕХ занятий группы успешно изменены!")
        await show_group_edit_options_after_update(message, state)
    else:
        await message.answer("❌ Ошибка при изменении даты/времени.")

async def edit_group_price_start(callback_query: types.CallbackQuery, state: FSMContext):
    """Начало изменения стоимости для группы"""
    await callback_query.answer()
    
    await callback_query.message.edit_text(
        "💰 <b>Введите новую стоимость занятия для группы:</b>\n\n"
        "Например: 1500",
        reply_markup=get_back_keyboard("back_to_group_options"),
        parse_mode="HTML"
    )
    await state.set_state(EditLessonStates.editing_group_price)

async def process_new_group_price(message: types.Message, state: FSMContext):
    """Обработка новой стоимости для группы"""
    is_valid, result = validate_price(message.text)
    if not is_valid:
        await message.answer(result)
        return
    
    price = result
    data = await state.get_data()
    group_id = data.get('group_id')
    
    success = db.update_group_lesson_price(group_id, price)
    
    if success:
        await message.answer(f"✅ Стоимость ВСЕХ занятий группы изменена на {price} руб.!")
        await show_group_edit_options_after_update(message, state)
    else:
        await message.answer("❌ Ошибка при изменении стоимости.")

async def edit_group_duration_start(callback_query: types.CallbackQuery, state: FSMContext):
    """Начало изменения длительности для группы"""
    await callback_query.answer()
    
    await callback_query.message.edit_text(
        "⏱️ <b>Введите новую длительность занятия для группы (в минутах):</b>\n\n"
        "Например: 90 (для 1.5 часа)",
        reply_markup=get_back_keyboard("back_to_group_options"),
        parse_mode="HTML"
    )
    await state.set_state(EditLessonStates.editing_group_duration)

async def process_new_group_duration(message: types.Message, state: FSMContext):
    """Обработка новой длительности для группы"""
    is_valid, result = validate_duration(message.text)
    if not is_valid:
        await message.answer(result)
        return
    
    duration = result
    data = await state.get_data()
    group_id = data.get('group_id')
    
    success = db.update_group_lesson_duration(group_id, duration)
    
    if success:
        await message.answer(f"✅ Длительность ВСЕХ занятий группы изменена на {duration} минут!")
        await show_group_edit_options_after_update(message, state)
    else:
        await message.answer("❌ Ошибка при изменении длительности.")

async def delete_group_lessons_confirm(callback_query: types.CallbackQuery, state: FSMContext):
    """Подтверждение удаления всех занятий группы"""
    await callback_query.answer()
    
    data = await state.get_data()
    group_lessons = data.get('group_lessons', [])
    group = db.get_group_by_id(data.get('group_id'))
    
    keyboard = get_confirmation_keyboard("confirm_group_delete", "back_to_group_options")
    
    await callback_query.message.edit_text(
        f"⚠️ <b>Вы уверены, что хотите удалить ВСЕ занятия группы?</b>\n\n"
        f"👥 Группа: {group['name'] if group else 'Неизвестная группа'}\n"
        f"📅 Дата: {data.get('selected_date')}\n"
        f"⏰ Время: {data.get('selected_time')}\n"
        f"👥 Количество занятий: {len(group_lessons)}\n\n"
        f"Это действие нельзя отменить!",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await state.set_state(EditLessonStates.confirming_group_delete)

async def confirm_delete_group_lessons(callback_query: types.CallbackQuery, state: FSMContext):
    """Подтвержденное удаление всех занятий группы с переходом к расписанию"""
    await callback_query.answer()
    
    data = await state.get_data()
    group_lessons = data.get('group_lessons', [])
    
    success_count = 0
    for lesson in group_lessons:
        if db.delete_lesson(lesson['id']):
            success_count += 1
    
    # Получаем ID репетитора
    tutor_id = db.get_tutor_id_by_telegram_id(callback_query.from_user.id)
    
    if success_count == len(group_lessons):
        # Показываем уведомление об успешном удалении
        await callback_query.answer(f"✅ Все {success_count} занятий группы успешно удалены!", show_alert=True)
    else:
        # Показываем уведомление о частичном удалении
        await callback_query.answer(f"⚠️ Удалено {success_count} из {len(group_lessons)} занятий группы!", show_alert=True)
    
    # Получаем актуальное расписание
    from handlers.schedule.schedule_utils import get_upcoming_lessons_text
    from handlers.schedule.keyboards_schedule import get_schedule_keyboard
    
    schedule_text = await get_upcoming_lessons_text(tutor_id)
    
    # Переходим к расписанию
    await callback_query.message.edit_text(
        schedule_text,
        reply_markup=get_schedule_keyboard(),
        parse_mode="HTML"
    )
    
    await state.clear()

async def back_to_group_options(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.answer()
    data = await state.get_data()
    selected_date = data.get('selected_date')
    if selected_date:
        await show_lessons_for_editing(callback_query, state, selected_date)

async def show_group_edit_options_after_update(message: types.Message, state: FSMContext):
    """Показать опции редактирования группы после обновления"""
    data = await state.get_data()
    group_id = data.get('group_id')
    selected_date = data.get('selected_date')
    
    group = db.get_group_by_id(group_id)
    lessons = db.get_lessons_by_date(group['tutor_id'], selected_date)
    group_lessons = [lesson for lesson in lessons if lesson['group_id'] == group_id]
    
    if group_lessons:
        representative_lesson = group_lessons[0]
        await state.update_data(
            group_lessons=group_lessons,
            representative_lesson=representative_lesson
        )
        
        keyboard = get_group_edit_keyboard(selected_date)
        
        lesson_date = representative_lesson['lesson_date'].split()[0]
        lesson_time = representative_lesson['lesson_date'].split()[1][:5]
        
        await message.answer(
            f"📋 <b>Редактирование группового занятия:</b>\n\n"
            f"👥 Группа: {group['name']}\n"
            f"📅 Дата: {lesson_date}\n"
            f"⏰ Время: {lesson_time}\n"
            f"👥 Количество учеников: {len(group_lessons)}\n"
            f"💰 Стоимость: {representative_lesson['price']} руб.\n"
            f"⏱️ Длительность: {representative_lesson['duration']} мин.\n\n",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        await state.set_state(EditLessonStates.choosing_group_action)

__all__ = ['router']