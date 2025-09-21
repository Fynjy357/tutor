from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime
from database import db
from handlers.schedule.schedule_utils import get_today_schedule_text
from handlers.schedule.states import AddLessonStates
import logging

from handlers.start.config import WELCOME_BACK_TEXT
from keyboards.main_menu import get_main_menu_keyboard

router = Router()
logger = logging.getLogger(__name__)

# Экран 2: Выбор частоты занятия
@router.callback_query(AddLessonStates.choosing_frequency, F.data.startswith("frequency_"))
async def process_frequency(callback_query: types.CallbackQuery, state: FSMContext):
    """Обработка выбора частоты занятия"""
    logger.info(f"🔥 FREQUENCY SELECTED: User {callback_query.from_user.id}, data: {callback_query.data}")
    logger.info(f"🔥 Current state: {await state.get_state()}")
    await callback_query.answer()
    
    frequency = callback_query.data.split("_")[1]
    await state.update_data(frequency=frequency)
    logger.info(f"🔥 Frequency set to: {frequency}")
    
    # Получаем данные из состояния чтобы узнать тип занятия
    data = await state.get_data()
    lesson_type = data.get('lesson_type')
    
    if lesson_type == 'group':
        # ДЛЯ ГРУППОВЫХ ЗАНЯТИЙ - ПЕРЕХОДИМ К ВЫБОРУ ДАТЫ/ВРЕМЕНИ!
        
        if frequency == "regular":
            # Для регулярных групповых занятий - выбираем день недели
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
            # Для единоразовых групповых занятий - запрашиваем дату
            await callback_query.message.edit_text(
                "📅 <b>Введите дату занятия в формате ДД.ММ.ГГГГ:</b>\n\n"
                "Например: 15.01.2024",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_frequency")]
                ]),
                parse_mode="HTML"
            )
            await state.set_state(AddLessonStates.entering_date)
        
    else:
        # Индивидуальные занятия
        if frequency == "regular":
            # Для регулярных занятий - выбираем день недели
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
            # Для единоразовых занятий - запрашиваем дату
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
    """Обработка ввода даты занятия"""
    try:
        # Преобразуем дату из формата ДД.ММ.ГГГГ в YYYY-MM-DD
        date_obj = datetime.strptime(message.text, '%d.%m.%Y')
        iso_date = date_obj.strftime('%Y-%m-%d')
        
        await state.update_data(date=iso_date)
        logger.info(f"Date processed: {iso_date}")
        
        await message.answer(
            "⏰ <b>Теперь укажите время занятия в формате ЧЧ:ММ</b>\n\n"
            "Например: 14:30",
            parse_mode="HTML"
        )
        await state.set_state(AddLessonStates.entering_time)
        
    except ValueError:
        await message.answer(
            "❌ <b>Неверный формат даты!</b>\n\n"
            "Пожалуйста, введите дату в формате ДД.ММ.ГГГГ\n"
            "Например: 21.12.1994",
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Error processing date: {e}")
        await message.answer("❌ Произошла ошибка при обработке даты")
        await state.clear()

# Обработчик ввода времени (универсальный для всех типов занятий)
@router.message(AddLessonStates.entering_time, F.text.regexp(r'^\d{2}:\d{2}$'))
async def process_time(message: types.Message, state: FSMContext):
    """Обработка ввода времени для любого типа занятия"""
    try:
        data = await state.get_data()
        lesson_type = data.get('lesson_type')
        frequency = data.get('frequency')
        logger.info(f"Processing time. Lesson type: {lesson_type}, Frequency: {frequency}")
        
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
                
                # Получаем данные репетитора для главного меню
                tutor = db.get_tutor_by_telegram_id(message.from_user.id)
                tutor_name = tutor[2] if tutor else "Пользователь"
                tutor_id = tutor[0] if tutor else None
                
                # Получаем расписание на сегодня
                schedule_text = await get_today_schedule_text(tutor_id) if tutor_id else "Расписание недоступно"
                
                # Проверяем активную подписку
                has_active_subscription = db.check_tutor_subscription(tutor_id)
                subscription_icon = "💎 " if has_active_subscription else ""
                
                # Формируем полный текст приветствия
                formatted_text = WELCOME_BACK_TEXT.format(
                    tutor_name=tutor_name,
                    schedule_text=schedule_text
                )
                welcome_text = f"{subscription_icon}{formatted_text}"
                
                await message.answer(
                    welcome_text,
                    reply_markup=get_main_menu_keyboard(),
                    parse_mode="HTML"
                )
                return
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[])
            active_students_count = 0

            for student in students:
                # Более надежная проверка статуса
                status = student.get('status', '').lower()  # Приводим к нижнему регистру для надежности
                if status != 'inactive':
                    keyboard.inline_keyboard.append([
                        InlineKeyboardButton(text=f"👤 {student['full_name']}", callback_data=f"add_lesson_student_{student['id']}")
                    ])
                    active_students_count += 1

            if active_students_count > 0:
                keyboard.inline_keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_time_input")])
            
            await message.answer(
                "👤 <b>Выберите ученика:</b>",
                reply_markup=keyboard,
                parse_mode="HTML"
            )
            await state.set_state(AddLessonStates.choosing_students)
            
        else:
            # Логика для групповых занятий
            group_id = data.get('group_id')
            
            # Формируем текст подтверждения
            if frequency == 'regular':
                weekdays = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
                weekday = data.get('weekday')
                
                confirmation_text = "✅ <b>Подтвердите данные регулярного группового занятия:</b>\n\n"
                confirmation_text += f"👥 Группа: {data.get('group_name')}\n"
                confirmation_text += f"📅 День: {weekdays[weekday]}\n"
                confirmation_text += f"⏰ Время: {message.text}\n"
                confirmation_text += "🔄 Тип: Регулярное\n"
                
            else:
                # Преобразуем дату обратно в читаемый формат
                date_obj = datetime.strptime(data.get('date'), '%Y-%m-%d')
                readable_date = date_obj.strftime('%d.%m.%Y')
                
                confirmation_text = "✅ <b>Подтвердите данные единоразового группового занятия:</b>\n\n"
                confirmation_text += f"👥 Группа: {data.get('group_name')}\n"
                confirmation_text += f"📅 Дата: {readable_date}\n"
                confirmation_text += f"⏰ Время: {message.text}\n"
                confirmation_text += "📋 Тип: Единоразовое\n"
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✅ Подтвердить", callback_data="confirm_lesson")],
                [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_time_input")]
            ])
            
            await message.answer(
                confirmation_text,
                reply_markup=keyboard,
                parse_mode="HTML"
            )
            await state.set_state(AddLessonStates.confirmation)
            
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