from aiogram import Router, types, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest
import logging

from .states import RegistrationStates
from .utils import show_confirmation
from keyboards.registration import get_cancel_keyboard, get_phone_keyboard, get_promo_keyboard, get_registration_keyboard
from database import db

router = Router()
logger = logging.getLogger(__name__)

@router.callback_query(F.data == "start_registration")
async def start_registration(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.answer()
    
    # Проверяем, не зарегистрирован ли пользователь уже
    existing_tutor = db.get_tutor_by_telegram_id(callback_query.from_user.id)
    if existing_tutor:
        await callback_query.message.answer(
            "Вы уже зарегистрированы в системе!\n\n"
            f"ФИО: {existing_tutor[2]}\n"
            f"Телефон: {existing_tutor[3]}\n"
            f"Промокод: {existing_tutor[4] if existing_tutor[4] != '0' else 'не указан'}"
        )
        return
    
    try:
        # Удаляем предыдущее сообщение с кнопками
        await callback_query.message.delete()
    except TelegramBadRequest:
        # Если сообщение уже удалено, игнорируем ошибку
        pass
    
    # Отправляем новое сообщение с запросом ФИО
    message = await callback_query.message.answer(
        "Начинаем процесс регистрации...\n\nПожалуйста, введите ваше ФИО:",
        reply_markup=get_cancel_keyboard()
    )
    
    # Сохраняем ID сообщения в состоянии
    await state.set_state(RegistrationStates.waiting_for_name)
    await state.update_data(registration_messages=[message.message_id])

@router.callback_query(RegistrationStates.waiting_for_promo, F.data == "skip_promo")
async def skip_promo(callback_query: types.CallbackQuery, state: FSMContext, bot: Bot):
    await callback_query.answer()
    
    # Сохраняем ID сообщения с промокодом
    data = await state.get_data()
    registration_messages = data.get('registration_messages', [])
    registration_messages.append(callback_query.message.message_id)
    
    # Устанавливаем промокод как "0"
    await state.update_data(promo="0", registration_messages=registration_messages)
    await show_confirmation(callback_query.message, state, bot)

@router.callback_query(RegistrationStates.confirmation, F.data == "confirm_data")
async def confirm_data(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.answer()
    user_data = await state.get_data()
    
    # Сохраняем данные в базу
    try:
        tutor_id = db.add_tutor(
            telegram_id=callback_query.from_user.id,
            full_name=user_data['name'],
            phone=user_data['phone'],
            promo_code=user_data.get('promo', '0')
        )
        
        # Проверяем и используем промокод, если он валидный
        promo_code = user_data.get('promo')
        if promo_code and promo_code != '0':
            promo_info = db.check_promo_code(promo_code)
            if promo_info:
                db.use_promo_code(promo_code)
                discount = promo_info[2] if promo_info[2] > 0 else promo_info[3]
                discount_type = "%" if promo_info[2] > 0 else "руб."
                promo_text = f"Промокод: {promo_code} (скидка {discount}{discount_type})"
            else:
                promo_text = f"Промокод: {promo_code} (недействителен)"
        else:
            promo_text = "Промокод: не указан"
            
        # Формируем финальное сообщение
        await callback_query.message.edit_text(
            f"Данные подтверждены!\n\n"
            f"ФИО: {user_data['name']}\n"
            f"Телефон: {user_data['phone']}\n"
            f"{promo_text}\n\n"
            f"Теперь вы можете пользоваться всеми функциями бота."
        )
        
    except Exception as e:
        logger.error(f"Ошибка при сохранении данных: {e}")
        await callback_query.message.edit_text(
            "Произошла ошибка при сохранении данных. Пожалуйста, попробуйте позже."
        )
    
    await state.clear()

@router.callback_query(RegistrationStates.confirmation, F.data == "change_name")
async def change_name(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.answer()
    
    # Сохраняем ID сообщения с подтверждением для последующего удаления
    data = await state.get_data()
    registration_messages = data.get('registration_messages', [])
    registration_messages.append(callback_query.message.message_id)
    
    # Отправляем сообщение с запросом нового ФИО
    name_message = await callback_query.message.answer(
        "Введите новое ФИО:",
        reply_markup=get_cancel_keyboard()
    )
    
    # Добавляем ID нового сообщения в список
    registration_messages.append(name_message.message_id)
    await state.update_data(registration_messages=registration_messages)
    await state.set_state(RegistrationStates.editing_name)

@router.callback_query(RegistrationStates.confirmation, F.data == "change_phone")
async def change_phone(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.answer()
    
    # Сохраняем ID сообщения с подтверждением для последующего удаления
    data = await state.get_data()
    registration_messages = data.get('registration_messages', [])
    registration_messages.append(callback_query.message.message_id)
    
    # Отправляем сообщение с запросом нового телефона
    phone_message = await callback_query.message.answer(
        "Введите новый телефон. Вы можете использовать кнопку ниже для быстрой отправки:",
        reply_markup=get_phone_keyboard()
    )
    
    # Добавляем ID нового сообщения в список
    registration_messages.append(phone_message.message_id)
    await state.update_data(registration_messages=registration_messages)
    await state.set_state(RegistrationStates.editing_phone)

@router.callback_query(F.data == "cancel_registration")
async def cancel_registration(callback_query: types.CallbackQuery, state: FSMContext, bot: Bot):
    # Получаем данные из состояния
    data = await state.get_data()
    registration_messages = data.get('registration_messages', [])
    
    # Удаляем все сообщения процесса регистрации
    for msg_id in registration_messages:
        try:
            await bot.delete_message(chat_id=callback_query.message.chat.id, message_id=msg_id)
        except TelegramBadRequest:
            # Если сообщение уже удалено, игнорируем ошибку
            pass
    
    # Очищаем состояние
    await state.clear()
    await callback_query.answer()
    
    welcome_text = """
<b>Ежедневник репетитора</b>

Привет! Этот бот для репетиторов

🔲 Зарегистрироваться в боте
✅ Написать сообщение...
    """
    
    # Отправляем главное меню
    await callback_query.message.answer(
        welcome_text,
        reply_markup=get_registration_keyboard(),
        parse_mode="HTML"
    )