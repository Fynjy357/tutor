from datetime import datetime, timedelta
import time
from typing import Optional
from database import Database
import logging
import sqlite3

logger = logging.getLogger(__name__)

class PaymentManager:
    @staticmethod
    async def get_payment_info(user_id: int) -> dict:
        """Получает актуальную информацию о подписке пользователя из таблицы payments"""
        try:
            db = Database()
            with db.get_connection() as conn:
                cursor = conn.cursor()
                
                # Ищем последний УСПЕШНЫЙ платеж пользователя с valid_until
                query = """
                    SELECT tariff_name, amount, status, created_at, valid_until 
                    FROM payments 
                    WHERE user_id = ? 
                    AND status = 'succeeded'
                    ORDER BY created_at DESC 
                    LIMIT 1
                """
                cursor.execute(query, (user_id,))
                result = cursor.fetchone()
                
                logger.info(f"DEBUG: Payment query result for user {user_id}: {result}")
                
                if result:
                    # Используем valid_undo из базы данных
                    if result['valid_until']:
                        valid_until = datetime.strptime(result['valid_until'], '%Y-%m-%d %H:%M:%S')
                    else:
                        # Если valid_until нет, рассчитываем от даты оплаты
                        payment_date = datetime.strptime(result['created_at'], '%Y-%m-%d %H:%M:%S')
                        valid_until = payment_date + timedelta(days=30)
                    
                    logger.info(f"DEBUG: Valid until: {valid_until}, Now: {datetime.now()}")
                    
                    return {
                        'is_active': valid_until > datetime.now(),
                        'valid_until': valid_until.strftime('%Y-%m-%d %H:%M:%S'),
                        'tariff': result['tariff_name']
                    }
                else:
                    logger.info(f"DEBUG: No successful payments found for user {user_id}")
                    return {'is_active': False}
                        
        except Exception as e:
            logger.error(f"Error getting payment info for user {user_id}: {e}")
            return {'is_active': False}

    @staticmethod
    async def create_payment_record(user_id: int, payment_id: str, tariff_name: str, 
                                amount: float, status: str, days: int) -> bool:
        """Создает или ОБНОВЛЯЕТ запись о платеже - НОВАЯ ЛОГИКА"""
        try:
            db = Database()
            with db.get_connection() as conn:
                cursor = conn.cursor()
                
                # 1. Проверяем активную подписку пользователя
                cursor.execute(
                    """SELECT valid_until FROM payments 
                    WHERE user_id = ? AND status = 'succeeded' 
                    ORDER BY created_at DESC LIMIT 1""",
                    (user_id,)
                )
                existing_sub = cursor.fetchone()
                
                # 2. НОВАЯ ЛОГИКА: подписка всегда начинается с даты оплаты
                payment_date = datetime.now()
                
                if existing_sub and existing_sub['valid_until']:
                    # Проверяем, действует ли текущая подписка
                    current_end = datetime.strptime(existing_sub['valid_until'], '%Y-%m-%d %H:%M:%S')
                    
                    if current_end > payment_date:
                        # Текущая подписка еще активна - ПРОДЛЕВАЕМ от даты окончания
                        new_valid_until = current_end + timedelta(days=days)
                        logger.info(f"Продление активной подписки: {current_end} + {days} дней = {new_valid_until}")
                    else:
                        # Текущая подписка истекла - НАЧИНАЕМ НОВУЮ с даты оплаты
                        new_valid_until = payment_date + timedelta(days=days)
                        logger.info(f"Новая подписка после истечения: {payment_date} + {days} дней = {new_valid_until}")
                else:
                    # Первая подписка пользователя
                    new_valid_until = payment_date + timedelta(days=days)
                    logger.info(f"Первая подписка: {payment_date} + {days} дней = {new_valid_until}")
                
                # 3. Проверяем, существует ли уже запись с таким payment_id
                cursor.execute(
                    "SELECT id FROM payments WHERE payment_id = ?", 
                    (payment_id,)
                )
                existing_record = cursor.fetchone()
                
                if existing_record:
                    # ОБНОВЛЯЕМ существующую запись
                    cursor.execute(
                        """UPDATE payments 
                        SET status = ?, tariff_name = ?, amount = ?, 
                            valid_until = ?, updated_at = datetime('now')
                        WHERE payment_id = ?""",
                        (status, tariff_name, amount, new_valid_until.strftime('%Y-%m-%d %H:%M:%S'), payment_id)
                    )
                    logger.info(f"Updated existing payment record: {payment_id}")
                else:
                    # СОЗДАЕМ новую запись
                    cursor.execute(
                        """INSERT INTO payments 
                        (user_id, payment_id, tariff_name, amount, status, 
                            created_at, updated_at, valid_until)
                        VALUES (?, ?, ?, ?, ?, datetime('now'), datetime('now'), ?)""",
                        (user_id, payment_id, tariff_name, amount, status, 
                        new_valid_until.strftime('%Y-%m-%d %H:%M:%S'))
                    )
                    logger.info(f"Created new payment record: {payment_id}")
                
                conn.commit()
                return True
                
        except Exception as e:
            logger.error(f"Error creating/updating payment record: {e}")
            return False


    @staticmethod
    async def update_payment_status(payment_id: str, status: str) -> bool:
        """Обновляет статус платежа"""
        try:
            db = Database()
            with db.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute(
                    """UPDATE payments 
                       SET status = ?, updated_at = datetime('now')
                       WHERE payment_id = ?""",
                    (status, payment_id)
                )
                
                conn.commit()
                return cursor.rowcount > 0
                
        except Exception as e:
            logger.error(f"Error updating payment status: {e}")
            return False

    @staticmethod
    async def check_subscription(user_id: int) -> bool:
        """Проверка активной подписки"""
        info = await PaymentManager.get_payment_info(user_id)
        return info and info['is_active']

    @staticmethod
    async def get_subscription_end_date(user_id: int) -> Optional[datetime]:
        """Возвращает дату окончания текущей подписки"""
        try:
            payment_info = await PaymentManager.get_payment_info(user_id)
            if payment_info and payment_info['is_active']:
                return datetime.strptime(payment_info['valid_until'], '%Y-%m-%d %H:%M:%S')
            return None
        except Exception as e:
            logger.error(f"Error getting subscription end date for user {user_id}: {e}")
            return None

    @staticmethod
    async def debug_check_payments(user_id: int):
        """Отладочная функция для проверки всех платежей пользователя"""
        try:
            db = Database()
            with db.get_connection() as conn:
                cursor = conn.cursor()
                
                query = "SELECT * FROM payments WHERE user_id = ? ORDER BY created_at DESC"
                cursor.execute(query, (user_id,))
                results = cursor.fetchall()
                
                logger.info(f"DEBUG: All payments for user {user_id}:")
                for row in results:
                    logger.info(f"  - ID: {row['id']}, Status: {row['status']}, "
                            f"Tariff: {row['tariff_name']}, Valid until: {row['valid_until']}")
                    
        except Exception as e:
            logger.error(f"Debug error: {e}")

    @staticmethod
    async def create_free_trial(user_id: int) -> bool:
        """Создает бесплатную пробную подписку на 7 дней"""
        try:
            db = Database()
            with db.get_connection() as conn:
                cursor = conn.cursor()
                
                # Проверяем, нет ли уже активной подписки
                cursor.execute(
                    """SELECT id FROM payments 
                    WHERE user_id = ? AND status = 'succeeded' 
                    AND valid_until > datetime('now')""",
                    (user_id,)
                )
                existing_active = cursor.fetchone()
                
                if existing_active:
                    logger.info(f"У пользователя {user_id} уже есть активная подписка, пробный период не создается")
                    return False
                
                # Проверяем, не использовал ли уже пользователь пробный период
                cursor.execute(
                    """SELECT id FROM payments 
                    WHERE user_id = ? AND tariff_name = 'Бесплатный пробный период'""",
                    (user_id,)
                )
                existing_trial = cursor.fetchone()
                
                if existing_trial:
                    logger.info(f"Пользователь {user_id} уже использовал пробный период")
                    return False
                
                # Создаем запись о бесплатной подписке
                valid_until = datetime.now() + timedelta(days=7)
                payment_id = f"free_trial_{user_id}_{int(time.time())}"
                
                cursor.execute(
                    """INSERT INTO payments 
                    (user_id, payment_id, tariff_name, amount, status, 
                    created_at, updated_at, valid_until)
                    VALUES (?, ?, ?, ?, ?, datetime('now'), datetime('now'), ?)""",
                    (user_id, payment_id, 'Бесплатный пробный период', 0, 'succeeded', 
                    valid_until.strftime('%Y-%m-%d %H:%M:%S'))
                )
                
                conn.commit()
                logger.info(f"Создан бесплатный пробный период для пользователя {user_id}")
                return True
                
        except Exception as e:
            logger.error(f"Ошибка создания бесплатной подписки: {e}")
            return False
    @staticmethod
    async def activate_planner_immediately(telegram_id: int):
        """Немедленная активация планера после оплаты"""
        try:
            from handlers.schedule.planner.timer.planner_manager import planner_manager
            
            # Проверяем подписку
            has_subscription = await PaymentManager.check_subscription(telegram_id)
            
            if has_subscription:
                # НЕМЕДЛЕННО включаем планер
                success = await planner_manager.update_tutor_planner_status(telegram_id, True)
                
                if success:
                    logger.info(f"Планер НЕМЕДЛЕННО активирован для {telegram_id} после оплаты")
                    return True
                else:
                    logger.error(f"Ошибка немедленной активации планера для {telegram_id}")
                    return False
            else:
                logger.warning(f"У {telegram_id} нет активной подписки для немедленной активации")
                return False
                
        except Exception as e:
            logger.error(f"Ошибка при немедленной активации планера: {e}")
            return False