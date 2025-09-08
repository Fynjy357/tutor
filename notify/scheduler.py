"""Планировщик уведомлений"""

import asyncio
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

async def lesson_notification_scheduler(bot, notification_manager):
    """Планировщик уведомлений о занятиях"""
    logger.info("🚀 Планировщик уведомлений запущен")
    
    while True:
        try:
            lessons_to_notify = notification_manager.get_upcoming_lessons_for_notification()
            logger.info(f"📋 Найдено занятий для уведомления: {len(lessons_to_notify)}")
            
            for lesson in lessons_to_notify:
                # Получаем telegram_id - ключ student_telegram_id
                student_telegram_id = lesson.get('student_telegram_id')
                student_id = lesson.get('student_id')
                lesson_id = lesson.get('id')
                
                logger.info(f"🔍 Анализ занятия #{lesson_id}: telegram_id={student_telegram_id}")
                
                if not student_telegram_id:
                    logger.warning(f"⚠️ У ученика занятия #{lesson_id} не указан telegram_id")
                    continue
                
                if not student_id:
                    logger.error(f"❌ Не найден student_id для занятия #{lesson_id}")
                    continue
                
                logger.info(f"📩 Обрабатываем занятие #{lesson_id} для ученика {student_telegram_id} (ID: {student_id})")
                
                # Получаем время занятия - ключ lesson_date
                lesson_time_str = lesson.get('lesson_date')
                
                if not lesson_time_str:
                    logger.error(f"❌ Не указано время занятия #{lesson_id}")
                    continue
                
                try:
                    lesson_time = datetime.strptime(str(lesson_time_str), '%Y-%m-%d %H:%M:%S')
                    notification_time = lesson_time - timedelta(hours=24)
                    logger.info(f"⏰ Время занятия: {lesson_time}, время уведомления: {notification_time}")
                except ValueError as e:
                    logger.error(f"❌ Неверный формат времени занятия #{lesson_id}: {lesson_time_str}. Ошибка: {e}")
                    continue
                
                # Отправляем уведомление (метод сам создаст запись подтверждения)
                success = await notification_manager.send_notification_to_student(
                    bot, lesson, student_telegram_id
                )
                
                if success:
                    logger.info(f"✅ Уведомление отправлено успешно")
                else:
                    logger.error(f"❌ Не удалось отправить уведомление")
            
            # Ждем 5 минут перед следующей проверкой
            await asyncio.sleep(300)
            
        except Exception as e:
            logger.error(f"❌ Критическая ошибка в планировщике уведомлений: {e}")
            await asyncio.sleep(60)

