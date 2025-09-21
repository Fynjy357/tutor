import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Set
from aiogram import Bot
from database import Database

logger = logging.getLogger(__name__)

class TrialNotificationManager:
    def __init__(self, bot: Bot):
        self.bot = bot
        self.db = Database()
        self.sent_notifications: Set[int] = set()  # Храним ID пользователей, которым уже отправили уведомление

    async def get_users_with_expiring_trial(self, hours_before: int = 24) -> List[dict]:
        """Получает пользователей, у которых пробный период истекает через указанное количество часов"""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                # Рассчитываем время, через которое истекает пробный период
                expiration_time = datetime.now() + timedelta(hours=hours_before)
                
                query = """
                SELECT p.user_id, p.valid_until, t.telegram_id, t.full_name
                FROM payments p
                JOIN tutors t ON p.user_id = t.telegram_id
                WHERE p.tariff_name = 'Бесплатный пробный период'
                AND p.status = 'succeeded'
                AND p.valid_until BETWEEN datetime('now') AND ?
                """
                
                cursor.execute(query, (expiration_time.strftime('%Y-%m-%d %H:%M:%S'),))
                users = cursor.fetchall()
                
                return users
                
        except Exception as e:
            logger.error(f"Ошибка при получении пользователей с истекающим пробным периодом: {e}")
            return []

    async def send_trial_expiration_notification(self, user_id: int, telegram_id: int, full_name: str, valid_until: str):
        """Отправляет уведомление об окончании пробного периода"""
        try:
            # Проверяем, не отправляли ли уже уведомление этому пользователю
            if user_id in self.sent_notifications:
                logger.info(f"Уведомление уже отправлено пользователю {user_id}, пропускаем")
                return False
            
            # Форматируем дату окончания
            end_date = datetime.strptime(valid_until, '%Y-%m-%d %H:%M:%S')
            formatted_date = end_date.strftime('%d.%m.%Y в %H:%M')
            
            # Создаем клавиатуру с кнопкой оплаты
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="💳 Оплатить подписку", callback_data="payment_menu")]
            ])
            
            message_text = (
                f"👋 <b>{full_name}, большое спасибо, что выбрали наш сервис!</b>\n\n"
                f"⏰ Ваш пробный период истекает <b> {formatted_date}.</b>\n\n"
                f"✨ Понравился весь функционал? \n Не расставайтесь с ним!\n"
                f"Оформите подписку и продолжайте легко управлять групповыми занятиями, учениками и родителями без ограничений.\n\n"
                f"<b>Мы растем и развиваемся благодаря таким пользователям, как вы! 💙.</b>"
            )
            
            await self.bot.send_message(
                chat_id=telegram_id,
                text=message_text,
                reply_markup=keyboard,
                parse_mode='HTML'
            )
            
            # Помечаем, что уведомление отправлено
            self.sent_notifications.add(user_id)
            logger.info(f"Уведомление об окончании пробного периода отправлено пользователю {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка отправки уведомления пользователю {user_id}: {e}")
            return False

    async def check_and_send_trial_notifications(self):
        """Проверяет и отправляет уведомления об окончании пробного периода"""
        try:
            users = await self.get_users_with_expiring_trial(24)
            
            if not users:
                logger.info("Нет пользователей с истекающим пробным периодом")
                return
            
            logger.info(f"Найдено {len(users)} пользователей с истекающим пробным периодом")
            
            sent_count = 0
            for user in users:
                success = await self.send_trial_expiration_notification(
                    user_id=user['user_id'],
                    telegram_id=user['telegram_id'],
                    full_name=user['full_name'],
                    valid_until=user['valid_until']
                )
                if success:
                    sent_count += 1
                # Небольшая задержка между отправками
                await asyncio.sleep(0.5)
            
            logger.info(f"Отправлено {sent_count} уведомлений")
                
        except Exception as e:
            logger.error(f"Ошибка в процессе отправки уведомлений: {e}")

    async def cleanup_expired_notifications(self):
        """Очищает уведомления для пользователей, у которых уже истек пробный период"""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                # Получаем пользователей с истекшим пробным периодом
                cursor.execute('''
                SELECT user_id FROM payments 
                WHERE tariff_name = 'Бесплатный пробный период'
                AND status = 'succeeded'
                AND valid_until < datetime('now')
                ''')
                
                expired_users = [row['user_id'] for row in cursor.fetchall()]
                
                # Удаляем из памяти
                for user_id in expired_users:
                    if user_id in self.sent_notifications:
                        self.sent_notifications.remove(user_id)
                        logger.info(f"Очищено уведомление для пользователя {user_id} (пробный период истек)")
                
        except Exception as e:
            logger.error(f"Ошибка очистки уведомлений: {e}")