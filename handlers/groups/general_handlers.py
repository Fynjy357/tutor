from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from handlers.groups.keyboards import *
from handlers.schedule.schedule_utils import get_today_schedule_text
from handlers.start.config import WELCOME_BACK_TEXT
from handlers.start.welcome import show_main_menu

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
    
     # Используем универсальную функцию для показа главного меню
    await show_main_menu(
        chat_id=callback_query.from_user.id,
        callback_query=callback_query
    )
    