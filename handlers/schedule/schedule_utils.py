import logging
from datetime import datetime
from database import db

logger = logging.getLogger(__name__)

async def get_upcoming_lessons_text(tutor_id: int) -> str:
    """Формирует текст расписания на неделю с группировкой"""
    lessons = db.get_upcoming_lessons(tutor_id)
    
    if not lessons:
        return "📅 <b>Расписание занятий</b>\n\nНа ближайшую неделю занятий нет."
    
    # Группируем занятия по дате+времени и группе
    schedule_dict = {}
    
    for lesson in lessons:
        lesson_date = datetime.strptime(lesson['lesson_date'], '%Y-%m-%d %H:%M:%S')
        time_key = lesson_date.strftime('%Y-%m-%d %H:%M')
        group_id = lesson.get('group_id')
        lesson_id = lesson['id']  # Уникальный ID занятия
        
        if time_key not in schedule_dict:
            schedule_dict[time_key] = {
                'datetime': lesson_date,
                'individual_lessons': {},  # Меняем на словарь для избежания дубликатов
                'group_lessons': {}
            }
        
        # Проверяем тип занятия
        if group_id:
            if group_id not in schedule_dict[time_key]['group_lessons']:
                group_info = db.get_group_by_id(group_id)
                group_name = group_info['name'] if group_info else f'Группа #{group_id}'
                
                schedule_dict[time_key]['group_lessons'][group_id] = {
                    'group_name': group_name,
                    'students': set(),
                    'duration': lesson['duration'],
                    'price': lesson['price'],
                    'status': lesson['status']
                }
            schedule_dict[time_key]['group_lessons'][group_id]['students'].add(lesson['student_name'])
        else:
            # ИСПРАВЛЕНИЕ: используем уникальный ID занятия как ключ
            if lesson_id not in schedule_dict[time_key]['individual_lessons']:
                schedule_dict[time_key]['individual_lessons'][lesson_id] = lesson
            else:
                logger.warning(f"⚠️ Дубликат занятия ID {lesson_id} уже существует для времени {time_key}")
    
    # Словарь для перевода дней недели
    days_of_week = {
        'Monday': 'понедельник',
        'Tuesday': 'вторник', 
        'Wednesday': 'среда',
        'Thursday': 'четверг',
        'Friday': 'пятница',
        'Saturday': 'суббота',
        'Sunday': 'воскресенье'
    }
    
    # Словарь для перевода месяцев
    months = {
        1: 'января', 2: 'февраля', 3: 'марта', 4: 'апреля',
        5: 'мая', 6: 'июня', 7: 'июля', 8: 'августа',
        9: 'сентября', 10: 'октября', 11: 'ноября', 12: 'декабря'
    }
    
    # Группируем по дням
    days_dict = {}
    for time_key, slot_data in schedule_dict.items():
        date_obj = slot_data['datetime']
        day_key = date_obj.strftime('%Y-%m-%d')
        
        if day_key not in days_dict:
            days_dict[day_key] = {
                'date': date_obj,
                'time_slots': {}
            }
        
        days_dict[day_key]['time_slots'][time_key] = slot_data
    
    # Форматируем расписание
    schedule_text = "📅 <b>Расписание на 14 дней</b>\n\n"
    
    for day_key in sorted(days_dict.keys()):
        day_data = days_dict[day_key]
        date_obj = day_data['date']
        
        # Форматируем дату: "25 сентября, вторник"
        day_number = date_obj.day
        month_name = months[date_obj.month]
        day_of_week_en = date_obj.strftime('%A')
        day_of_week_ru = days_of_week.get(day_of_week_en, day_of_week_en)
        
        schedule_text += f"━━━━━━━━━━━━━━━\n"
        schedule_text += f"🗓️ <b>**{day_number} {month_name}, {day_of_week_ru}**</b>\n"
        schedule_text += f"━━━━━━━━━━━━━━━\n\n"
        
        # Сортируем временные слоты
        for time_key in sorted(day_data['time_slots'].keys()):
            slot_data = day_data['time_slots'][time_key]
            display_time = slot_data['datetime'].strftime('%H:%M')
            
            # Показываем индивидуальные занятия
            for lesson_id, lesson in slot_data['individual_lessons'].items():
                schedule_text += f"<b>**{display_time}**</b> │ Индивидуальное занятие\n"
                schedule_text += f"👤 **{lesson['student_name']}**\n"
                schedule_text += f"⏱️ {lesson['duration']} мин │ 💰 {lesson['price']} руб\n\n"
            
            # Показываем групповые занятия
            for group_id, group_data in slot_data['group_lessons'].items():
                schedule_text += f"<b>**{display_time}**</b> │ Групповое занятие\n"
                schedule_text += f"👥 **{group_data['group_name']}** ({len(group_data['students'])} ученика)\n"
                schedule_text += f"⏱️ {group_data['duration']} мин │ 💰 {group_data['price']} руб\n"
                
                # Ученики без сокращений - как есть в базе
                students = ", ".join(sorted(group_data['students']))
                schedule_text += f"🎓 {students}\n\n"
        
        schedule_text += "\n"
    
    schedule_text += "Выберите действие:"
    
    return schedule_text



# получение расписания на сегодня
async def get_today_schedule_text(tutor_id: int) -> str:
    """Формирует текст расписания на сегодня в новом формате"""
    from datetime import datetime, date, timedelta
    
    today = datetime.now().strftime('%Y-%m-%d')
    lessons = db.get_lessons_by_date(tutor_id, today)
    
    # Русские названия дней недели и месяцев
    weekday_names = {
        0: "понедельник", 1: "вторник", 2: "среда", 3: "четверг",
        4: "пятница", 5: "суббота", 6: "воскресенье"
    }
    
    month_names = {
        1: "января", 2: "февраля", 3: "марта", 4: "апреля",
        5: "мая", 6: "июня", 7: "июля", 8: "августа",
        9: "сентября", 10: "октября", 11: "ноября", 12: "декабря"
    }
    
    current_date = datetime.now()
    day_name = weekday_names[current_date.weekday()]
    date_str = f"{current_date.day} {month_names[current_date.month]}, {day_name}"
    
    if not lessons:
        # Финансовая статистика
        current_month = datetime.now().month
        current_year = datetime.now().year
        
        current_month_earnings = db.get_earnings_by_period(
            tutor_id, 
            date(current_year, current_month, 1), 
            datetime.now().date()
        )
        
        if current_month == 1:
            prev_month = 12
            prev_year = current_year - 1
        else:
            prev_month = current_month - 1
            prev_year = current_year
        
        prev_month_earnings = db.get_earnings_by_period(
            tutor_id,
            date(prev_year, prev_month, 1),
            date(prev_year, prev_month, 1).replace(day=28) + timedelta(days=4)
        )
        
        active_students_count = db.get_active_students_count(tutor_id)
        
        return (
            f"📅 <b>Расписание на сегодня</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🗓️ <b>{date_str.capitalize()}</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"📭 <b>Занятий нет</b>\n\n"
            f"👨‍🎓 <b>Активных учеников:</b> {active_students_count}\n"
            f"💰 <b>Заработано в {month_names[current_month]}:</b> {current_month_earnings} руб\n"
            f"📊 <b>Заработано в {month_names[prev_month]}:</b> {prev_month_earnings} руб"
        )
    
    # Группируем занятия по времени
    schedule_dict = {}
    
    for lesson in lessons:
        lesson_date = datetime.strptime(lesson['lesson_date'], '%Y-%m-%d %H:%M:%S')
        time_key = lesson_date.strftime('%H:%M')
        group_id = lesson.get('group_id')
        lesson_id = lesson['id']
        
        if time_key not in schedule_dict:
            schedule_dict[time_key] = {
                'datetime': lesson_date,
                'individual_lessons': {},
                'group_lessons': {}
            }
        
        if group_id:
            if group_id not in schedule_dict[time_key]['group_lessons']:
                group_info = db.get_group_by_id(group_id)
                group_name = group_info['name'] if group_info else f'Группа #{group_id}'
                
                schedule_dict[time_key]['group_lessons'][group_id] = {
                    'group_name': group_name,
                    'students': set(),
                    'duration': lesson['duration'],
                    'price': lesson['price'],
                    'status': lesson['status']
                }
            schedule_dict[time_key]['group_lessons'][group_id]['students'].add(lesson['student_name'])
        else:
            if lesson_id not in schedule_dict[time_key]['individual_lessons']:
                schedule_dict[time_key]['individual_lessons'][lesson_id] = lesson
    
    # Форматируем расписание в новом стиле
    schedule_text = (
        f"📅 <b>Расписание на сегодня</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🗓️ <b>{date_str.capitalize()}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    )
    
    for time_key in sorted(schedule_dict.keys()):
        slot_data = schedule_dict[time_key]
        display_time = slot_data['datetime'].strftime('%H:%M')
        
        # Индивидуальные занятия
        for lesson_id, lesson in slot_data['individual_lessons'].items():
            schedule_text += (
                f"<b>{display_time}</b> │ Индивидуальное занятие\n"
                f"👤 <b>{lesson['student_name']}</b>\n"
                f"⏱️ {lesson['duration']} мин │ 💰 {int(lesson['price'])} руб\n\n"
            )
        
        # Групповые занятия
        for group_id, group_data in slot_data['group_lessons'].items():
            student_count = len(group_data['students'])
            students_text = ", ".join(sorted(group_data['students']))
            
            schedule_text += (
                f"<b>{display_time}</b> │ Групповое занятие\n"
                f"👥 <b>{group_data['group_name']}</b> ({student_count} ученика)\n"
                f"⏱️ {group_data['duration']} мин │ 💰 {int(group_data['price'])} руб\n"
                f"🎓 {students_text}\n\n"
            )
    
    # Добавляем финансовую статистику
    current_month = datetime.now().month
    current_year = datetime.now().year
    
    current_month_earnings = db.get_earnings_by_period(
        tutor_id, 
        date(current_year, current_month, 1), 
        datetime.now().date()
    )
    
    if current_month == 1:
        prev_month = 12
        prev_year = current_year - 1
    else:
        prev_month = current_month - 1
        prev_year = current_year
    
    prev_month_earnings = db.get_earnings_by_period(
        tutor_id,
        date(prev_year, prev_month, 1),
        date(prev_year, prev_month, 1).replace(day=28) + timedelta(days=4)
    )
    
    active_students_count = db.get_active_students_count(tutor_id)
    
    schedule_text += (
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📊 <b>Статистика</b>\n\n"
        f"👨‍🎓 <b>Активных учеников:</b> {active_students_count}\n"
        f"💰 <b>Заработано в {month_names[current_month]}:</b> {current_month_earnings} руб\n"
        f"📈 <b>Заработано в {month_names[prev_month]}:</b> {prev_month_earnings} руб"
    )
    
    return schedule_text

