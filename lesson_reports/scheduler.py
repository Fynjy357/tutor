import logging
import sqlite3
import asyncio
from datetime import datetime
from aiogram.utils.keyboard import InlineKeyboardBuilder

logger = logging.getLogger(__name__)

class LessonScheduler:
    def __init__(self, db):
        self.db = db

    async def notify_tutor_about_lesson_end(self, bot):
        """Уведомляет репетитора об окончании занятия"""
        logger.info("🚀 Запуск планировщика уведомлений о завершении занятий")
        while True:
            try:
                logger.info("🔍 Проверка завершенных занятий...")
                now = datetime.now()
                now_str = now.strftime('%Y-%m-%d %H:%M:%S')
                
                with self.db.get_connection() as conn:
                    conn.row_factory = sqlite3.Row
                    cursor = conn.cursor()
                    
                    # Получаем ID первого занятия в группе для callback_data
                    cursor.execute('''
                    SELECT l.group_id, l.lesson_date, l.duration, 
                        t.telegram_id as tutor_telegram_id,
                        g.name as group_name,
                        COUNT(l.id) as student_count,
                        GROUP_CONCAT(s.full_name) as student_names,
                        MIN(l.id) as first_lesson_id
                    FROM lessons l
                    JOIN tutors t ON l.tutor_id = t.id
                    LEFT JOIN groups g ON l.group_id = g.id
                    LEFT JOIN students s ON l.student_id = s.id
                    WHERE l.status = 'planned'
                    AND datetime(l.lesson_date, '+' || l.duration || ' minutes') 
                    BETWEEN datetime(?) AND datetime(?, '+5 minutes')
                    GROUP BY l.group_id, l.lesson_date, l.duration, t.telegram_id, g.name
                    ''', (now_str, now_str))
                    
                    lessons = cursor.fetchall()
                    logger.info(f"Найдено завершенных занятий (группировано): {len(lessons)}")
                    
                    for lesson in lessons:
                        await self._send_lesson_notification(bot, conn, cursor, dict(lesson))
                
                await asyncio.sleep(60)
                
            except Exception as e:
                logger.error(f"❌ Ошибка в фоновой задаче: {e}")
                await asyncio.sleep(60)

    async def _send_lesson_notification(self, bot, conn, cursor, lesson_dict):
        """Отправляет уведомление о завершении занятия"""
        tutor_id = lesson_dict['tutor_telegram_id']
        group_id = lesson_dict['group_id']
        start_time = lesson_dict['lesson_date']
        duration = lesson_dict['duration']
        first_lesson_id = lesson_dict['first_lesson_id']
        
        if group_id:  # Групповое занятие
            logger.info(f"👥 Групповое занятие: группа={lesson_dict['group_name']}, "
                      f"ID={first_lesson_id}, учеников={lesson_dict['student_count']}")
            
            message = f"🎓 Групповое занятие '{lesson_dict['group_name']}' завершено!\n"
            message += f"📅 Время: {start_time}\n"
            message += f"⏱ Длительность: {duration} мин\n"
            message += f"👥 Учеников: {lesson_dict['student_count']}\n\n"
            message += "Заполните отчет по занятию:"
            
            keyboard = InlineKeyboardBuilder()
            keyboard.button(
                text="📝 Заполнить отчет", 
                callback_data=f"group_report:{first_lesson_id}"
            )
            
        else:  # Индивидуальное занятие
            logger.info(f"👤 Индивидуальное занятие: ученик={lesson_dict['student_names']}")
            
            message = f"🎓 Занятие с {lesson_dict['student_names']} завершено!\n"
            message += f"📅 Время: {start_time}\n"
            message += f"⏱ Длительность: {duration} мин\n\n"
            message += "Заполните отчет по занятию:"
            
            keyboard = InlineKeyboardBuilder()
            keyboard.button(
                text="📝 Заполнить отчет", 
                callback_data=f"individual_report:{first_lesson_id}"
            )
        
        reply_markup = keyboard.as_markup()
        
        try:
            await bot.send_message(
                chat_id=tutor_id,
                text=message,
                reply_markup=reply_markup
            )
            
            # Обновляем статус ВСЕХ занятий этой группы
            await self._update_lesson_status(conn, cursor, group_id, start_time, lesson_dict['student_names'])
            
            logger.info(f"✅ Уведомление отправлено репетитору {tutor_id}")
            
        except Exception as e:
            logger.error(f"❌ Ошибка отправки уведомления: {e}")

    async def _update_lesson_status(self, conn, cursor, group_id, start_time, student_names):
        """Обновляет статус занятий"""
        if group_id:
            cursor.execute('''
            UPDATE lessons 
            SET status = 'completed' 
            WHERE group_id = ? AND lesson_date = ? AND status = 'planned'
            ''', (group_id, start_time))
        else:
            cursor.execute('''
            UPDATE lessons 
            SET status = 'completed' 
            WHERE student_id IN (
                SELECT id FROM students WHERE full_name = ?
            ) AND lesson_date = ? AND status = 'planned'
            ''', (student_names, start_time))
        
        conn.commit()
