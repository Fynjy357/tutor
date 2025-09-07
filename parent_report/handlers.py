import logging
import sqlite3
from aiogram import Bot
from datetime import datetime

logger = logging.getLogger(__name__)

class ParentReportHandlers:
    def __init__(self, db):
        self.db = db
    
    async def send_report_to_parent(self, bot: Bot, lesson_id: int, student_id: int):
        """Отправляет отчет родителю ученика"""
        try:
            # Получаем информацию об отчете и родителе
            with self.db.get_connection() as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute('''
                SELECT lr.*, s.full_name as student_name, s.parent_telegram_id,
                       l.lesson_date, l.duration, t.full_name as tutor_name
                FROM lesson_reports lr
                JOIN students s ON lr.student_id = s.id
                JOIN lessons l ON lr.lesson_id = l.id
                JOIN tutors t ON l.tutor_id = t.id
                WHERE lr.lesson_id = ? AND lr.student_id = ?
                ''', (lesson_id, student_id))
                
                report = cursor.fetchone()
                
                if not report:
                    logger.warning(f"❌ Отчет не найден: lesson_id={lesson_id}, student_id={student_id}")
                    return
                
                report = dict(report)
                
                # Проверяем, есть ли telegram_id у родителя
                parent_telegram_id = report.get('parent_telegram_id')
                if not parent_telegram_id:
                    logger.info(f"❌ У ученика {report['student_name']} нет telegram_id родителя")
                    return
                
                # Формируем сообщение для родителя
                message = f"📊 Отчет о занятии для {report['student_name']}\n\n"
                message += f"📅 Дата: {report['lesson_date']}\n"
                message += f"⏱ Длительность: {report['duration']} мин\n"
                message += f"👨‍🏫 Преподаватель: {report['tutor_name']}\n\n"
                
                # Статус занятия
                if report.get('lesson_held'):
                    message += "✅ Занятие состоялось\n"
                else:
                    message += "❌ Занятие не состоялось\n"
                    await bot.send_message(chat_id=parent_telegram_id, text=message)
                    return
                
                # Оплата
                if report.get('lesson_paid'):
                    message += "💳 Занятие оплачено\n"
                else:
                    message += "⚠️ Занятие не оплачено\n"
                
                # Домашняя работа
                if report.get('homework_done'):
                    message += "📚 Домашняя работа выполнена\n"
                else:
                    message += "📝 Домашняя работа не выполнена\n"
                
                # Комментарий преподавателя
                performance = report.get('student_performance')
                if performance:
                    message += f"\n📝 Комментарий преподавателя:\n{performance}\n"
                
                # Отправляем сообщение родителю
                try:
                    await bot.send_message(
                        chat_id=parent_telegram_id,
                        text=message
                    )
                    logger.info(f"✅ Отчет отправлен родителю ученика {report['student_name']}")
                    
                except Exception as e:
                    logger.error(f"❌ Ошибка отправки отчета родителю: {e}")
                    
        except Exception as e:
            logger.error(f"❌ Ошибка при подготовке отчета для родителя: {e}")
    
    async def send_reports_to_all_parents(self, bot: Bot, lesson_id: int, student_ids: list):
        """Отправляет отчеты всем родителям группы"""
        for student_id in student_ids:
            await self.send_report_to_parent(bot, lesson_id, student_id)