import re
from typing import Optional
from aiogram import types, Bot
from aiogram.fsm.context import FSMContext
from database import db
from handlers.registration.states import RegistrationStates
from handlers.registration.keyboards import get_confirmation_keyboard
import secrets
import string
import logging

from keyboards.keyboard_phone import get_phone_keyboard

logger = logging.getLogger(__name__)

def generate_referral_code(length=8):
    """Генерация уникального реферального кода"""
    alphabet = string.ascii_uppercase + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def generate_referral_link(bot_username: str, referral_code: str) -> str:
    """Генерация реферальной ссылки"""
    return f"https://t.me/{bot_username}?start=ref_{referral_code}"

async def show_confirmation(message: types.Message, state: FSMContext, bot: Bot):
    """Показ подтверждения данных"""
    data = await state.get_data()
    
    confirmation_text = f"""
<b>Проверьте ваши данные:</b>

📝 <b>ФИО:</b> {data.get('name', 'не указано')}
📞 <b>Телефон:</b> {data.get('phone', 'не указан')}

Всё верно?
"""
    
    # Удаляем предыдущие сообщения регистрации
    registration_messages = data.get('registration_messages', [])
    for msg_id in registration_messages:
        try:
            await bot.delete_message(chat_id=message.chat.id, message_id=msg_id)
        except:
            pass
    
    # Отправляем сообщение с подтверждением
    confirm_message = await message.answer(
        confirmation_text,
        reply_markup=get_confirmation_keyboard(),
        parse_mode="HTML"
    )
    
    # Сохраняем ID нового сообщения
    await state.update_data(registration_messages=[confirm_message.message_id])
    await state.set_state(RegistrationStates.confirmation)

async def save_tutor_data(callback_query: types.CallbackQuery, user_data: dict, bot: Bot):
    """Сохранение данных репетитора в БД с генерацией реферальной ссылки"""
    try:
        # Генерируем уникальный реферальный код
        referral_code = generate_referral_code()
        
        # Получаем username бота для создания ссылки
        bot_info = await bot.get_me()
        bot_username = bot_info.username
        
        # Генерируем полную реферальную ссылку
        referral_link = generate_referral_link(bot_username, referral_code)
        
        tutor_id = db.add_tutor(
            telegram_id=callback_query.from_user.id,
            full_name=user_data['name'],
            phone=user_data['phone'],
            promo_code=referral_link
        )
        
        # АКТИВАЦИЯ РЕФЕРАЛА (просто меняем статус)
        user_id = callback_query.from_user.id
        db.activate_referral(user_id, tutor_id)
        
        return tutor_id, True
        
    except Exception as e:
        logger.error(f"Ошибка сохранения данных репетитора: {e}")
        return None, False

def validate_phone_number(phone: Optional[str]) -> bool:
    """Проверяет валидность российского номера телефона"""
    if phone is None:
        logger.warning("Передан None в валидацию номера")
        return False
    
    if not isinstance(phone, str):
        logger.warning(f"Передан не строковый тип: {type(phone)}")
        return False
    
    if not phone.strip():
        logger.warning("Передана пустая строка")
        return False
    
    logger.info(f"Валидация номера: '{phone}'")
    
    # Убираем все нецифровые символы
    digits = re.sub(r'\D', '', phone)
    
    if not digits:
        logger.warning(f"Номер не содержит цифр: {phone}")
        return False
    
    logger.info(f"Цифры номера: {digits} (длина: {len(digits)})")
    
    # Проверяем длину (10 или 11 цифр для российских номеров)
    if len(digits) not in [10, 11]:
        logger.warning(f"Неправильная длина номера: {digits} (длина: {len(digits)})")
        return False
    
    # Более гибкая проверка формата российского номера
    if len(digits) == 11:
        # Для 11-значных номеров первая цифра должна быть 7 или 8
        if not digits.startswith(('7', '8')):
            logger.warning(f"Неправильный формат 11-значного номера: {digits}")
            return False
    else:
        # Для 10-значных номеров первая цифра должна быть 9 (мобильные) или 4/8 (городские)
        if not digits.startswith(('9', '4', '8')):
            logger.warning(f"Неправильный формат 10-значного номера: {digits}")
            return False
    
    logger.info(f"Номер прошел валидацию: {digits}")
    return True

async def handle_invalid_phone(message: types.Message, state: FSMContext):
    """Обработка невалидного номера телефона"""
    error_text = """
❌ <b>Неверный формат номера телефона!</b>

Номер должен быть в формате: <code>+79111234567</code>

Примеры правильных форматов:
• +79183567075
• +79261234567

Пожалуйста, введите номер еще раз:
"""
    
    await message.answer(
        error_text,
        parse_mode="HTML",
        reply_markup=get_phone_keyboard()
    )