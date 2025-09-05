from datetime import datetime
import logging
from aiogram import types

logger = logging.getLogger(__name__)

async def detect_user_timezone(message: types.Message) -> str:
    """Определение часового пояса пользователя"""
    try:
        # Способ 1: Если пользователь отправил свое местоположение
        if hasattr(message, 'location') and message.location:
            latitude = message.location.latitude
            longitude = message.location.longitude
            return await get_timezone_from_coordinates(latitude, longitude)
        
        # Способ 2: Если есть геолокация в сообщении
        if message.content_type == 'location':
            latitude = message.location.latitude
            longitude = message.location.longitude
            return await get_timezone_from_coordinates(latitude, longitude)
        
        # Способ 3: Используем информацию из профиля Telegram
        # (если в будущем добавится возможность получать часовой пояс)
        
    except Exception as e:
        logger.error(f"Ошибка определения часового пояса: {e}")
    
    # Способ 4: Используем серверное время или дефолтный пояс
    return get_default_timezone()

async def get_timezone_from_coordinates(lat: float, lon: float) -> str:
    """Получение часового пояса по координатам"""
    try:
        # Простая логика для основных российских городов
        if 55.0 <= lat <= 56.0 and 37.0 <= lon <= 38.0:
            return 'Europe/Moscow'
        elif 59.0 <= lat <= 60.0 and 30.0 <= lon <= 31.0:
            return 'Europe/Moscow'  # СПб в том же поясе
        elif 43.0 <= lat <= 44.0 and 131.0 <= lon <= 132.0:
            return 'Asia/Vladivostok'
        elif 56.0 <= lat <= 57.0 and 92.0 <= lon <= 93.0:
            return 'Asia/Krasnoyarsk'
        elif 54.0 <= lat <= 55.0 and 82.0 <= lon <= 83.0:
            return 'Asia/Novosibirsk'
        elif 55.0 <= lat <= 56.0 and 49.0 <= lon <= 50.0:
            return 'Europe/Moscow'  # Казань
        else:
            # Для других мест используем смещение UTC
            utc_offset = datetime.now().astimezone().utcoffset()
            if utc_offset:
                hours = utc_offset.total_seconds() / 3600
                if hours == 3:
                    return 'Europe/Moscow'
                elif hours == 5:
                    return 'Asia/Yekaterinburg'
                elif hours == 7:
                    return 'Asia/Krasnoyarsk'
                elif hours == 8:
                    return 'Asia/Irkutsk'
                elif hours == 9:
                    return 'Asia/Yakutsk'
                elif hours == 10:
                    return 'Asia/Vladivostok'
                elif hours == 11:
                    return 'Asia/Magadan'
                elif hours == 12:
                    return 'Asia/Kamchatka'
            
    except Exception as e:
        logger.error(f"Ошибка определения по координатам: {e}")
    
    return get_default_timezone()

def get_default_timezone() -> str:
    """Возвращает дефолтный часовой пояс"""
    return 'Europe/Moscow'