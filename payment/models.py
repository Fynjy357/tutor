from datetime import datetime, timedelta
from database import db
import logging

logger = logging.getLogger(__name__)

class PaymentManager:
    @staticmethod
    async def get_payment_info(user_id: int):
        """Получение информации об оплате пользователя"""
        try:
            with db.get_connection() as conn:
                conn.row_factory = db.get_connection().row_factory
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT valid_until, tariff, is_active FROM user_subscriptions WHERE user_id = ?",
                    (user_id,)
                )
                result = cursor.fetchone()
                
                if result:
                    valid_until = datetime.strptime(result['valid_until'], '%Y-%m-%d')
                    return {
                        "valid_until": result['valid_until'],
                        "tariff": result['tariff'],
                        "is_active": result['is_active'] and datetime.now() < valid_until
                    }
                
            return None
            
        except Exception as e:
            logger.error(f"Error getting payment info: {e}")
            return None

    @staticmethod
    async def update_subscription(user_id: int, days: int, tariff: str):
        """Обновление подписки пользователя"""
        try:
            valid_until = (datetime.now() + timedelta(days=days)).strftime('%Y-%m-%d')
            
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """INSERT OR REPLACE INTO user_subscriptions 
                       (user_id, valid_until, tariff, is_active) 
                       VALUES (?, ?, ?, ?)""",
                    (user_id, valid_until, tariff, True)
                )
                conn.commit()
                
            return True
            
        except Exception as e:
            logger.error(f"Error updating subscription: {e}")
            return False

    @staticmethod
    async def check_subscription(user_id: int):
        """Проверка активной подписки"""
        info = await PaymentManager.get_payment_info(user_id)
        return info and info['is_active']