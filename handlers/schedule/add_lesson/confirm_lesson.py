from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from datetime import datetime, timedelta
from database import db
from handlers.schedule.states import AddLessonStates
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
    lesson_type = data.get('lesson_type')
    frequency = data.get('frequency')
    
    logger.info(f"Confirming lesson. Type: {lesson_type}, Frequency: {frequency}")
    
    try:
        if frequency == 'regular':
            # Регулярные занятия (индивидуальные и групповые)
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
                
                if lesson_type == 'individual':
                    # Индивидуальное регулярное занятие
                    lesson_id = db.add_lesson(
                        tutor_id=tutor_id,
                        student_id=data.get('student_id'),
                        lesson_date=full_datetime,
                        duration=60,
                        price=1000
                    )
                    if lesson_id:
                        created_count += 1
                        
                else:
                    # Групповое регулярное занятие
                    group_id = data.get('group_id')
                    group_students = db.get_students_by_group(group_id)
                    
                    for student in group_students:
                        lesson_id = db.add_lesson(
                            tutor_id=tutor_id,
                            student_id=student['id'],
                            lesson_date=full_datetime,
                            duration=60,
                            price=500.0,  # Групповые обычно дешевле
                            group_id=group_id
                        )
                        if lesson_id:
                            created_count += 1
            
            # Формируем сообщение об успехе
            if lesson_type == 'individual':
                student = db.get_student_by_id(data.get('student_id'))
                student_name = student['full_name'] if student else "ученика"
                message_text = f"✅ <b>Создано {created_count} регулярных занятий для {student_name}!</b>\n\n"
            else:
                group_name = data.get('group_name', 'группы')
                message_text = f"✅ <b>Создано {created_count} регулярных групповых занятий для {group_name}!</b>\n\n"
            
            message_text += "Занятия добавлены в расписание на месяц вперед."
            
            await callback_query.message.edit_text(
                message_text,
                parse_mode="HTML"
            )
            
        else:
            # Единоразовые занятия
            full_datetime = f"{data.get('date')} {data.get('time')}:00"
            
            if lesson_type == 'individual':
                # Индивидуальное единоразовое занятие
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
                    
            else:
                # Групповое единоразовое занятие
                group_id = data.get('group_id')
                group_students = db.get_students_by_group(group_id)
                success_count = 0
                
                for student in group_students:
                    lesson_id = db.add_lesson(
                        tutor_id=tutor_id,
                        student_id=student['id'],
                        lesson_date=full_datetime,
                        duration=60,
                        price=500.0,
                        group_id=group_id
                    )
                    if lesson_id:
                        success_count += 1
                
                group_name = data.get('group_name', 'группы')
                if success_count > 0:
                    await callback_query.message.edit_text(
                        f"✅ <b>Групповое занятие для {group_name} добавлено!</b>\n\n"
                        f"Создано занятий: {success_count}/{len(group_students)}",
                        parse_mode="HTML"
                    )
                else:
                    await callback_query.message.edit_text(
                        "❌ <b>Ошибка при добавлении группового занятия!</b>\n\n"
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