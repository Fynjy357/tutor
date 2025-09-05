"""Обработчики для уведомлений"""

from aiogram import F
from aiogram import types
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

def setup_notification_handlers(dp, db, notification_manager):
    """Настройка обработчиков уведомлений"""
    logger.info("🔄 Настройка обработчиков уведомлений")
    
    @dp.message(F.text.startswith(("✅ Посещу занятие #", "❌ Не приду #")))
    async def handle_lesson_confirmation(message: types.Message):
        """Обработчик подтверждения занятия"""
        logger.info(f"📨 Получено подтверждение от пользователя {message.from_user.id}: {message.text}")
        
        try:
            # Извлекаем ID занятия из текста
            if "✅ Посещу занятие #" in message.text:
                confirmed = True
                lesson_id = int(message.text.split("#")[1])
                logger.debug(f"✅ Подтверждение занятия #{lesson_id}")
            else:
                confirmed = False
                lesson_id = int(message.text.split("#")[1])
                logger.debug(f"❌ Отмена занятия #{lesson_id}")
            
            # Получаем информацию об ученике
            student = db.get_student_by_telegram_id(message.from_user.id)
            if not student:
                logger.warning(f"⚠️ Ученик не найден по telegram_id: {message.from_user.id}")
                await message.answer("❌ Ошибка: ученик не найден")
                return
            
            logger.debug(f"👤 Найден ученик: {student.get('full_name')}")
            
            # Обновляем подтверждение
            success = notification_manager.update_confirmation(lesson_id, student['id'], confirmed)
            
            if success:
                # Получаем информацию о занятии
                lesson = db.get_lesson_by_id(lesson_id)
                
                if lesson and lesson.get('tutor_telegram_id'):
                    # Форматируем дату для учителя
                    lesson_date = datetime.strptime(lesson['lesson_date'], '%Y-%m-%d %H:%M:%S')
                    
                    tutor_message = f"""
📋 Подтверждение занятия!

Ученик: {student.get('full_name', 'Неизвестно')}
{"✅ Подтвердил занятие" if confirmed else "❌ Отменил занятие"}

📅 Дата: {lesson_date.strftime('%d.%m.%Y')}
⏰ Время: {lesson_date.strftime('%H:%M')}
⏱ Длительность: {lesson.get('duration', 60)} минут
💰 Стоимость: {lesson.get('price', 0)} руб.
                    """
                    
                    try:
                        await message.bot.send_message(
                            chat_id=lesson['tutor_telegram_id'],
                            text=tutor_message
                        )
                        logger.info(f"📤 Уведомление отправлено репетитору {lesson['tutor_telegram_id']}")
                    except Exception as tutor_error:
                        logger.error(f"❌ Ошибка отправки репетитору: {tutor_error}")
                
                # Ответ ученику
                response_text = (
                    "✅ Спасибо за подтверждение! Ждем вас на занятии!" 
                    if confirmed else 
                    "❌ Спасибо, что предупредили! Сообщили вашему репетитору."
                )
                
                await message.answer(
                    response_text,
                    reply_markup=types.ReplyKeyboardRemove()
                )
                logger.info(f"✅ Ответ ученику отправлен")
                
            else:
                logger.error(f"❌ Ошибка при обновлении подтверждения занятия #{lesson_id}")
                await message.answer("❌ Ошибка при обработке подтверждения")
                
        except (ValueError, IndexError):
            logger.warning(f"⚠️ Неверный формат подтверждения: {message.text}")
            await message.answer("❌ Неверный формат подтверждения")
        except Exception as e:
            logger.error(f"❌ Ошибка обработки подтверждения: {e}")
            await message.answer("❌ Произошла ошибка при обработке")