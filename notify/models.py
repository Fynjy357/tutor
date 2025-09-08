"""Модели и методы базы данных для уведомлений"""

import sqlite3
from datetime import datetime
import logging
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


logger = logging.getLogger(__name__)

class NotificationManager:
    def __init__(self, db):
        self.db = db
        logger.info("📊 Менеджер уведомлений инициализирован")
        
        # Проверяем формат дат занятий при инициализации
        #self.check_lesson_dates_format()
    
    def get_upcoming_lessons_for_notification(self):
        """Получает занятия, которые нужно уведомить (на сегодня и за 24 часа)"""
        logger.info("🔍 Поиск занятий для уведомления (сегодня + завтра)")
        
        try:
            with self.db.get_connection() as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # 1. Проверим ВСЕ занятия на СЕГОДНЯ и ЗАВТРА
                debug_query = """
                SELECT l.id, l.lesson_date, l.status, 
                    s.full_name as student_name, s.student_telegram_id,
                    t.full_name as tutor_name
                FROM lessons l
                JOIN students s ON l.student_id = s.id
                JOIN tutors t ON l.tutor_id = t.id
                WHERE date(l.lesson_date) IN (date('now'), date('now', '+1 day'))
                """
                
                cursor.execute(debug_query)
                all_upcoming_lessons = [dict(row) for row in cursor.fetchall()]
                
                logger.info(f"📊 Все занятия на сегодня и завтра: {len(all_upcoming_lessons)}")
                for lesson in all_upcoming_lessons:
                    logger.info(f"   📅 #{lesson.get('id')}: {lesson.get('student_name')} - "
                            f"{lesson.get('lesson_date')} - статус: {lesson.get('status')} - "
                            f"TG: {lesson.get('student_telegram_id')}")
                
                # 2. Проверим учеников без telegram_id
                debug_students_query = """
                SELECT s.id, s.full_name, s.student_telegram_id
                FROM students s
                JOIN lessons l ON s.id = l.student_id
                WHERE date(l.lesson_date) IN (date('now'), date('now', '+1 day'))
                AND (s.student_telegram_id IS NULL OR s.student_telegram_id = '')
                """
                
                cursor.execute(debug_students_query)
                students_without_tg = [dict(row) for row in cursor.fetchall()]
                logger.info(f"👥 Ученики без telegram_id: {len(students_without_tg)}")
                for student in students_without_tg:
                    logger.info(f"   ❌ #{student.get('id')}: {student.get('full_name')} - TG: {student.get('student_telegram_id')}")
                
                # 3. Проверим уже отправленные уведомления
                debug_sent_query = """
                SELECT lc.*, l.lesson_date, s.full_name
                FROM lesson_confirmations lc
                JOIN lessons l ON lc.lesson_id = l.id
                JOIN students s ON l.student_id = s.id
                WHERE date(l.lesson_date) IN (date('now'), date('now', '+1 day'))
                AND date(lc.notified_at) = date('now')
                """
                
                cursor.execute(debug_sent_query)
                sent_notifications = [dict(row) for row in cursor.fetchall()]
                logger.info(f"📨 Уже отправленные уведомления: {len(sent_notifications)}")
                for notification in sent_notifications:
                    logger.info(f"   📤 #{notification.get('lesson_id')} - отправлено в {notification.get('notified_at')}")
                
                # 4. Основной запрос - только ученики с telegram_id
                query = """
                SELECT l.*, s.full_name as student_name, s.student_telegram_id,
                    t.full_name as tutor_name, t.telegram_id as tutor_telegram_id
                FROM lessons l
                JOIN students s ON l.student_id = s.id
                JOIN tutors t ON l.tutor_id = t.id
                WHERE date(l.lesson_date) IN (date('now'), date('now', '+1 day'))
                AND l.status = 'planned'
                AND s.student_telegram_id IS NOT NULL 
                AND s.student_telegram_id != ''
                AND NOT EXISTS (
                    SELECT 1 FROM lesson_confirmations lc 
                    WHERE lc.lesson_id = l.id 
                    AND date(lc.notified_at) = date('now')
                )
                """
                
                cursor.execute(query)
                lessons = [dict(row) for row in cursor.fetchall()]
                
                logger.info(f"🎯 Найдено занятий для уведомления: {len(lessons)}")
                
                for lesson in lessons:
                    logger.info(f"   ✅ Для уведомления: #{lesson.get('id')} - {lesson.get('student_name')}")
                
                return lessons
                
        except Exception as e:
            logger.error(f"❌ Ошибка при получении занятий для уведомления: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return []
            
    def check_lesson_dates_format(self):
        """Проверяет формат дат в базе данных"""
        logger.info("🔍 Проверка формата дат занятий")
        try:
            with self.db.get_connection() as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute('''
                SELECT id, lesson_date, status 
                FROM lessons 
                WHERE lesson_date > datetime('now')
                ORDER BY lesson_date 
                LIMIT 10
                ''')
                
                lessons = cursor.fetchall()
                logger.info(f"📊 Примеры дат из базы:")
                
                for lesson in lessons:
                    logger.info(f"   Занятие #{lesson['id']}: '{lesson['lesson_date']}' - {lesson['status']}")
                    
                return True
                
        except Exception as e:
            logger.error(f"❌ Ошибка при проверке формата дат: {e}")
            return False

    def create_notification_record(self, lesson_id, student_tg_id, notification_time):
        """Создает запись о уведомлении в базе данных"""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                # Сначала получим student_id по telegram_id
                cursor.execute('SELECT id FROM students WHERE student_telegram_id = ?', (student_tg_id,))
                student_result = cursor.fetchone()
                
                if not student_result:
                    logger.error(f"❌ Не найден student_id для telegram_id: {student_tg_id}")
                    return None
                    
                student_id = student_result[0]
                
                # Создаем запись в lesson_confirmations с правильным student_id
                cursor.execute('''
                    INSERT INTO lesson_confirmations 
                    (lesson_id, student_id, notified_at)
                    VALUES (?, ?, datetime('now'))
                ''', (lesson_id, student_id))
                
                conn.commit()
                
                # Получаем ID созданной записи
                confirmation_id = cursor.lastrowid
                
                logger.info(f"📝 Создана запись подтверждения для занятия #{lesson_id}, student_id: {student_id}, ID записи: {confirmation_id}")
                return confirmation_id
                
        except Exception as e:
            logger.error(f"❌ Ошибка при создании записи подтверждения: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None

    def update_confirmation(self, lesson_id, student_id, confirmed):
        """Обновляет статус подтверждения занятия"""
        logger.debug(f"🔄 Обновление подтверждения: урок {lesson_id}, ученик {student_id}, статус {confirmed}")
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                UPDATE lesson_confirmations 
                SET confirmed = ?, confirmed_at = CURRENT_TIMESTAMP
                WHERE lesson_id = ? AND student_id = ?
                ''', (confirmed, lesson_id, student_id))
                conn.commit()
                success = cursor.rowcount > 0
                if success:
                    logger.info(f"✅ Подтверждение обновлено успешно")
                else:
                    logger.warning(f"⚠️ Не найдена запись для обновления")
                return success
        except Exception as e:
            logger.error(f"❌ Ошибка при обновлении подтверждения: {e}")
            return False
        
    async def send_notification_to_student(self, bot, lesson, student_telegram_id):
        """Отправляет уведомление ученику с инлайн-кнопками"""
        try:
            lesson_id = lesson['id']
            lesson_date = lesson['lesson_date']
            tutor_name = lesson.get('tutor_name', 'преподаватель')
            
            # Форматируем дату
            try:
                lesson_datetime = datetime.strptime(lesson_date, '%Y-%m-%d %H:%M:%S')
                formatted_date = lesson_datetime.strftime('%d.%m.%Y в %H:%M')
            except:
                formatted_date = lesson_date
            
            message_text = (
                f"📚 Напоминание о занятии\n\n"
                f"🗓️ Дата: {formatted_date}\n"
                f"👨‍🏫 Преподаватель: {tutor_name}\n\n"
                f"Пожалуйста, подтвердите ваше участие:"
            )
            
            # Создаем запись подтверждения и получаем confirmation_id
            notification_time = datetime.strptime(lesson_date, '%Y-%m-%d %H:%M:%S')
            confirmation_id = self.create_notification_record(lesson_id, student_telegram_id, notification_time)
            
            if not confirmation_id:
                logger.error(f"❌ Не удалось создать запись подтверждения для занятия #{lesson_id}")
                return False
            
            # Создаем клавиатуру здесь (убираем импорт get_confirmation_keyboard)
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="✅ Подтвердить", 
                            callback_data=f"notify_confirm_{lesson_id}_{confirmation_id}"
                        ),
                        InlineKeyboardButton(
                            text="❌ Отменить", 
                            callback_data=f"notify_cancel_{lesson_id}_{confirmation_id}"
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            text="🔄 Перенести", 
                            callback_data=f"notify_reschedule_{lesson_id}_{confirmation_id}"
                        )
                    ]
                ]
            )
            
            await bot.send_message(
                chat_id=student_telegram_id,
                text=message_text,
                reply_markup=keyboard
            )
            
            logger.info(f"📨 Уведомление отправлено ученику {student_telegram_id} для занятия #{lesson_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка при отправке уведомления: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
            
        
    def mark_notification_sent(self, confirmation_id):
        """Помечает уведомление как отправленное"""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE lesson_confirmations 
                    SET notified_at = datetime('now'), status = 'sent'
                    WHERE id = ?
                ''', (confirmation_id,))
                conn.commit()
                logger.info(f"✅ Уведомление #{confirmation_id} помечено как отправленное")
                
        except Exception as e:
            logger.error(f"❌ Ошибка при обновлении статуса уведомления: {e}")

    def mark_confirmation(self, confirmation_id, confirmed):
        """Обновляет статус подтверждения занятия"""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE lesson_confirmations 
                    SET confirmed = ?, confirmed_at = datetime('now')
                    WHERE id = ?
                ''', (confirmed, confirmation_id))
                conn.commit()
                logger.info(f"✅ Статус подтверждения обновлен: ID {confirmation_id} -> {confirmed}")
                
        except Exception as e:
            logger.error(f"❌ Ошибка при обновлении статуса подтверждения: {e}")

    def get_teacher_chat_id_by_confirmation(self, confirmation_id):
        """Получает chat_id репетитора по ID подтверждения"""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT t.telegram_id 
                    FROM tutors t
                    JOIN lessons l ON l.tutor_id = t.id
                    JOIN lesson_confirmations lc ON lc.lesson_id = l.id
                    WHERE lc.id = ?
                ''', (confirmation_id,))
                
                result = cursor.fetchone()
                return result[0] if result else None
                
        except Exception as e:
            logger.error(f"❌ Ошибка при получении chat_id репетитора: {e}")
            return None
        
    def get_lesson_info(self, lesson_id):
        """Получает информацию о занятии"""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT l.id, l.lesson_date, s.full_name as student_name
                    FROM lessons l
                    JOIN students s ON l.student_id = s.id
                    WHERE l.id = ?
                ''', (lesson_id,))
                
                result = cursor.fetchone()
                if result:
                    return {
                        'lesson_id': result[0],
                        'lesson_date': result[1],
                        'student_name': result[2]
                    }
                return None
                
        except Exception as e:
            logger.error(f"❌ Ошибка при получении информации о занятии: {e}")
            return None