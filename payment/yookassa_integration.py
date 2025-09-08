import aiohttp
import base64
from config import YOOKASSA_SHOP_ID, YOOKASSA_SECRET_KEY
import logging

logger = logging.getLogger(__name__)

class YooKassaManager:
    def __init__(self):
        self.auth = base64.b64encode(f"{YOOKASSA_SHOP_ID}:{YOOKASSA_SECRET_KEY}".encode()).decode()
    
    async def create_payment(self, amount: int, user_id: int, tariff_name: str, tariff_days: int):
        """Создание платежа в ЮKassa"""
        try:
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Basic {self.auth}",
                "Idempotence-Key": f"{user_id}_{tariff_name}_{amount}"
            }
            
            payment_data = {
                "amount": {
                    "value": f"{amount:.2f}",
                    "currency": "RUB"
                },
                "confirmation": {
                    "type": "redirect",
                    "return_url": "https://t.me/your_bot"  # Замените на URL вашего бота
                },
                "capture": True,
                "description": f"Оплата подписки {tariff_name} для пользователя {user_id}",
                "metadata": {
                    "user_id": user_id,
                    "tariff": tariff_name,
                    "days": tariff_days
                }
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://api.yookassa.ru/v3/payments",
                    json=payment_data,
                    headers=headers
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get('confirmation', {}).get('confirmation_url')
                    
            return None
            
        except Exception as e:
            logger.error(f"Error creating YooKassa payment: {e}")
            return None