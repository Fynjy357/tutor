# handlers/schedule/planner/handlers/main_menu.py
from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext

from ...planner.keyboards_planner import get_planner_keyboard
from handlers.schedule.keyboards_schedule import get_schedule_keyboard

router = Router()

@router.callback_query(F.data == "planer_lessons")
async def planner_menu(callback: CallbackQuery):
    """Открывает меню планера"""
    await callback.message.edit_text(
        "🔄 Регулярные занятия\n\n"

       " Настройте расписание для занятий, которые проходят на постоянной основе. \n"
        "Все события будут автоматически добавляться в ваше основное расписание.\n\n"

        "👇 Выберите действие:",
        reply_markup=get_planner_keyboard()
    )
    await callback.answer()

@router.callback_query(F.data == "back_to_planner")
async def back_to_planner(callback: CallbackQuery, state: FSMContext):
    """Возврат в меню планера"""
    await state.clear()
    await planner_menu(callback)

@router.callback_query(F.data == "back_to_schedule")
async def back_to_schedule(callback: CallbackQuery, state: FSMContext):
    """Возврат в меню расписания"""
    await state.clear()
    await callback.message.edit_text(
        "📅 <b>Управление расписанием</b>\n\n"
        "Выберите действие:",
        reply_markup=get_schedule_keyboard()
    )
    await callback.answer()
