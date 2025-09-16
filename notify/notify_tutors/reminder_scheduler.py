# notify/notify_tutors/reminder_scheduler.py
import asyncio
import logging
from datetime import datetime
from database import db  # Импортируем вашу базу данных

logger = logging.getLogger(__name__)

class ReminderScheduler:
    def __init__(self, bot):
        self.bot = bot
        self.is_running = False
        self.task = None

    async def start(self):
        """Запуск планировщика напоминаний"""
        if self.is_running:
            logger.warning("Планировщик уже запущен")
            return
            
        self.is_running = True
        logger.info("🚀 Планировщик напоминаний запущен")
        
        # Сбрасываем напоминания для прошедших занятий при запуске
        reset_count = db.reset_reminders_for_past_lessons()
        logger.info(f"Сброшено {reset_count} напоминаний для прошедших занятий")
        
        self.task = asyncio.create_task(self._scheduler_loop())
        return self.task

    async def _scheduler_loop(self):
        """Основной цикл планировщика с отправкой напоминаний"""
        try:
            while self.is_running:
                try:
                    # Проверяем и отправляем напоминания
                    await self.check_and_send_reminders()
                    await asyncio.sleep(300)  # Проверка каждые 5 минут
                    
                except Exception as e:
                    logger.error(f"Ошибка в цикле планировщика: {e}")
                    await asyncio.sleep(60)
                    
        except asyncio.CancelledError:
            logger.info("Планировщик напоминаний остановлен по запросу")
        except Exception as e:
            logger.error(f"Критическая ошибка в планировщике: {e}")
        finally:
            self.is_running = False
            logger.info("Цикл планировщика завершен")

    async def check_and_send_reminders(self):
        """Проверяет и отправляет напоминания о занятиях в ближайшие 60 минут"""
        try:
            current_time = datetime.now().strftime("%H:%M:%S")
            logger.debug(f"Проверка напоминаний в {current_time}")
            
            lessons = db.get_lessons_for_reminder()
            
            # Словарь для отслеживания уже отправленных групповых занятий
            sent_group_lessons = {}
            
            if lessons:
                logger.info(f"Найдено {len(lessons)} занятий для напоминания")
                
                for lesson in lessons:
                    try:
                        # Проверяем, является ли занятие групповым
                        group_id = lesson.get('group_id')
                        
                        if group_id:  # Это групповое занятие
                            if group_id not in sent_group_lessons:
                                # Отправляем напоминание о групповом занятии
                                await self.send_group_lesson_reminder(lesson)
                                sent_group_lessons[group_id] = True
                                
                                # Помечаем ВСЕ занятия этой группы как отправленные
                                self.mark_group_lessons_as_sent(group_id)
                                logger.info(f"✅ Групповое напоминание отправлено для группы #{group_id}")
                            else:
                                logger.debug(f"Пропускаем дублирующее групповое занятие #{group_id}")
                        else:
                            # Это индивидуальное занятие
                            await self.send_lesson_reminder(lesson)
                            if db.mark_reminder_sent(lesson['lesson_id']):
                                logger.info(f"✅ Индивидуальное напоминание отправлено для занятия #{lesson['lesson_id']}")
                            else:
                                logger.error(f"❌ Не удалось пометить напоминание как отправленное для занятия #{lesson['lesson_id']}")
                                
                    except Exception as e:
                        logger.error(f"Ошибка при отправке напоминания для занятия #{lesson['lesson_id']}: {e}")
            else:
                logger.debug("Занятий для напоминания нет")
                
        except Exception as e:
            logger.error(f"Ошибка при проверке напоминаний: {e}")

    async def send_lesson_reminder(self, lesson):
        """Отправляет напоминание о занятии репетитору"""
        try:
            tutor_telegram_id = lesson['tutor_telegram_id']
            lesson_date = datetime.strptime(lesson['lesson_date'], '%Y-%m-%d %H:%M:%S')
            formatted_date = lesson_date.strftime('%d.%m.%Y в %H:%M')
            
            message = (
                f"⏰ Напоминание о занятии!\n\n"
                f"📚 У вас запланировано занятие:\n"
                f"👨‍🎓 Студент: {lesson['student_name']}\n"
                f"📅 Дата и время: {formatted_date}\n"
                f"⏱ Продолжительность: {lesson['duration']} минут\n\n"
                f"Не забудьте подготовиться к занятию! 🎯"
            )
            
            await self.bot.send_message(
                chat_id=tutor_telegram_id,
                text=message
            )
            logger.info(f"✅ Сообщение успешно отправлено репетитору {tutor_telegram_id} о занятии {lesson['lesson_id']}")
            
        except Exception as e:
            logger.error(f"💥 Ошибка при отправке напоминания для занятия {lesson['lesson_id']}: {e}")

    async def send_group_lesson_reminder(self, lesson):
        """Отправляет напоминание о групповом занятии"""
        try:
            tutor_telegram_id = lesson['tutor_telegram_id']
            lesson_date = datetime.strptime(lesson['lesson_date'], '%Y-%m-%d %H:%M:%S')
            formatted_date = lesson_date.strftime('%d.%m.%Y в %H:%M')
            
            # Получаем количество студентов в группе
            group_id = lesson['group_id']
            students = db.get_students_in_group(group_id)
            students_count = len(students) if students else 0
            
            # Получаем название группы
            group = db.get_group_by_id(group_id)
            group_name = group['name'] if group else 'Без названия'
            
            message = (
                f"⏰ Напоминание о групповом занятии!\n\n"
                f"👥 Группа: {group_name}\n"
                f"👨‍🎓 Количество студентов: {students_count}\n"
                f"📅 Дата и время: {formatted_date}\n"
                f"⏱ Продолжительность: {lesson['duration']} минут\n\n"
                f"Не забудьте подготовиться к занятию! 🎯"
            )
            
            await self.bot.send_message(
                chat_id=tutor_telegram_id,
                text=message
            )
            logger.info(f"✅ Групповое напоминание отправлено репетитору {tutor_telegram_id} для группы #{group_id}")
            
        except Exception as e:
            logger.error(f"💥 Ошибка при отправке группового напоминания: {e}")

    def mark_group_lessons_as_sent(self, group_id):
        """Помечает все занятия группы как отправленные"""
        try:
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                UPDATE lessons 
                SET reminder_sent = 1 
                WHERE group_id = ? 
                AND status = 'planned'
                AND reminder_sent = 0
                ''', (group_id,))
                conn.commit()
                marked_count = cursor.rowcount
                logger.info(f"Помечено {marked_count} занятий группы #{group_id} как отправленные")
                return marked_count
        except Exception as e:
            logger.error(f"Ошибка при отметке групповых занятий: {e}")
            return 0

    async def stop(self):
        """Корректная остановка планировщика"""
        if not self.is_running:
            logger.info("Планировщик уже остановлен")
            return
            
        logger.info("Остановка планировщика напоминаний...")
        self.is_running = False
        
        if self.task and not self.task.done():
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
            except Exception as e:
                logger.error(f"Ошибка при ожидании остановки задачи: {e}")
        
        logger.info("Планировщик напоминаний успешно остановлен")

    async def send_custom_reminder(self, tutor_id: int, message: str):
        """Отправляет кастомное напоминание репетитору"""
        try:
            # Получаем telegram_id репетитора
            tutor_info = db.get_tutor_by_id(tutor_id)
            if tutor_info and tutor_info.get('telegram_id'):
                await self.bot.send_message(
                    chat_id=tutor_info['telegram_id'],
                    text=f"📢 Напоминание: {message}"
                )
                logger.info(f"Кастомное напоминание отправлено репетитору {tutor_id}")
                return True
            else:
                logger.warning(f"Не найден telegram_id для репетитора {tutor_id}")
                return False
                
        except Exception as e:
            logger.error(f"Ошибка при отправке кастомного напоминания: {e}")
            return False