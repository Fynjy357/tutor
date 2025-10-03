from datetime import datetime
import re
from database import db


from datetime import datetime
from aiogram import types
from aiogram.fsm.context import FSMContext
from .keyboards import get_lesson_selection_keyboard
from .edit_lesson import EditLessonStates

def group_lessons_by_date(lessons):
    """Группировка занятий по дате"""
    lessons_by_date = {}
    for lesson in lessons:
        lesson_date = lesson['lesson_date'].split()[0]
        if lesson_date not in lessons_by_date:
            lessons_by_date[lesson_date] = []
        lessons_by_date[lesson_date].append(lesson)
    return lessons_by_date

def group_lessons_by_time(lessons):
    """Группировка занятий по времени и группе"""
    grouped_lessons = {}
    for lesson in lessons:
        time_str = lesson['lesson_date'].split()[1][:5]
        group_id = lesson['group_id']
        
        if group_id:
            # Групповое занятие
            key = f"{time_str}_group_{group_id}"
            if key not in grouped_lessons:
                grouped_lessons[key] = {
                    'time': time_str,
                    'group_id': group_id,
                    'group_name': lesson['group_name'],
                    'count': 0,
                    'lesson_ids': []
                }
            grouped_lessons[key]['count'] += 1
            grouped_lessons[key]['lesson_ids'].append(lesson['id'])
        else:
            # Индивидуальное занятие
            key = f"{time_str}_individual_{lesson['id']}"
            grouped_lessons[key] = {
                'time': time_str,
                'student_name': lesson['student_name'],
                'is_group': False,
                'lesson_id': lesson['id']
            }
    return grouped_lessons

def validate_date(date_str):
    """Проверка валидности даты"""
    date_pattern = r'^\d{2}\.\d{2}\.\d{4}$'
    if not re.match(date_pattern, date_str):
        return False, "❌ Неверный формат даты. Используйте ДД.ММ.ГГГГ"
    
    try:
        day, month, year = date_str.split('.')
        datetime(int(year), int(month), int(day))
        return True, None
    except ValueError:
        return False, "❌ Неверная дата. Проверьте правильность ввода."

def validate_time(time_str):
    """Проверка валидности времени"""
    time_pattern = r'^\d{2}:\d{2}$'
    if not re.match(time_pattern, time_str):
        return False, "❌ Неверный формат времени. Используйте ЧЧ:ММ"
    
    try:
        hours, minutes = time_str.split(':')
        if not (0 <= int(hours) <= 23 and 0 <= int(minutes) <= 59):
            return False, "❌ Неверное время. Часы: 00-23, минуты: 00-59"
        return True, None
    except ValueError:
        return False, "❌ Неверный формат времени."

def validate_price(price_str):
    """Проверка валидности цены"""
    try:
        price = float(price_str)
        if price <= 0:
            return False, "❌ Стоимость должна быть положительным числом."
        return True, price
    except ValueError:
        return False, "❌ Введите число. Например: 1500 или 1200.50"

def validate_duration(duration_str):
    """Проверка валидности длительности"""
    try:
        duration = int(duration_str)
        if duration <= 0:
            return False, "❌ Длительность должна быть положительным числом."
        return True, duration
    except ValueError:
        return False, "❌ Введите целое число. Например: 60 или 90"

def format_datetime_for_db(date_str, time_str):
    """Форматирование даты и времени для БД"""
    day, month, year = date_str.split('.')
    db_date = f"{year}-{month}-{day}"
    return f"{db_date} {time_str}:00"

async def show_lessons_for_editing(callback_query: types.CallbackQuery, state: FSMContext, selected_date: str):
    """Показать уроки для редактирования (общая функция)"""
    tutor_id = db.get_tutor_id_by_telegram_id(callback_query.from_user.id)
    lessons = db.get_lessons_by_date(tutor_id, selected_date)
    grouped_lessons = group_lessons_by_time(lessons)
    keyboard = get_lesson_selection_keyboard(grouped_lessons, selected_date)
    
    date_obj = datetime.strptime(selected_date, "%Y-%m-%d")
    display_date = date_obj.strftime("%d.%m.%Y")
    
    await callback_query.message.edit_text(
        f"📅 <b>Занятия на {display_date}:</b>\n\n"
        "👤 - индивидуальное занятие\n"
        "👥 - групповое занятие\n\n"
        "Выберите занятие для редактирования:",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await state.set_state(EditLessonStates.choosing_lesson)