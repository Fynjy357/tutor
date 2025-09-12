import asyncio
import aiohttp
import base64
import time
import uuid
from config import YOOKASSA_SHOP_ID, YOOKASSA_SECRET_KEY
import logging
import json
from typing import Optional, Dict
from database import db

logger = logging.getLogger(__name__)

class YooKassaManager:
    def __init__(self):
        logger.info(f"Инициализация YooKassaManager: ShopID={YOOKASSA_SHOP_ID}")
        try:
            auth_string = f"{YOOKASSA_SHOP_ID}:{YOOKASSA_SECRET_KEY}"
            logger.info(f"Auth string: {auth_string}")
            self.auth = base64.b64encode(auth_string.encode()).decode()
            logger.info(f"Base64 auth: {self.auth}")
        except Exception as e:
            logger.error(f"Ошибка инициализации авторизации: {e}")
            raise
    
    def _generate_idempotence_key(self, user_id: int, tariff_name: str, amount: int):
        """Генерация уникального Idempotence-Key"""
        timestamp = int(time.time())
        unique_id = str(uuid.uuid4())[:8]
        key = f"{user_id}_{tariff_name}_{amount}_{timestamp}_{unique_id}"
        logger.info(f"Сгенерирован Idempotence-Key: {key}")
        return key
    
    async def create_payment(self, amount: int, user_id: int, tariff_name: str, tariff_days: int) -> Optional[str]:
        """Создание платежа в ЮKassa"""
        logger.info(f"Начало создания платежа: user_id={user_id}, amount={amount}, tariff={tariff_name}")
        
        try:
            idempotence_key = self._generate_idempotence_key(user_id, tariff_name, amount)
            
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
                "description": f"Оплата доступа к полному коду функционала в чат-боте @TutorPlanetBot на {tariff_name} для пользователя {user_id}",
                "metadata": {
                    "user_id": user_id,
                    "tariff": tariff_name,
                    "days": tariff_days
                }
            }
            
            logger.info(f"Данные для платежа: {json.dumps(payment_data, indent=2, ensure_ascii=False)}")
            logger.info(f"Заголовки: {headers}")
            
            async with aiohttp.ClientSession() as session:
                logger.info("Отправка запроса к API ЮKassa...")
                
                try:
                    async with session.post(
                        "https://api.yookassa.ru/v3/payments",
                        json=payment_data,
                        headers=headers,
                        timeout=aiohttp.ClientTimeout(total=30)
                    ) as response:
                        
                        logger.info(f"Статус ответа: {response.status}")
                        logger.info(f"Заголовки ответа: {dict(response.headers)}")
                        
                        response_text = await response.text()
                        logger.info(f"Текст ответа: {response_text}")
                        
                        if response.status == 200:
                            try:
                                data = await response.json()
                                logger.info(f"JSON ответ: {json.dumps(data, indent=2, ensure_ascii=False)}")
                                
                                confirmation_url = data.get('confirmation', {}).get('confirmation_url')
                                payment_id = data.get('id')
                                
                                logger.info(f"Confirmation URL: {confirmation_url}")
                                logger.info(f"Payment ID: {payment_id}")
                                
                                if confirmation_url:
                                    # Сохраняем payment_id в БД
                                    logger.info("Сохранение payment_id в базу данных...")
                                    save_result = db.save_payment_id(user_id, payment_id, tariff_name, amount)
                                    logger.info(f"Результат сохранения: {save_result}")
                                    return confirmation_url
                                else:
                                    logger.error("Confirmation URL не найден в ответе")
                                    
                            except json.JSONDecodeError as e:
                                logger.error(f"Ошибка парсинга JSON: {e}, текст ответа: {response_text}")
                                return None
                        
                        else:
                            logger.error(f"Ошибка API ЮKassa: Статус {response.status}")
                            logger.error(f"Тело ошибки: {response_text}")
                            return None
                            
                except aiohttp.ClientError as e:
                    logger.error(f"Ошибка HTTP клиента: {e}")
                    return None
                except asyncio.TimeoutError:
                    logger.error("Таймаут запроса к API ЮKassa")
                    return None
            
        except aiohttp.ClientError as e:
            logger.error(f"HTTP client error: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error in create_payment: {e}", exc_info=True)
            return None

    async def get_last_payment(self, user_id: int) -> Optional[Dict]:
        """Получить информацию о последнем платеже пользователя"""
        logger.info(f"Получение информации о последнем платеже для user_id={user_id}")
        
        try:
            payment_id = db.get_last_payment_id(user_id)
            logger.info(f"Найден payment_id: {payment_id}")
            
            if not payment_id:
                logger.info("Платежи не найдены")
                return None
            
            headers = {
                "Authorization": f"Basic {self.auth}",
                "Content-Type": "application/json"
            }
            
            async with aiohttp.ClientSession() as session:
                logger.info(f"Запрос информации о платеже {payment_id}")
                
                async with session.get(
                    f"https://api.yookassa.ru/v3/payments/{payment_id}",
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    
                    logger.info(f"Статус ответа: {response.status}")
                    response_text = await response.text()
                    logger.info(f"Текст ответа: {response_text}")
                    
                    if response.status == 200:
                        try:
                            payment_data = await response.json()
                            logger.info(f"Данные платежа: {json.dumps(payment_data, indent=2, ensure_ascii=False)}")
                            
                            return {
                                'id': payment_data.get('id'),
                                'status': payment_data.get('status'),
                                'amount': payment_data.get('amount', {}).get('value'),
                                'currency': payment_data.get('amount', {}).get('currency'),
                                'created_at': payment_data.get('created_at'),
                                'metadata': payment_data.get('metadata', {})
                            }
                            
                        except json.JSONDecodeError as e:
                            logger.error(f"Ошибка парсинга JSON: {e}")
                            return None
                    else:
                        logger.error(f"Ошибка получения информации о платеже: {response.status}")
                        return None
            
        except Exception as e:
            logger.error(f"Error getting payment: {e}", exc_info=True)
            return None