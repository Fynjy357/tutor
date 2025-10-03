from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from datetime import datetime, timedelta
from database import db

from handlers.schedule.states import AddLessonStates
import logging

router = Router()
logger = logging.getLogger(__name__)

# Обработчик подтверждения занятия
@router.callback_query(AddLessonStates.confirmation, F.data == "confirm_lesson")
async def process_confirmation(callback_query: types.CallbackQuery, state: FSMContext):
    """Обработка подтверждения занятия с переходом к редактированию"""
    await callback_query.answer()
    
    data = await state.get_data()
    tutor_id = db.get_tutor_id_by_telegram_id(callback_query.from_user.id)
    lesson_type = data.get('lesson_type')
    frequency = data.get('frequency')
    
    logger.info(f"Confirming lesson. Type: {lesson_type}, Frequency: {frequency}")
    
    # ДЕБАГ: выводим все данные состояния
    logger.info(f"State data: {data}")
    
    created_lesson_ids = []  # Храним ID созданных занятий
    group_id = None
    
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
                    logger.info(f"🔥 BEFORE ADD LESSON: tutor={tutor_id}, student={data.get('student_id')}, "
                            f"date={full_datetime}, duration=60, price=1000, group=None")
                    lesson_id = db.add_lesson(
                        tutor_id=tutor_id,
                        student_id=data.get('student_id'),
                        lesson_date=full_datetime,
                        duration=60,
                        price=1000
                    )
                    if lesson_id:
                        created_count += 1
                        created_lesson_ids.append(lesson_id)
                        
                else:
                    # Групповое единоразовое занятие
                    group_id = data.get('group_id')
                    
                    # ДОБАВЬТЕ ЭТУ ПРОВЕРКУ ПЕРЕД ЦИКЛОМ!
                    logger.info(f"🔥 Getting students for group {group_id}")
                    group_students = db.get_students_by_group(group_id)
                    logger.info(f"🔥 Group students result: {group_students}")
                    
                    if not group_students:
                        await callback_query.message.edit_text(
                            "❌ <b>В группе нет студентов или ошибка получения!</b>\n\n"
                            "Добавьте студентов в группу перед созданием занятия.",
                            parse_mode="HTML"
                        )
                        await state.clear()
                        return
                    
                    success_count = 0
                    for student in group_students:
                        # ИСПРАВЛЕННЫЙ ЛОГ - используем student из цикла
                        logger.info(f"🔥 BEFORE ADD LESSON: tutor={tutor_id}, student={student['id']}, "
                                f"date={full_datetime}, duration=60, price=500.0, group={group_id}")
                        
                        lesson_id = db.add_lesson(
                            tutor_id=tutor_id,
                            student_id=student['id'],
                            lesson_date=full_datetime,
                            duration=60,
                            price=500.0,
                            group_id=group_id
                        )
                        
                        logger.info(f"🔥 AFTER ADD LESSON: result={lesson_id}")
                        
                        if lesson_id:
                            success_count += 1
                            created_lesson_ids.append(lesson_id)
            
        else:
            # Единоразовые занятия
            full_datetime = f"{data.get('date')} {data.get('time')}:00"
            
            if lesson_type == 'individual':
                # Индивидуальное единоразовое занятие
                student_id = data.get('student_id')  # ДОБАВЬТЕ ЭТУ СТРОКУ
                
                # ИСПРАВЛЕННЫЙ ЛОГ
                logger.info(f"🔥 BEFORE ADD LESSON: tutor={tutor_id}, student={student_id}, "
                        f"date={full_datetime}, duration=60, price=1000, group=None")
                
                lesson_id = db.add_lesson(
                    tutor_id=tutor_id,
                    student_id=student_id,  # ИСПРАВЛЕНО
                    lesson_date=full_datetime,
                    duration=60,
                    price=1000
                )
                
                logger.info(f"🔥 AFTER ADD LESSON: result={lesson_id}")
                
                if lesson_id:
                    created_lesson_ids.append(lesson_id)
                else:
                    await callback_query.message.edit_text(
                        "❌ <b>Ошибка при добавлении занятия!</b>\n\n"
                        "Попробуйте еще раз.",
                        parse_mode="HTML"
                    )
                    return
                    
            else:
                # Групповое единоразовое занятие
                group_id = data.get('group_id')
                group_students = db.get_students_by_group(group_id)
                success_count = 0
                
                for student in group_students:
                    logger.info(f"🔥 BEFORE ADD LESSON: tutor={tutor_id}, student={data.get('student_id')}, "
                            f"date={full_datetime}, duration=60, price=1000, group=None")
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
                        created_lesson_ids.append(lesson_id)
                
                if success_count == 0:
                    await callback_query.message.edit_text(
                        "❌ <b>Ошибка при добавлении группового занятия!</b>\n\n"
                        "Попробуйте еще раз.",
                        parse_mode="HTML"
                    )
                    return
        
        # НЕМЕДЛЕННЫЙ ПЕРЕХОД К РЕДАКТИРОВАНИЮ
        if created_lesson_ids:
            first_lesson_id = created_lesson_ids[0]
            
            # Получаем необходимые данные
            selected_date = data.get('date') if frequency == 'single' else datetime.now().strftime('%Y-%m-%d')
            selected_time = data.get('time')
            
            # Очищаем состояние перед переходом
            await state.clear()
            
            if lesson_type == 'individual':
                # ПРЯМОЙ ВЫЗОВ ФУНКЦИИ РЕДАКТИРОВАНИЯ ДЛЯ ИНДИВИДУАЛЬНОГО ЗАНЯТИЯ
                await show_individual_edit_options_directly(
                    callback_query.message, 
                    first_lesson_id, 
                    state
                )
                
            else:
                # ПРЯМОЙ ВЫЗОВ ФУНКЦИИ РЕДАКТИРОВАНИЯ ДЛЯ ГРУППОВОГО ЗАНЯТИЯ
                await show_group_edit_options_directly(
                    callback_query.message, 
                    group_id, 
                    selected_date, 
                    selected_time, 
                    state
                )
            
            return
        
        # Если не удалось создать занятия
        await callback_query.message.edit_text(
            "❌ <b>Не удалось создать занятия!</b>\n\n"
            "Попробуйте еще раз.",
            parse_mode="HTML"
        )
        
    except Exception as e:
        logger.error(f"Ошибка при создании занятия: {e}", exc_info=True)
        await callback_query.message.edit_text(
            "❌ <b>Ошибка при создании занятия!</b>\n\n"
            f"Ошибка: {str(e)}",
            parse_mode="HTML"
        )

async def show_individual_edit_options_directly(message: types.Message, lesson_id: int, state: FSMContext):
    """Прямой вызов функции редактирования для индивидуального занятия"""
    from handlers.schedule.edit_lesson.individual_handlers import show_edit_options
    
    # Создаем простой callback-like объект
    class SimpleCallback:
        def __init__(self, message, lesson_id):
            self.message = message
            self.data = f"edit_lesson_{lesson_id}"
            self.from_user = message.from_user
            
        async def answer(self):
            pass
    
    callback = SimpleCallback(message, lesson_id)
    await show_edit_options(callback, state)

async def show_group_edit_options_directly(message: types.Message, group_id: int, date: str, time: str, state: FSMContext):
    """Прямой вызов функции редактирования для группового занятия"""
    from handlers.schedule.edit_lesson.group_handlers import show_group_edit_options
    
    # Создаем простой callback-like объект
    class SimpleCallback:
        def __init__(self, message, group_id, date, time):
            self.message = message
            self.data = f"edit_group_{group_id}_{date}_{time}"
            self.from_user = message.from_user
            
        async def answer(self):
            pass
    
    callback = SimpleCallback(message, group_id, date, time)
    await show_group_edit_options(callback, state)