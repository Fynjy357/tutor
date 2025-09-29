from datetime import datetime, timedelta
from database import Database

class ScheduleService:
    def __init__(self):
        self.db = Database()
    
    def get_monthly_schedule_data(self, tutor_id: int, month: int = None, year: int = None) -> dict:
        """Получает данные для месячного расписания"""
        if month is None:
            month = datetime.now().month
        if year is None:
            year = datetime.now().year
        
        # Получаем данные репетитора
        tutor = self.db.get_tutor_by_id(tutor_id)
        tutor_data = {
            'id': tutor[0],
            'name': tutor[2] if len(tutor) > 2 else 'Не указано',
            'phone': tutor[3] if len(tutor) > 3 else 'Не указано'
        }
        
        # Определяем период
        start_date = datetime(year, month, 1)
        if month == 12:
            end_date = datetime(year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = datetime(year, month + 1, 1) - timedelta(days=1)
        
        # Получаем занятия за период
        lessons = self._get_lessons_by_period(tutor_id, start_date, end_date)
        
        # Группируем по дням для расписания
        daily_schedule = self._group_lessons_by_day(lessons)
        
        return {
            'tutor': tutor_data,
            'lessons': lessons,
            'daily_schedule': daily_schedule,
            'month': month,
            'year': year,
            'period': {
                'start': start_date,
                'end': end_date
            }
        }
    
    def _get_lessons_by_period(self, tutor_id: int, start_date: datetime, end_date: datetime) -> list:
        """Получает занятия за указанный период"""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
            SELECT 
                l.*, 
                s.full_name as student_name, 
                g.name as group_name,
                g.id as group_id
            FROM lessons l
            LEFT JOIN students s ON l.student_id = s.id
            LEFT JOIN groups g ON l.group_id = g.id
            WHERE l.tutor_id = ? 
            AND l.lesson_date BETWEEN ? AND ?
            ORDER BY l.lesson_date
            ''', (tutor_id, start_date, end_date))
            
            lessons = cursor.fetchall()
            return [dict(zip([col[0] for col in cursor.description], lesson)) for lesson in lessons]
    
    def _group_lessons_by_day(self, lessons: list) -> dict:
        """Группирует занятия по дням"""
        daily_schedule = {}
        
        for lesson in lessons:
            lesson_date = datetime.strptime(lesson['lesson_date'], '%Y-%m-%d %H:%M:%S')
            date_key = lesson_date.strftime('%Y-%m-%d')
            day_name = self._get_day_name_russian(lesson_date)
            
            if date_key not in daily_schedule:
                daily_schedule[date_key] = {
                    'date': lesson_date,
                    'day_name': day_name,
                    'lessons': []
                }
            
            daily_schedule[date_key]['lessons'].append(lesson)
        
        # Сортируем занятия внутри каждого дня по времени
        for day in daily_schedule.values():
            day['lessons'].sort(key=lambda x: x['lesson_date'])
        
        return daily_schedule
    
    def _get_day_name_russian(self, date: datetime) -> str:
        """Возвращает русское название дня недели"""
        days = {
            0: "Понедельник",
            1: "Вторник", 
            2: "Среда",
            3: "Четверг",
            4: "Пятница",
            5: "Суббота",
            6: "Воскресенье"
        }
        return days.get(date.weekday(), "Неизвестно")

    def get_available_months(self, tutor_id: int) -> list:
        """Возвращает список месяцев, за которые есть данные"""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
            SELECT DISTINCT 
                strftime('%Y', lesson_date) as year,
                strftime('%m', lesson_date) as month
            FROM lessons 
            WHERE tutor_id = ?
            ORDER BY year DESC, month DESC
            ''', (tutor_id,))
            
            months = cursor.fetchall()
            return [
                {
                    'year': int(month[0]),
                    'month': int(month[1]),
                    'name': self._get_month_name(int(month[1]))
                }
                for month in months
            ]

    def _get_month_name(self, month: int) -> str:
        """Возвращает русское название месяца"""
        month_names = {
            1: "Январь", 2: "Февраль", 3: "Март", 4: "Апрель",
            5: "Май", 6: "Июнь", 7: "Июль", 8: "Август",
            9: "Сентябрь", 10: "Октябрь", 11: "Ноябрь", 12: "Декабрь"
        }
        return month_names.get(month, f"Месяц {month}")