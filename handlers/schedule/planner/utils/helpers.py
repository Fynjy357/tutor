# handlers/schedule/planner/utils/helpers.py
from datetime import datetime
from database import db

async def get_lesson_info_text(data: dict, price: float) -> str:
    """Формирует текст с информацией о занятии в новом формате"""
    weekdays_ru = {
        'monday': 'Понедельник',
        'tuesday': 'Вторник', 
        'wednesday': 'Среда',
        'thursday': 'Четверг',
        'friday': 'Пятница',
        'saturday': 'Суббота',
        'sunday': 'Воскресенье'
    }
    
    lesson_type = "Индивидуальное занятие" if data['lesson_type'] == 'individual' else "Групповое занятие"
    weekday = weekdays_ru.get(data['weekday'], data['weekday'])
    time = data['time']
    duration = data['duration']
    
    if data['lesson_type'] == 'individual':
        student_id = data.get('student_id')
        if student_id:
            student = db.get_student_by_id(student_id)
            target_name = student['full_name'] if student else "Неизвестный ученик"
    else:
        group_id = data.get('group_id')
        if group_id:
            group = db.get_group_by_id(group_id)
            target_name = group['name'] if group else "Неизвестная группа"
    
    return (
        f"📋 **{lesson_type}**\n"
        f"👤 {target_name}\n"
        f"📅 {weekday}, {time}\n"
        f"⏱️ {duration} мин • 💰 {int(price)} руб"
    )


def validate_time_format(time_text: str) -> bool:
    """Проверяет корректность формата времени"""
    try:
        datetime.strptime(time_text, '%H:%M')
        return True
    except ValueError:
        return False

def validate_duration(duration_text: str) -> bool:
    """Проверяет корректность длительности"""
    try:
        duration = int(duration_text)
        return duration > 0
    except ValueError:
        return False

def validate_price(price_text: str) -> bool:
    """Проверяет корректность стоимости"""
    try:
        price = float(price_text)
        return price > 0
    except ValueError:
        return False
