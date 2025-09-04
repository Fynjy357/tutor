from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime
from database import db
from handlers.schedule.states import AddLessonStates
import logging

router = Router()
logger = logging.getLogger(__name__)

# Экран 2: Выбор частоты занятия
@router.callback_query(AddLessonStates.choosing_frequency, F.data.startswith("frequency_"))
async def process_frequency(callback_query: types.CallbackQuery, state: FSMContext):
    """Обработка выбора частоты занятия"""
    await callback_query.answer()
    
    frequency = callback_query.data.split("_")[1]
    await state.update_data(frequency=frequency)
    
    if frequency == "regular":
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
    else:
        await callback_query.message.edit_text(
            "📅 <b>Введите дату занятия в формате ДД.ММ.ГГГГ:</b>\n\n"
            "Например: 15.01.2024",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_frequency")]
            ]),
            parse_mode="HTML"
        )
        await state.set_state(AddLessonStates.entering_date)

# Обработчик выбора дня недели для регулярных занятий
@router.callback_query(AddLessonStates.choosing_weekday, F.data.startswith("weekday_"))
async def process_weekday(callback_query: types.CallbackQuery, state: FSMContext):
    """Обработка выбора дня недели"""
    await callback_query.answer()
    
    weekday = int(callback_query.data.split("_")[1])
    await state.update_data(weekday=weekday)
    
    await callback_query.message.edit_text(
        "⏰ <b>Введите время занятия в формате ЧЧ:ММ:</b>\n\n"
        "Например: 14:30",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_weekday")]
        ]),
        parse_mode="HTML"
    )
    await state.set_state(AddLessonStates.entering_time)

# Обработчик ввода даты (универсальный для всех типов занятий)
@router.message(AddLessonStates.entering_date, F.text.regexp(r'^\d{2}\.\d{2}\.\d{4}$'))
async def process_date(message: types.Message, state: FSMContext):
    """Обработка ввода даты для любого типа занятия"""
    try:
        data = await state.get_data()
        lesson_type = data.get('lesson_type')
        logger.info(f"Processing date. Lesson type: {lesson_type}")
        
        date_obj = datetime.strptime(message.text, '%d.%m.%Y')
        await state.update_data(date=date_obj.strftime('%Y-%m-%d'))
        
        logger.info(f"Date processed: {date_obj.strftime('%Y-%m-%d')}")
        
        await message.answer(
            "⏰ <b>Введите время занятия в формате ЧЧ:ММ:</b>\n\n"
            "Например: 14:30",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_date_input")]
            ]),
            parse_mode="HTML"
        )
        await state.set_state(AddLessonStates.entering_time)
        
    except ValueError:
        await message.answer(
            "❌ <b>Неверный формат даты!</b>\n\n"
            "Пожалуйста, введите дату в формате ДД.ММ.ГГГГ\n"
            "Например: 15.01.2024",
            parse_mode="HTML"
        )

# Обработчик ввода времени (универсальный для всех типов занятий)
@router.message(AddLessonStates.entering_time, F.text.regexp(r'^\d{2}:\d{2}$'))
async def process_time(message: types.Message, state: FSMContext):
    """Обработка ввода времени для любого типа занятия"""
    try:
        data = await state.get_data()
        lesson_type = data.get('lesson_type')
        logger.info(f"Processing time. Lesson type: {lesson_type}")
        
        # Проверяем формат времени
        datetime.strptime(message.text, '%H:%M')
        await state.update_data(time=message.text)
        
        logger.info(f"Time processed: {message.text}")
        
        # Получаем данные из состояния
        data = await state.get_data()
        
        # Получаем ID репетитора
        tutor_id = db.get_tutor_id_by_telegram_id(message.from_user.id)
        if not tutor_id:
            await message.answer("❌ Ошибка: не найден ID репетитора.")
            await state.clear()
            return
        
        if lesson_type == 'individual':
            # Логика для индивидуальных занятий
            students = db.get_students_by_tutor(tutor_id)
            
            if not students:
                await message.answer(
                    "❌ <b>У вас нет студентов!</b>\n\n"
                    "Сначала добавьте студентов в систему.",
                    parse_mode="HTML"
                )
                await state.clear()
                return
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[])
            for student in students:
                keyboard.inline_keyboard.append([
                    InlineKeyboardButton(text=f"👤 {student['full_name']}", callback_data=f"add_lesson_student_{student['id']}")
                ])
            keyboard.inline_keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_time_input")])
            
            await message.answer(
                "👤 <b>Выберите ученика:</b>",
                reply_markup=keyboard,
                parse_mode="HTML"
            )
            await state.set_state(AddLessonStates.choosing_students)
            
        elif lesson_type == 'group':
            # Логика для групповых занятий
            group_id = data.get('group_id')
            date_str = data.get('date')
            time_str = data.get('time')
            
            # Создаем datetime объект из ISO формата даты
            lesson_datetime = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
            
            # Получаем всех учеников группы
            group_students = db.get_students_by_group(group_id)
            student_ids = [student['id'] for student in group_students]
            
            # Сохраняем занятие для каждого ученика
            success_count = 0
            for student_id in student_ids:
                lesson_id = db.add_lesson(
                    tutor_id=tutor_id,
                    student_id=student_id,
                    lesson_date=lesson_datetime,
                    duration=60,
                    price=500.0,
                    group_id=group_id
                )
                if lesson_id:
                    success_count += 1
            
            # Получаем информацию о группе
            group = db.get_group_by_id(group_id)
            
            if success_count > 0:
                display_date = lesson_datetime.strftime("%d.%m.%Y")
                
                await message.answer(
                    f"✅ <b>Групповое занятие добавлено!</b>\n\n"
                    f"👥 Группа: {group['name']}\n"
                    f"📅 Дата: {display_date}\n"
                    f"⏰ Время: {time_str}\n"
                    f"👨‍🎓 Учеников: {success_count}/{len(student_ids)}",
                    parse_mode="HTML"
                )
            else:
                await message.answer("❌ Ошибка при сохранении групповых занятий")
            
            await state.clear()
            
    except ValueError:
        await message.answer(
            "❌ <b>Неверный формат времени!</b>\n\n"
            "Пожалуйста, введите время в формате ЧЧ:ММ\n"
            "Например: 14:30",
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Error processing time: {e}")
        await message.answer("❌ Произошла ошибка при обработке времени")
        await state.clear()