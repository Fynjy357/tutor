import aiohttp
import base64
import time
import uuid
from config import YOOKASSA_SHOP_ID, YOOKASSA_SECRET_KEY
import logging
import json

logger = logging.getLogger(__name__)

class YooKassaManager:
    def __init__(self):
        self.auth = base64.b64encode(f"{YOOKASSA_SHOP_ID}:{YOOKASSA_SECRET_KEY}".encode()).decode()
        logger.info(f"YooKassaManager initialized with Shop ID: {YOOKASSA_SHOP_ID}")
    
    def _generate_idempotence_key(self, user_id: int, tariff_name: str, amount: int):
        """Генерация уникального Idempotence-Key с временной меткой"""
        timestamp = int(time.time())
        unique_id = str(uuid.uuid4())[:8]  # Берем первые 8 символов UUID
        return f"{user_id}_{tariff_name}_{amount}_{timestamp}_{unique_id}"
    
    async def create_payment(self, amount: int, user_id: int, tariff_name: str, tariff_days: int):
        """Создание платежа в ЮKassa"""
        logger.info(f"Creating payment for user {user_id}, amount: {amount} RUB, tariff: {tariff_name} ({tariff_days} days)")
        
        try:
            # Генерируем уникальный ключ
            idempotence_key = self._generate_idempotence_key(user_id, tariff_name, amount)
            logger.debug(f"Generated Idempotence-Key: {idempotence_key}")
            
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Basic {self.auth}",
                "Idempotence-Key": idempotence_key
            }
            
            payment_data = {
                "amount": {
                    "value": f"{amount:.2f}",
                    "currency": "RUB"
                },
                "confirmation": {
                    "type": "redirect",
                    "return_url": "https://t.me/egeTOP100_bot"
                },
                "capture": True,
                "description": f"Оплата подписки {tariff_name} для пользователя {user_id}",
                "metadata": {
                    "user_id": user_id,
                    "tariff": tariff_name,
                    "days": tariff_days
                }
            }
            
            logger.debug(f"Request headers: {headers}")
            logger.debug(f"Payment data: {json.dumps(payment_data, ensure_ascii=False)}")
            
            async with aiohttp.ClientSession() as session:
                logger.info("Sending request to YooKassa API...")
                
                async with session.post(
                    "https://api.yookassa.ru/v3/payments",
                    json=payment_data,
                    headers=headers
                ) as response:
                    
                    response_text = await response.text()
                    logger.info(f"YooKassa API response status: {response.status}")
                    
                    if response.status == 200:
                        data = await response.json()
                        confirmation_url = data.get('confirmation', {}).get('confirmation_url')
                        payment_id = data.get('id')
                        
                        if confirmation_url:
                            logger.info(f"Payment created successfully! Payment ID: {payment_id}")
                            logger.info(f"Confirmation URL: {confirmation_url}")
                            return confirmation_url
                        else:
                            logger.warning("No confirmation URL in response")
                            return None
                    else:
                        logger.error(f"YooKassa API error: Status {response.status}")
                        logger.error(f"Error response: {response_text}")
                        
                        # Логируем дополнительные детали для отладки
                        try:
                            error_data = json.loads(response_text)
                            if 'code' in error_data:
                                logger.error(f"Error code: {error_data['code']}")
                            if 'description' in error_data:
                                logger.error(f"Error description: {error_data['description']}")
                        except:
                            pass
                        
                        return None
            
        except aiohttp.ClientError as e:
            logger.error(f"HTTP client error: {e}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error creating YooKassa payment: {e}", exc_info=True)
            return None