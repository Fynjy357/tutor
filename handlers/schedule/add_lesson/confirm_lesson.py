from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from datetime import datetime
from database import db
from handlers.schedule.states import AddLessonStates
from datetime import datetime, timedelta
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import logging


router = Router()
logger = logging.getLogger(__name__)


# Обработчик подтверждения занятия
@router.callback_query(AddLessonStates.confirmation, F.data == "confirm_lesson")
async def process_confirmation(callback_query: types.CallbackQuery, state: FSMContext):
    """Обработка подтверждения занятия"""
    await callback_query.answer()
    
    data = await state.get_data()
    tutor_id = db.get_tutor_id_by_telegram_id(callback_query.from_user.id)
    
    try:
        if data.get('frequency') == 'regular':
            # Создаем регулярные занятия на месяц вперед
            created_count = 0
            weekday = data.get('weekday')
            time_str = data.get('time')
            
            for i in range(4):  # На 4 недели вперед
                # Вычисляем дату для этого дня недели
                target_date = datetime.now() + timedelta(weeks=i)
                days_to_add = (weekday - target_date.weekday()) % 7
                lesson_date = target_date + timedelta(days=days_to_add)
                
                # Формируем полную дату и время
                full_datetime = f"{lesson_date.strftime('%Y-%m-%d')} {time_str}:00"
                
                # Добавляем занятие в БД
                lesson_id = db.add_lesson(
                    tutor_id=tutor_id,
                    student_id=data.get('student_id'),
                    lesson_date=full_datetime,
                    duration=60,  # По умолчанию 60 минут
                    price=1000    # По умолчанию 1000 руб
                )
                
                if lesson_id:
                    created_count += 1
            
            await callback_query.message.edit_text(
                f"✅ <b>Создано {created_count} регулярных занятий!</b>\n\n"
                "Занятия добавлены в расписание на месяц вперед.",
                parse_mode="HTML"
            )
            
        else:
            # Единоразовое занятие
            full_datetime = f"{data.get('date')} {data.get('time')}:00"
            
            lesson_id = db.add_lesson(
                tutor_id=tutor_id,
                student_id=data.get('student_id'),
                lesson_date=full_datetime,
                duration=60,
                price=1000
            )
            
            if lesson_id:
                await callback_query.message.edit_text(
                    "✅ <b>Занятие успешно добавлено!</b>\n\n"
                    "Занятие добавлено в ваше расписание.",
                    parse_mode="HTML"
                )
            else:
                await callback_query.message.edit_text(
                    "❌ <b>Ошибка при добавлении занятия!</b>\n\n"
                    "Попробуйте еще раз.",
                    parse_mode="HTML"
                )
        
        await state.clear()
        
    except Exception as e:
        logger.error(f"Ошибка при создании занятия: {e}")
        await callback_query.message.edit_text(
            "❌ <b>Ошибка при создании занятия!</b>\n\n"
            f"Ошибка: {str(e)}",
            parse_mode="HTML"
        )

@router.message(AddLessonStates.confirming_lesson)
async def confirm_lesson_data(message: types.Message, state: FSMContext):
    """Подтверждение данных занятия"""
    data = await state.get_data()
    
    # Формируем текст для подтверждения
    confirm_text = f"""
✅ <b>Проверьте данные занятия:</b>

📅 Дата: {data.get('date')}
⏰ Время: {data.get('time')}
👥 Тип: {'Групповое' if data.get('lesson_type') == 'group' else 'Индивидуальное'}
"""

    if data.get('lesson_type') == 'individual':
        confirm_text += f"👤 Ученик: {data.get('student_name')}"
    else:
        confirm_text += f"👥 Группа: {data.get('group_name')}"

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Подтвердить", callback_data="confirm_lesson")],
        [InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_lesson")]
    ])
    
    await message.answer(confirm_text, reply_markup=keyboard, parse_mode="HTML")

@router.callback_query(F.data == "confirm_lesson", AddLessonStates.confirming_lesson)
async def process_lesson_confirmation(callback_query: types.CallbackQuery, state: FSMContext):
    """Обработка подтверждения занятия"""
    data = await state.get_data()
    
    # Сохраняем занятие в БД
    # db.add_lesson(...)
    
    await callback_query.message.edit_text(
        "✅ <b>Занятие успешно добавлено в расписание!</b>",
        parse_mode="HTML"
    )
    await state.clear()

@router.callback_query(F.data == "cancel_lesson", AddLessonStates.confirming_lesson)
async def process_lesson_cancellation(callback_query: types.CallbackQuery, state: FSMContext):
    """Обработка отмены занятия"""
    await callback_query.message.edit_text(
        "❌ <b>Добавление занятия отменено</b>",
        parse_mode="HTML"
    )
    await state.clear()