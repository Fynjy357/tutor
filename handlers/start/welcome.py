from aiogram import types
from database import db
from handlers.start.handlers_parent import get_parent_welcome_keyboard
from handlers.schedule.schedule_utils import get_today_schedule_text
from handlers.start.keyboards_start import get_parent_welcome_keyboard, get_registration_keyboard, get_student_welcome_keyboard
from keyboards.main_menu import get_main_menu_keyboard
from handlers.start.config import STUDENT_WELCOME_TEXT, PARENT_WELCOME_TEXT, WELCOME_BACK_TEXT, REGISTRATION_TEXT

async def show_welcome_message(message: types.Message):
    """Показ приветственного сообщения"""
    # 1) Проверяем, является ли пользователь учеником
    existing_student = db.get_student_by_telegram_id(message.from_user.id)
    
    if existing_student:
        await show_student_welcome(message, existing_student)
        return
    
    # 2) Проверяем, является ли пользователь родителем
    existing_parent = db.get_parent_by_telegram_id(message.from_user.id)
    
    if existing_parent:
        await show_parent_welcome(message, existing_parent)
        return
    
    # 3) Проверяем, является ли пользователь репетитором
    existing_tutor = db.get_tutor_by_telegram_id(message.from_user.id)
    
    if existing_tutor:
        await show_welcome_back(message, existing_tutor)
        return
    
    # 4) Если ни одно из условий не выполнилось - показываем регистрацию
    await show_registration_message(message)

async def show_student_welcome(message: types.Message, student: dict):
    """Приветствие для ученика с информацией о репетиторе"""
    # Получаем информацию о репетиторе ученика
    print(student)
    tutor_id = student['tutor_id']
    tutor = db.get_tutor_by_id(tutor_id)
    
    if tutor:
        welcome_text = STUDENT_WELCOME_TEXT.format(
            student_name=student['full_name'],
            tutor_name=tutor[2],  # full_name (предположительно индекс 2)
            tutor_contact=tutor[3]  # phone (предположительно индекс 3)
        )
    else:
        welcome_text = "Добро пожаловать! Вы прикреплены к репетитору."

    keyboard = get_student_welcome_keyboard()
    
    await message.answer(
        welcome_text,
        reply_markup=keyboard,
        parse_mode="HTML"
    )

async def show_parent_welcome(message: types.Message, parent: dict):
    """Приветствие для родителя с информацией о репетиторе"""
    # Получаем информацию о репетиторе
    tutor_id = parent['tutor_id']
    tutor = db.get_tutor_by_id(tutor_id)
    
    if tutor:
        welcome_text = PARENT_WELCOME_TEXT.format(
            student_name=parent['full_name'],
            tutor_name=tutor[2],
            tutor_contact=tutor[3]
        )
    else:
        welcome_text = f"Добрый день! Ваш ребенок {parent['full_name']} прикреплен к репетитору."
    
        # Создаем инлайн клавиатуру
    keyboard = get_parent_welcome_keyboard()
    
    await message.answer(
        welcome_text,
        reply_markup=keyboard,
        parse_mode="HTML"
    )

async def show_welcome_back(message: types.Message, tutor: tuple):
    """Приветствие для зарегистрированного репетитора с расписанием на сегодня"""
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
    
    await message.answer(
        welcome_text,
        reply_markup=get_main_menu_keyboard(),
        parse_mode="HTML"
    )

async def show_registration_message(message: types.Message):
    """Приветствие для нового пользователя"""
    await message.answer(
        REGISTRATION_TEXT,
        reply_markup=get_registration_keyboard(),
        parse_mode="HTML"
    )