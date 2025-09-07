from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from handlers.groups.keyboards import *
from handlers.schedule.schedule_utils import get_today_schedule_text
from handlers.start.config import WELCOME_BACK_TEXT

router = Router()

# Экран 1 - Главное меню групп
@router.callback_query(F.data == "groups")
async def groups_main_menu(callback_query: CallbackQuery, state: FSMContext):
    """Главное меню управления группами"""
    await callback_query.answer()
    
    await callback_query.message.edit_text(
        "👨‍👩‍👧‍👦 <b>Управление группами</b>\n\nВыберите действие:",
        reply_markup=get_groups_main_menu_keyboard(),
        parse_mode="HTML"
    )
# Обработчики кнопок "Назад"
@router.callback_query(F.data == "back_to_groups_menu")
async def back_to_groups_menu(callback_query: CallbackQuery, state: FSMContext):
    """Возврат в главное меню групп"""
    await callback_query.answer()
    await state.clear()
    await groups_main_menu(callback_query, state)

@router.callback_query(F.data == "back_to_main_from_groups")
async def back_to_main_menu_from_groups(callback_query: CallbackQuery, state: FSMContext):
    """Возврат в главное меню"""
    await callback_query.answer()
    await state.clear()
    
    # Получаем данные преподавателя из базы
    from database import db
    tutor = db.get_tutor_by_telegram_id(callback_query.from_user.id)
    tutor_id = tutor[0]
    schedule_text = await get_today_schedule_text(tutor_id)
    
    if not tutor:
        await callback_query.message.answer("❌ Ошибка: преподаватель не найден")
        return
    
    # Отправляем новое сообщение с главным меню
    welcome_text = WELCOME_BACK_TEXT.format(tutor_name=tutor[2], schedule_text=schedule_text)  # предполагая, что имя в третьем элементе
    from keyboards.main_menu import get_main_menu_keyboard
    await callback_query.message.answer(
        welcome_text,
        reply_markup=get_main_menu_keyboard(),
        parse_mode="HTML"
    )
    
    # Удаляем предыдущее сообщение (опционально)
    try:
        await callback_query.message.delete()
    except:
        pass