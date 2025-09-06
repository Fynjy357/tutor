from aiogram import types
from database import db
from handlers.schedule.schedule_utils import get_today_schedule_text
from handlers.start.keyboards_start import get_registration_keyboard
from keyboards.main_menu import get_main_menu_keyboard
from handlers.start.config import STUDENT_WELCOME_TEXT, WELCOME_BACK_TEXT, REGISTRATION_TEXT

async def show_welcome_message(message: types.Message):
    """Показ приветственного сообщения"""
    # Сначала проверяем, является ли пользователь учеником
    existing_student = db.get_student_by_telegram_id(message.from_user.id)
    
    if existing_student:
        await show_student_welcome(message, existing_student)
        return
    
    # Если не ученик, проверяем репетитора
    existing_tutor = db.get_tutor_by_telegram_id(message.from_user.id)
    
    if existing_tutor:
        await show_welcome_back(message, existing_tutor)
    else:
        await show_registration_message(message)


async def show_student_welcome(message: types.Message, student: dict):
    """Приветствие для ученика с информацией о репетиторе"""
    # Получаем информацию о репетиторе ученика
    tutor_id = student['tutor_id']
    tutor = db.get_tutor_by_id(tutor_id)
    
    if tutor:
        # tutor - это кортеж, нужно знать структуру таблицы tutors
        # Предполагаемая структура: (id, telegram_id, full_name, phone, ...)
        # Проверьте реальную структуру вашей таблицы!
        welcome_text = STUDENT_WELCOME_TEXT.format(
            student_name=student['full_name'],
            tutor_name=tutor[2],  # full_name (предположительно индекс 2)
            tutor_contact=tutor[3]  # phone (предположительно индекс 3)
        )
    else:
        welcome_text = "Добро пожаловать! Вы прикреплены к репетитору."
    
    await message.answer(
        welcome_text,
        parse_mode="HTML"
    )

# async def show_welcome_back(message: types.Message, tutor: tuple):
#     """Приветствие для зарегистрированного репетитора"""
#     welcome_text = WELCOME_BACK_TEXT.format(tutor_name=tutor[2])
    
#     await message.answer(
#         welcome_text,
#         reply_markup=get_main_menu_keyboard(),
#         parse_mode="HTML"
#     )

async def show_registration_message(message: types.Message):
    """Приветствие для нового пользователя"""
    await message.answer(
        REGISTRATION_TEXT,
        reply_markup=get_registration_keyboard(),
        parse_mode="HTML"
    )

async def show_welcome_back(message: types.Message, tutor: tuple):
    """Приветствие для зарегистрированного репетитора с расписанием на сегодня"""
    tutor_name = tutor[2] if tutor else "Пользователь"
    tutor_id = tutor[0]  # ID репетитора
    
    # Получаем расписание на сегодня
    schedule_text = await get_today_schedule_text(tutor_id)
    
    # Формируем полный текст приветствия
    welcome_text = WELCOME_BACK_TEXT.format(
        tutor_name=tutor_name,
        schedule_text=schedule_text
    )
    
    await message.answer(
        welcome_text,
        reply_markup=get_main_menu_keyboard(),
        parse_mode="HTML"
    )