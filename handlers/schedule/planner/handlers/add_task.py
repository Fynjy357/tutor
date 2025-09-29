# handlers/schedule/planner/handlers/add_task.py
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram import types
import logging

from handlers.schedule.planner.states import PlannerStates
from ...planner.keyboards_planner import get_planner_keyboard
from handlers.schedule.planner.utils.helpers import (
    get_lesson_info_text, validate_time_format, validate_duration, validate_price
)
from database import db
from handlers.schedule.planner.timer.planner_manager import planner_manager  # Добавляем импорт

router = Router()
logger = logging.getLogger(__name__)

@router.callback_query(F.data == "planner_add_task")
async def planner_add_task_start(callback: CallbackQuery, state: FSMContext):
    """Начинает процесс добавления задачи в планер"""
    tutor_id = db.get_tutor_id_by_telegram_id(callback.from_user.id)
    if not tutor_id:
        await callback.answer("❌ Ошибка: репетитор не найден", show_alert=True)
        return
    
    # Убрана проверка подписки - сразу переходим к выбору типа занятия
    await show_lesson_type_selection(callback, state)

async def show_lesson_type_selection(callback: CallbackQuery, state: FSMContext):
    """Показывает выбор типа занятия"""
    builder = InlineKeyboardBuilder()
    builder.row(
        types.InlineKeyboardButton(
            text="👤 Индивидуальное занятие",
            callback_data="planner_type_individual"
        )
    )
    builder.row(
        types.InlineKeyboardButton(
            text="👥 Групповое занятие",
            callback_data="planner_type_group"
        )
    )
    builder.row(
        types.InlineKeyboardButton(
            text="◀️ Назад",
            callback_data="back_to_planner"
        )
    )
    
    await callback.message.edit_text(
        "📝 <b>Добавление регулярного занятия</b>\n\n"
        "Выберите тип занятия:",
        reply_markup=builder.as_markup()
    )
    await state.set_state(PlannerStates.waiting_for_lesson_type)

@router.callback_query(F.data.startswith("planner_type_"))
async def planner_choose_type(callback: CallbackQuery, state: FSMContext):
    """Обрабатывает выбор типа занятия"""
    lesson_type = "individual" if "individual" in callback.data else "group"
    await state.update_data(lesson_type=lesson_type)
    
    tutor_id = db.get_tutor_id_by_telegram_id(callback.from_user.id)
    await state.update_data(tutor_id=tutor_id)
    
    if lesson_type == "individual":
        await show_student_selection(callback, state, tutor_id)
    else:
        await show_group_selection(callback, state, tutor_id)

async def show_student_selection(callback: CallbackQuery, state: FSMContext, tutor_id: int):
    """Показывает выбор ученика (только активных)"""
    # Получаем только активных учеников
    students = db.get_students_by_tutor(tutor_id)
    active_students = [student for student in students if student.get('status') == 'active']
    
    if not active_students:
        await callback.message.edit_text(
            "❌ <b>Нет активных учеников</b>\n\n"
            "Для создания индивидуального занятия сначала добавьте учеников со статусом 'активный'.",
            reply_markup=get_planner_keyboard()
        )
        await state.clear()
        await callback.answer()
        return
    
    builder = InlineKeyboardBuilder()
    for student in active_students:
        builder.row(
            types.InlineKeyboardButton(
                text=f"👤 {student['full_name']}",
                callback_data=f"planner_student_{student['id']}"
            )
        )
    builder.row(
        types.InlineKeyboardButton(
            text="◀️ Назад",
            callback_data="planner_add_task"
        )
    )
    
    await callback.message.edit_text("👤 <b>Выберите ученика:</b>", reply_markup=builder.as_markup())
    await state.set_state(PlannerStates.waiting_for_student_or_group)

async def show_group_selection(callback: CallbackQuery, state: FSMContext, tutor_id: int):
    """Показывает выбор группы"""
    groups = db.get_groups_by_tutor(tutor_id)
    if not groups:
        await callback.message.edit_text(
            "❌ <b>Нет доступных групп</b>\n\n"
            "Для создания группового занятия сначала создайте группу.",
            reply_markup=get_planner_keyboard()
        )
        await state.clear()
        await callback.answer()
        return
    
    builder = InlineKeyboardBuilder()
    for group in groups:
        builder.row(
            types.InlineKeyboardButton(
                text=f"👥 {group['name']} ({group['student_count']} уч.)",
                callback_data=f"planner_group_{group['id']}"
            )
        )
    builder.row(
        types.InlineKeyboardButton(
            text="◀️ Назад",
            callback_data="planner_add_task"
        )
    )
    
    await callback.message.edit_text("👥 <b>Выберите группу:</b>", reply_markup=builder.as_markup())
    await state.set_state(PlannerStates.waiting_for_student_or_group)

# ИСПРАВЛЕНИЕ: Убираем состояние waiting_for_target, используем waiting_for_student_or_group
@router.callback_query(F.data.startswith("planner_student_"), PlannerStates.waiting_for_student_or_group)
async def planner_choose_student(callback: CallbackQuery, state: FSMContext):
    """Обрабатывает выбор ученика"""
    student_id = int(callback.data.split("_")[2])
    await state.update_data(student_id=student_id, group_id=None)
    await show_weekday_selection(callback, state)

@router.callback_query(F.data.startswith("planner_group_"), PlannerStates.waiting_for_student_or_group)
async def planner_choose_group(callback: CallbackQuery, state: FSMContext):
    """Обрабатывает выбор группы"""
    group_id = int(callback.data.split("_")[2])
    await state.update_data(group_id=group_id, student_id=None)
    await show_weekday_selection(callback, state)

async def show_weekday_selection(callback: CallbackQuery, state: FSMContext):
    """Показывает выбор дня недели"""
    weekdays = [
        ("Понедельник", "monday"), ("Вторник", "tuesday"), ("Среда", "wednesday"),
        ("Четверг", "thursday"), ("Пятница", "friday"), ("Суббота", "saturday"), 
        ("Воскресенье", "sunday")
    ]
    
    builder = InlineKeyboardBuilder()
    for day_name, day_value in weekdays:
        builder.row(
            types.InlineKeyboardButton(
                text=day_name,
                callback_data=f"planner_weekday_{day_value}"
            )
        )
    
    # Исправляем callback_data для кнопки "Назад"
    builder.row(
        types.InlineKeyboardButton(
            text="◀️ Назад",
            callback_data="planner_back_to_target"
        )
    )
    
    await callback.message.edit_text("📅 <b>Выберите день недели:</b>", reply_markup=builder.as_markup())
    await state.set_state(PlannerStates.waiting_for_weekday)

# ДОБАВЛЯЕМ обработчик для возврата к выбору ученика/группы
@router.callback_query(F.data == "planner_back_to_target", PlannerStates.waiting_for_weekday)
async def planner_back_to_target(callback: CallbackQuery, state: FSMContext):
    """Возврат к выбору ученика/группы"""
    data = await state.get_data()
    tutor_id = data.get('tutor_id')
    lesson_type = data.get('lesson_type')
    
    if lesson_type == "individual":
        await show_student_selection(callback, state, tutor_id)
    else:
        await show_group_selection(callback, state, tutor_id)

@router.callback_query(F.data.startswith("planner_weekday_"), PlannerStates.waiting_for_weekday)
async def planner_choose_weekday(callback: CallbackQuery, state: FSMContext):
    """Обрабатывает выбор дня недели"""
    weekday = callback.data.split("_")[2]
    await state.update_data(weekday=weekday)
    await show_time_input(callback, state)

async def show_time_input(callback: CallbackQuery, state: FSMContext):
    """Показывает ввод времени"""
    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(text="◀️ Назад", callback_data="planner_back_to_weekday"))
    
    await callback.message.edit_text(
        "⏰ <b>Введите время начала занятия:</b>\n\n"
        "Формат: <code>ЧЧ:MM</code>\n"
        "Пример: <code>14:30</code>",
        reply_markup=builder.as_markup()
    )
    await state.set_state(PlannerStates.waiting_for_time)

@router.callback_query(F.data == "planner_back_to_weekday", PlannerStates.waiting_for_time)
async def planner_back_to_weekday(callback: CallbackQuery, state: FSMContext):
    """Возврат к выбору дня недели"""
    await show_weekday_selection(callback, state)

@router.message(PlannerStates.waiting_for_time)
async def planner_enter_time(message: Message, state: FSMContext):
    """Обрабатывает ввод времени"""
    time_text = message.text.strip()
    
    if not validate_time_format(time_text):
        builder = InlineKeyboardBuilder()
        builder.add(types.InlineKeyboardButton(text="◀️ Назад", callback_data="planner_back_to_weekday"))
        
        await message.answer(
            "❌ <b>Неверный формат времени!</b>\n\n"
            "Пожалуйста, введите время в формате <code>ЧЧ:MM</code>\n"
            "Пример: <code>14:30</code>",
            reply_markup=builder.as_markup()
        )
        return
    
    await state.update_data(time=time_text)
    await show_duration_input(message, state)

async def show_duration_input(message: Message, state: FSMContext):
    """Показывает ввод длительности"""
    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(text="◀️ Назад", callback_data="planner_back_to_time"))
    
    await message.answer(
        "⏱️ <b>Введите длительность занятия (в минутах):</b>\n\n"
        "Пример: <code>60</code> (1 час)",
        reply_markup=builder.as_markup()
    )
    await state.set_state(PlannerStates.waiting_for_duration)

@router.callback_query(F.data == "planner_back_to_time", PlannerStates.waiting_for_duration)
async def planner_back_to_time(callback: CallbackQuery, state: FSMContext):
    """Возврат к вводу времени"""
    await show_time_input(callback, state)

@router.message(PlannerStates.waiting_for_duration)
async def planner_enter_duration(message: Message, state: FSMContext):
    """Обрабатывает ввод длительности"""
    duration_text = message.text.strip()
    
    if not validate_duration(duration_text):
        builder = InlineKeyboardBuilder()
        builder.add(types.InlineKeyboardButton(text="◀️ Назад", callback_data="planner_back_to_time"))
        
        await message.answer(
            "❌ <b>Неверный формат длительности!</b>\n\n"
            "Пожалуйста, введите целое число (минуты)\n"
            "Пример: <code>60</code>",
            reply_markup=builder.as_markup()
        )
        return
    
    duration = int(duration_text)
    await state.update_data(duration=duration)
    await show_price_input(message, state)

async def show_price_input(message: Message, state: FSMContext):
    """Показывает ввод стоимости"""
    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(text="◀️ Назад", callback_data="planner_back_to_duration"))
    
    await message.answer(
        "💰 <b>Введите стоимость занятия для одного ученика (руб.):</b>\n\n"
        "Пример: <code>1000</code>"
        "<i>Укажите только цифры, без пробелов и символов.</i>",
        reply_markup=builder.as_markup()
    )
    await state.set_state(PlannerStates.waiting_for_price)

@router.callback_query(F.data == "planner_back_to_duration", PlannerStates.waiting_for_price)
async def planner_back_to_duration(callback: CallbackQuery, state: FSMContext):
    """Возврат к вводу длительности"""
    await callback.message.edit_text(
        "⏱️ <b>Введите длительность занятия (в минутах):</b>\n\n"
        "Пример: <code>60</code> (1 час)",
        reply_markup=InlineKeyboardBuilder().add(
            types.InlineKeyboardButton(text="◀️ Назад", callback_data="planner_back_to_time")
        ).as_markup()
    )
    await state.set_state(PlannerStates.waiting_for_duration)
    await callback.answer()

@router.message(PlannerStates.waiting_for_price)
async def planner_enter_price(message: Message, state: FSMContext):
    """Обрабатывает ввод стоимости и сохраняет задачу"""
    price_text = message.text.strip()
    
    if not validate_price(price_text):
        builder = InlineKeyboardBuilder()
        builder.add(types.InlineKeyboardButton(text="◀️ Назад", callback_data="planner_back_to_duration"))
        
        await message.answer(
            "❌ <b>Неверный формат стоимости!</b>\n\n"
            "Пожалуйста, введите число\n"
            "Пример: <code>1000</code>",
            reply_markup=builder.as_markup()
        )
        return
    
    price = float(price_text)
    data = await state.get_data()
    
    # Сохраняем задачу в планер
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
            INSERT INTO planner_actions 
            (tutor_id, lesson_type, student_id, group_id, weekday, time, duration, price)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                data['tutor_id'],
                data['lesson_type'],
                data.get('student_id'),
                data.get('group_id'),
                data['weekday'],
                data['time'],
                data['duration'],
                price
            ))
            conn.commit()
            
            # Получаем информацию о занятии для подтверждения
            lesson_info = await get_lesson_info_text(data, price)
            
            # Запускаем планер автоматически
            await planner_manager.start_planner()
            
            # Сразу выполняем проверку для создания занятий
            await planner_manager.force_check()
            
            # НОВОЕ СООБЩЕНИЕ С ОБНОВЛЕННЫМ ФОРМАТОМ
            await message.answer(
                f"✅ <b>Регулярное занятие настроено!</b>\n\n"
                f"{lesson_info}\n\n"
                f"🔄 <b>Расписание активно</b> — занятия будут добавляться автоматически.",
                reply_markup=get_planner_keyboard()
            )
            
    except Exception as e:
        logger.error(f"Ошибка при сохранении задачи в планер: {e}")
        await message.answer(
            "❌ <b>Ошибка при сохранении задачи!</b>\n\n"
            "Попробуйте еще раз позже.",
            reply_markup=get_planner_keyboard()
        )
    
    await state.clear()
