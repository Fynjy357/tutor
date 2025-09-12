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
        
        if time_key not in schedule_dict:
            schedule_dict[time_key] = {
                'datetime': lesson_date,
                'individual_lessons': [],
                'group_lessons': {}
            }
        
        # Проверяем тип занятия
        if group_id:
            if group_id not in schedule_dict[time_key]['group_lessons']:
                # ПРАВИЛЬНО получаем название группы из базы
                group_info = db.get_group_by_id(group_id)
                group_name = group_info['name'] if group_info else f'Группа #{group_id}'
                
                schedule_dict[time_key]['group_lessons'][group_id] = {
                    'group_name': group_name,  # Используем правильное название
                    'students': set(),
                    'duration': lesson['duration'],
                    'price': lesson['price'],
                    'status': lesson['status']
                }
            # Добавляем ученика в set
            schedule_dict[time_key]['group_lessons'][group_id]['students'].add(lesson['student_name'])
        else:
            schedule_dict[time_key]['individual_lessons'].append(lesson)
    
    # Форматируем расписание
    schedule_text = "📅 <b>Расписание занятий на неделю</b>\n\n"
    
    for time_key in sorted(schedule_dict.keys()):
        slot_data = schedule_dict[time_key]
        display_time = slot_data['datetime'].strftime('%d.%m %H:%M')
        
        schedule_text += f"🕐 <b>{display_time}</b>\n"
        
        # Показываем групповые занятия
        for group_id, group_data in slot_data['group_lessons'].items():
            schedule_text += f"👥 <b>Группа: {group_data['group_name']}</b>\n"
            schedule_text += f"⏱ Длительность: {group_data['duration']} мин\n"
            schedule_text += f"💰 Цена: {group_data['price']} руб\n"
            schedule_text += f"📊 Статус: {group_data['status']}\n"
            schedule_text += f"👨‍🎓 Учеников: {len(group_data['students'])}\n"
            
            # Список учеников
            students = ", ".join(sorted(group_data['students']))
            schedule_text += f"🎓 Ученики: {students}\n"
        
        # Показываем индивидуальные занятия
        for lesson in slot_data['individual_lessons']:
            schedule_text += f"👤 {lesson['student_name']}\n"
            schedule_text += f"⏱ Длительность: {lesson['duration']} мин\n"
            schedule_text += f"💰 Цена: {lesson['price']} руб\n"
            schedule_text += f"📊 Статус: {lesson['status']}\n"
        
        schedule_text += "───────────────\n"
    
    schedule_text += "\nВыберите действие:"
    
    return schedule_text


# получение расписания на сегодня
async def get_today_schedule_text(tutor_id: int) -> str:
    """Формирует текст расписания на сегодня"""
    from datetime import datetime
    today = datetime.now().strftime('%Y-%m-%d')
    lessons = db.get_lessons_by_date(tutor_id, today)
    
    if not lessons:
        return "У вас сегодня не запланировано занятий."
    
    # Группируем занятия по времени
    schedule_dict = {}
    
    for lesson in lessons:
        lesson_date = datetime.strptime(lesson['lesson_date'], '%Y-%m-%d %H:%M:%S')
        time_key = lesson_date.strftime('%H:%M')
        group_id = lesson.get('group_id')
        
        if time_key not in schedule_dict:
            schedule_dict[time_key] = {
                'datetime': lesson_date,
                'individual_lessons': [],
                'group_lessons': {}
            }
        
        # Проверяем тип занятия
        if group_id:
            if group_id not in schedule_dict[time_key]['group_lessons']:
                # ПРАВИЛЬНО получаем название группы из базы
                group_info = db.get_group_by_id(group_id)
                group_name = group_info['name'] if group_info else f'Группа #{group_id}'
                
                schedule_dict[time_key]['group_lessons'][group_id] = {
                    'group_name': group_name,
                    'students': set(),  # Используем set для уникальности
                    'duration': lesson['duration'],
                    'price': lesson['price'],
                    'status': lesson['status']
                }
            # Добавляем ученика в set (автоматически убирает дубликаты)
            schedule_dict[time_key]['group_lessons'][group_id]['students'].add(lesson['student_name'])
        else:
            schedule_dict[time_key]['individual_lessons'].append(lesson)
    
    # Форматируем расписание
    schedule_text = "Ваше расписание на сегодня:\n\n"
    
    for time_key in sorted(schedule_dict.keys()):
        slot_data = schedule_dict[time_key]
        display_time = slot_data['datetime'].strftime('%H:%M')
        
        schedule_text += f"🕐 <b>{display_time}</b>\n"
        
        # Показываем групповые занятия
        for group_id, group_data in slot_data['group_lessons'].items():
            schedule_text += f"👥 <b>Группа: {group_data['group_name']}</b>\n"
            schedule_text += f"⏱ Длительность: {group_data['duration']} мин\n"
            schedule_text += f"💰 Цена: {group_data['price']} руб\n"
            schedule_text += f"📊 Статус: {group_data['status']}\n"
            schedule_text += f"👨‍🎓 Учеников: {len(group_data['students'])}\n"
            
            # Список учеников (преобразуем set в отсортированный список)
            students = ", ".join(sorted(group_data['students']))
            schedule_text += f"🎓 Ученики: {students}\n"
        
        # Показываем индивидуальные занятия
        for lesson in slot_data['individual_lessons']:
            schedule_text += f"👤 {lesson['student_name']}\n"
            schedule_text += f"⏱ Длительность: {lesson['duration']} мин\n"
            schedule_text += f"💰 Цена: {lesson['price']} руб\n"
            schedule_text += f"📊 Статус: {lesson['status']}\n"
        
        schedule_text += "───────────────\n"
    
    return schedule_text