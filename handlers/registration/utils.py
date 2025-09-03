from aiogram import types, Bot
from aiogram.fsm.context import FSMContext
from database import db
from handlers.registration.states import RegistrationStates
from handlers.registration.keyboards import get_confirmation_keyboard

async def show_confirmation(message: types.Message, state: FSMContext, bot: Bot):
    """Показ подтверждения данных"""
    data = await state.get_data()
    
    confirmation_text = f"""
<b>Проверьте ваши данные:</b>

📝 <b>ФИО:</b> {data.get('name', 'не указано')}
📞 <b>Телефон:</b> {data.get('phone', 'не указан')}
🎫 <b>Промокод:</b> {data.get('promo', 'не указан') if data.get('promo') != '0' else 'не указан'}

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

async def save_tutor_data(callback_query: types.CallbackQuery, user_data: dict):
    """Сохранение данных репетитора в БД"""
    try:
        tutor_id = db.add_tutor(
            telegram_id=callback_query.from_user.id,
            full_name=user_data['name'],
            phone=user_data['phone'],
            promo_code=user_data.get('promo', '0')
        )
        return tutor_id, True
    except Exception as e:
        return None, False

async def process_promo_code(promo_code: str):
    """Обработка промокода"""
    if not promo_code or promo_code == '0':
        return "не указан"
    
    promo_info = db.check_promo_code(promo_code)
    if promo_info:
        db.use_promo_code(promo_code)
        discount = promo_info[2] if promo_info[2] > 0 else promo_info[3]
        discount_type = "%" if promo_info[2] > 0 else "руб."
        return f"{promo_code} (скидка {discount}{discount_type})"
    else:
        return f"{promo_code} (недействителен)"