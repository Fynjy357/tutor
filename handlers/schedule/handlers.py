# handlers/schedule/handlers.py
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest
import logging
from datetime import datetime
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from handlers.schedule.keyboards_schedule import get_schedule_keyboard
from handlers.start.config import WELCOME_BACK_TEXT
from keyboards.main_menu import get_main_menu_keyboard
from database import db
from handlers.schedule.add_lesson.handlers_add_lesson import router as add_new_lesson
from handlers.schedule.schedule_utils import get_today_schedule_text, get_upcoming_lessons_text


router = Router()
router.include_router(add_new_lesson)
logger = logging.getLogger(__name__)


@router.callback_query(F.data == "schedule")
async def show_schedule(callback_query: types.CallbackQuery, state: FSMContext):
    """Показ расписания занятий на неделю"""
    await callback_query.answer()
    
    # Очищаем состояние если было активным
    current_state = await state.get_state()
    if current_state:
        await state.clear()
    
    # Получаем ID репетитора
    tutor_id = db.get_tutor_id_by_telegram_id(callback_query.from_user.id)
    if not tutor_id:
        await callback_query.message.edit_text("❌ Ошибка: не найден ID репетитора.")
        return
    
    # Получаем расписание на ближайшую неделю
    schedule_text = await get_upcoming_lessons_text(tutor_id)
    
    try:
        await callback_query.message.edit_text(
            schedule_text,
            reply_markup=get_schedule_keyboard(),
            parse_mode="HTML"
        )
    except TelegramBadRequest:
        await callback_query.message.answer(
            schedule_text,
            reply_markup=get_schedule_keyboard(),
            parse_mode="HTML"
        )


# @router.callback_query(F.data == "back_from_schedule")
# async def back_from_schedule(callback_query: types.CallbackQuery, state: FSMContext):
#     """Возврат в главное меню из расписания"""
#     await callback_query.answer()
    
#     # Получаем данные репетитора для приветствия
#     tutor = db.get_tutor_by_telegram_id(callback_query.from_user.id)
#     tutor_name = tutor[2] if tutor else "Пользователь"
    
#     welcome_text = WELCOME_BACK_TEXT.format(tutor_name=tutor_name)
    
#     try:
#         await callback_query.message.edit_text(
#             welcome_text,
#             reply_markup=get_main_menu_keyboard(),
#             parse_mode="HTML"
#         )
#     except TelegramBadRequest:
#         await callback_query.message.answer(
#             welcome_text,
#             reply_markup=get_main_menu_keyboard(),
#             parse_mode="HTML"
#         )
@router.callback_query(F.data == "back_from_schedule")
async def back_from_schedule(callback_query: types.CallbackQuery, state: FSMContext):
    """Возврат в главное меню из расписания"""
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