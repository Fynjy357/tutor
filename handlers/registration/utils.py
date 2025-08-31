from aiogram.exceptions import TelegramBadRequest
from aiogram.types import ReplyKeyboardRemove

from keyboards.confirmation import get_confirmation_keyboard
from database import db
import logging

logger = logging.getLogger(__name__)

async def show_confirmation(message, state, bot):
    user_data = await state.get_data()
    
    # Удаляем все сообщения процесса регистрации
    registration_messages = user_data.get('registration_messages', [])
    for msg_id in registration_messages:
        try:
            await bot.delete_message(chat_id=message.chat.id, message_id=msg_id)
        except TelegramBadRequest:
            pass
    
    # Формируем текст с промокодом
    promo_code = user_data.get('promo', '0')
    promo_text = f"Промокод: {promo_code}" if promo_code != "0" else "Промокод: не указан"
    
    # Проверяем валидность промокода, если он указан
    if promo_code != "0":
        promo_info = db.check_promo_code(promo_code)
        if promo_info:
            discount = promo_info[2] if promo_info[2] > 0 else promo_info[3]
            discount_type = "%" if promo_info[2] > 0 else "руб."
            promo_text = f"Промокод: {promo_code} (скидка {discount}{discount_type})"
        else:
            promo_text = f"Промокод: {promo_code} (недействителен)"
    
    # Отправляем сообщение с подтверждением данных и кнопками
    confirmation_message = await message.answer(
        f"Регистрация завершена!\n\n"
        f"ФИО: {user_data['name']}\n"
        f"Телефон: {user_data['phone']}\n"
        f"{promo_text}\n\n"
        f"Подтвердите правильность данных или измените их:",
        reply_markup=get_confirmation_keyboard()
    )
    
    # Сохраняем ID сообщения с подтверждением
    await state.update_data(registration_messages=[confirmation_message.message_id])