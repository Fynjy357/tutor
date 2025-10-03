# На будущее
# import sqlite3
# import pytz
# from datetime import datetime, timedelta
# from typing import Optional, List, Dict, Any
# from database import Database

# class TimezoneAwareDatabase:
#     def __init__(self, db_name='tutor_bot.db'):
#         self.original_db = Database(db_name)
#         self.default_tz = pytz.timezone('Europe/Moscow')
    
#     def __getattr__(self, name):
#         """Перенаправляем все вызовы к оригинальной базе"""
#         return getattr(self.original_db, name)
    
#     def _convert_to_utc(self, dt: datetime) -> datetime:
#         """Конвертирует datetime в UTC"""
#         if dt.tzinfo is not None:
#             return dt.astimezone(pytz.utc).replace(tzinfo=None)
#         # Если время без таймзоны, считаем что оно в Europe/Moscow
#         localized = self.default_tz.localize(dt)
#         return localized.astimezone(pytz.utc).replace(tzinfo=None)
    
#     def _convert_from_utc(self, dt_str: str, to_tz: pytz.timezone = None) -> datetime:
#         """Конвертирует строку из БД в локальное время"""
#         if to_tz is None:
#             to_tz = self.default_tz
        
#         # Парсим строку из SQLite
#         if isinstance(dt_str, str):
#             try:
#                 # Пробуем разные форматы
#                 for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M:%S.%f']:
#                     try:
#                         naive_dt = datetime.strptime(dt_str, fmt)
#                         break
#                     except ValueError:
#                         continue
#                 else:
#                     return dt_str  # Если не удалось распарсить, возвращаем как есть
#             except:
#                 return dt_str
#         else:
#             naive_dt = dt_str
        
#         # Конвертируем в локальное время
#         utc_dt = pytz.utc.localize(naive_dt)
#         return utc_dt.astimezone(to_tz)
    
#     def _process_result(self, result: List[Dict], user_tz: pytz.timezone = None) -> List[Dict]:
#         """Обрабатывает результат, конвертируя времена"""
#         if user_tz is None:
#             user_tz = self.default_tz
            
#         processed = []
#         for row in result:
#             new_row = {}
#             for key, value in row.items():
#                 if 'date' in key.lower() or 'time' in key.lower():
#                     if value and isinstance(value, (str, datetime)):
#                         new_row[key] = self._convert_from_utc(value, user_tz)
#                     else:
#                         new_row[key] = value
#                 else:
#                     new_row[key] = value
#             processed.append(new_row)
#         return processed
    
#     # Переопределяем ключевые методы работы со временем
    
#     def add_lesson(self, tutor_id: int, student_id: int, lesson_date: datetime, 
#                   duration: int, price: float, status: str = "planned", group_id: int = None):
#         """Добавляет занятие с автоматической конвертацией в UTC"""
#         utc_date = self._convert_to_utc(lesson_date)
#         return self.original_db.add_lesson(tutor_id, student_id, utc_date, duration, price, status, group_id)
    
#     def get_upcoming_lessons(self, tutor_id: int, days: int = 14, user_tz: pytz.timezone = None):
#         """Получает занятия с конвертацией времени"""
#         result = self.original_db.get_upcoming_lessons(tutor_id, days)
#         return self._process_result(result, user_tz)
    
#     def get_lessons_by_date(self, tutor_id: int, date_str: str, user_tz: pytz.timezone = None):
#         """Получает занятия по дате с конвертацией"""
#         try:
#             # Пробуем разные форматы даты
#             try:
#                 # Формат YYYY-MM-DD (из базы данных)
#                 user_date = datetime.strptime(date_str, "%Y-%m-%d")
#             except ValueError:
#                 try:
#                     # Формат DD.MM.YYYY (от пользователя)
#                     user_date = datetime.strptime(date_str, "%d.%m.%Y")
#                 except ValueError:
#                     # Если оба формата не подходят, используем текущую дату
#                     user_date = datetime.now()
#                     print(f"⚠️ Неизвестный формат даты: {date_str}. Использую текущую дату.")
            
#             # Конвертируем дату пользователя в UTC
#             localized = self.default_tz.localize(user_date)
#             utc_date = localized.astimezone(pytz.utc).strftime("%Y-%m-%d")
            
#             result = self.original_db.get_lessons_by_date(tutor_id, utc_date)
#             return self._process_result(result, user_tz)
#         except Exception as e:
#             print(f"❌ Ошибка в get_lessons_by_date: {e}")
#             return []

    
#     def get_lessons_for_reminder(self):
#         """Получает занятия для напоминания"""
#         result = self.original_db.get_lessons_for_reminder()
#         return self._process_result(result)
    
#     def get_lesson_by_id(self, lesson_id: int, user_tz: pytz.timezone = None):
#         """Получает занятие по ID с конвертацией времени"""
#         result = self.original_db.get_lesson_by_id(lesson_id)
#         if result:
#             return self._process_result([result], user_tz)[0]
#         return None

# # Глобальный экземпляр с поддержкой таймзон
# db = TimezoneAwareDatabase()
