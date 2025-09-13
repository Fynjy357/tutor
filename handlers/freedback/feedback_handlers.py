# feedback_handlers.py
from aiogram import types, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.exceptions import TelegramBadRequest
import os
from database import db

# Импортируем необходимые функции
from handlers.schedule.schedule_utils import get_today_schedule_text
from handlers.start.config import WELCOME_BACK_TEXT
from keyboards.main_menu import get_main_menu_keyboard


router = Router()

class FeedbackStates(StatesGroup):
    waiting_for_feedback = State()

def get_cancel_inline_keyboard():
    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(
        text="❌ Отмена",
        callback_data="cancel_feedback"
    ))
    return builder.as_markup()

@router.callback_query(F.data == "contact_developers")
async def contact_developers_handler(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.message.answer(
        "📞 **Связь с разработчиками**\n\n"
        "Оставьте ваше обращение, команда разработчиков учтет его при дальнейшей работе.\n\n"
        "Если у вас возникла проблема - мы свяжемся с вами в ближайшее время.\n\n"
        "✍️ Напишите ваше сообщение:",
        parse_mode='Markdown',
        reply_markup=get_cancel_inline_keyboard()
    )
    await state.set_state(FeedbackStates.waiting_for_feedback)
    await callback_query.answer()

@router.callback_query(F.data == "cancel_feedback", FeedbackStates.waiting_for_feedback)
async def cancel_feedback_callback(callback_query: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback_query.answer()
    
    # Получаем данные репетитора
    tutor = db.get_tutor_by_telegram_id(callback_query.from_user.id)
    tutor_name = tutor[2] if tutor else "Пользователь"
    tutor_id = tutor[0]  # ID репетитора
    
    # Получаем расписание на сегодня
    schedule_text = await get_today_schedule_text(tutor_id)
    # Проверяем активную подписку
    has_active_subscription = db.check_tutor_subscription(tutor_id)
    subscription_icon = "💎 " if has_active_subscription else ""

    # Формируем полный текст приветствия
    formatted_text = WELCOME_BACK_TEXT.format(
        tutor_name=tutor_name,
        schedule_text=schedule_text
    )
    welcome_text = f"{subscription_icon}{formatted_text}"
    
    try:
        await callback_query.message.edit_text(
            welcome_text,
            reply_markup=get_main_menu_keyboard(),
            parse_mode="HTML"
        )
    except TelegramBadRequest:
        await callback_query.message.answer(
            welcome_text,
            reply_markup=get_main_menu_keyboard(),
            parse_mode="HTML"
        )

@router.message(FeedbackStates.waiting_for_feedback)
async def process_feedback_message(message: types.Message, state: FSMContext, bot):
    user_id = message.from_user.id
    user_name = message.from_user.full_name
    feedback_text = message.text
    
    try:
        # Сохраняем обращение в базу данных
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO feedback_messages 
                   (user_id, user_name, message) 
                   VALUES (?, ?, ?)""",
                (user_id, user_name, feedback_text)
            )
            conn.commit()
        
        # Получаем телефон пользователя из базы данных
        phone = None
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT phone FROM tutors WHERE telegram_id = ?",
                (user_id,)
            )
            result = cursor.fetchone()
            if result:
                phone = result[0]
        
        # Отправляем уведомление супер-админу
        super_admin_id = int(os.getenv('SUPER_ADMIN_ID'))
        
        admin_message = (
            f"📨 **Новое обращение от пользователя**\n\n"
            f"👤 Пользователь: {user_name} (ID: {user_id})\n"
        )
        
        # Добавляем телефон, если он есть
        if phone:
            admin_message += f"📞 Телефон: {phone}\n\n"
        else:
            admin_message += f"📞 Телефон: не указан\n\n"
        
        admin_message += (
            f"📝 Сообщение:\n{feedback_text}\n\n"
            f"🕒 Время: {message.date.strftime('%d.%m.%Y %H:%M')}"
        )
        
        await bot.send_message(
            chat_id=super_admin_id,
            text=admin_message,
            parse_mode='Markdown'
        )
        
        # Получаем данные репетитора для возврата в главное меню
        tutor = db.get_tutor_by_telegram_id(user_id)
        tutor_name = tutor[2] if tutor else "Пользователь"
        tutor_id = tutor[0] if tutor else None
        
        # Получаем расписание на сегодня
        schedule_text = await get_today_schedule_text(tutor_id) if tutor_id else "Расписание недоступно"
        
        # Проверяем активную подписку
        has_active_subscription = db.check_tutor_subscription(tutor_id)
        subscription_icon = "💎 " if has_active_subscription else ""

        # Формируем полный текст приветствия
        formatted_text = WELCOME_BACK_TEXT.format(
            tutor_name=tutor_name,
            schedule_text=schedule_text
        )
        welcome_text = f"{subscription_icon}{formatted_text}"
        
        # Подтверждаем пользователю и возвращаем в главное меню
        await message.answer(
            "✅ **Ваше обращение отправлено!**\n\n"
            "Спасибо за ваше сообщение. Мы рассмотрим его в ближайшее время.\n\n"
            "Если у вас срочный вопрос - мы свяжемся с вами.",
            parse_mode='Markdown'
        )
        
        await message.answer(
            welcome_text,
            reply_markup=get_main_menu_keyboard(),
            parse_mode="HTML"
        )
        
    except Exception as e:
        await message.answer(
            "❌ Произошла ошибка при отправке обращения. Попробуйте позже."
        )
        print(f"Error saving feedback: {e}")
    
    await state.clear()

@router.message(F.text.lower() == "отмена", FeedbackStates.waiting_for_feedback)
async def cancel_feedback_text(message: types.Message, state: FSMContext):
    await state.clear()
    
    # Получаем данные репетитора
    tutor = db.get_tutor_by_telegram_id(message.from_user.id)
    tutor_name = tutor[2] if tutor else "Пользователь"
    tutor_id = tutor[0] if tutor else None
    
    # Получаем расписание на сегодня
    schedule_text = await get_today_schedule_text(tutor_id) if tutor_id else "Расписание недоступно"

    # Проверяем активную подписку
    has_active_subscription = db.check_tutor_subscription(tutor_id)
    subscription_icon = "💎 " if has_active_subscription else ""
    
    # Формируем полный текст приветствия
    formatted_text = WELCOME_BACK_TEXT.format(
        tutor_name=tutor_name,
        schedule_text=schedule_text
    )
    welcome_text = f"{subscription_icon}{formatted_text}"
    
    await message.answer(
        welcome_text,
        reply_markup=get_main_menu_keyboard(),
        parse_mode="HTML"
    )