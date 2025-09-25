# handlers/schedule/planner/handlers/edit_fields.py
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
import re
import logging

from handlers.schedule.planner.utils.task_helpers import get_task_by_id, show_task_edit_menu_after_edit
from database import db

router = Router()
logger = logging.getLogger(__name__)

class EditTaskState(StatesGroup):
    waiting_for_time = State()
    waiting_for_duration = State()
    waiting_for_price = State()

@router.callback_query(F.data.startswith("planner_time_"))
async def planner_edit_time(callback: CallbackQuery, state: FSMContext):
    """Начинает процесс изменения времени"""
    try:
        task_id = int(callback.data.split("_")[2])
        
        # Сохраняем ID задачи в состоянии
        await state.update_data(task_id=task_id)
        await state.set_state(EditTaskState.waiting_for_time)
        
        # Просим пользователя ввести новое время
        await callback.message.edit_text(
            f"🕒 <b>Изменение времени</b>\n\n"
            f"Введите новое время в формате <b>ЧЧ:ММ</b>\n"
            f"Например: <code>14:30</code> или <code>09:00</code>\n\n"
            f"<i>Текущее время будет заменено.</i>",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="❌ Отмена", callback_data=f"planner_menu_{task_id}")
            ]])
        )
        await callback.answer()
    except Exception as e:
        logger.error(f"Ошибка при обработке изменения времени: {e}")
        await callback.answer("❌ Ошибка при изменении времени", show_alert=True)

@router.callback_query(F.data.startswith("planner_duration_"))
async def planner_edit_duration(callback: CallbackQuery, state: FSMContext):
    """Начинает процесс изменения длительности"""
    try:
        task_id = int(callback.data.split("_")[2])
        
        await state.update_data(task_id=task_id)
        await state.set_state(EditTaskState.waiting_for_duration)
        
        await callback.message.edit_text(
            f"⏱️ <b>Изменение длительности</b>\n\n"
            f"Введите новую длительность занятия в <b>минутах</b>\n"
            f"Например: <code>60</code> или <code>90</code>\n\n"
            f"<i>Обычно занятия длятся 60 или 90 минут.</i>",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="❌ Отмена", callback_data=f"planner_menu_{task_id}")
            ]])
        )
        await callback.answer()
    except Exception as e:
        logger.error(f"Ошибка при обработке изменения длительности: {e}")
        await callback.answer("❌ Ошибка при изменении длительности", show_alert=True)

@router.callback_query(F.data.startswith("planner_price_"))
async def planner_edit_price(callback: CallbackQuery, state: FSMContext):
    """Начинает процесс изменения стоимости"""
    try:
        task_id = int(callback.data.split("_")[2])
        
        await state.update_data(task_id=task_id)
        await state.set_state(EditTaskState.waiting_for_price)
        
        await callback.message.edit_text(
            f"💰 <b>Изменение стоимости</b>\n\n"
            f"Введите новую стоимость занятия в <b>рублях</b>\n"
            f"Например: <code>1500</code> или <code>2000</code>\n\n"
            f"<i>Укажите только цифры, без пробелов и символов.</i>",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="❌ Отмена", callback_data=f"planner_menu_{task_id}")
            ]])
        )
        await callback.answer()
    except Exception as e:
        logger.error(f"Ошибка при обработке изменения стоимости: {e}")
        await callback.answer("❌ Ошибка при изменении стоимости", show_alert=True)

@router.message(EditTaskState.waiting_for_time)
async def process_time_input(message: Message, state: FSMContext):
    """Обрабатывает ввод нового времени"""
    time_input = message.text.strip()
    
    # Проверяем формат времени (ЧЧ:ММ)
    if not re.match(r'^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$', time_input):
        await message.answer("❌ Неверный формат времени!\n\n"
                           "Введите время в формате <b>ЧЧ:ММ</b>\n"
                           "Например: <code>14:30</code> или <code>09:00</code>")
        return
    
    # Обновляем время в базе данных
    data = await state.get_data()
    task_id = data.get('task_id')
    
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE planner_actions SET time = ? WHERE id = ?",
                (time_input, task_id)
            )
            conn.commit()
        
        # Получаем обновленную задачу
        task = get_task_by_id(task_id)
        
        await message.answer(f"✅ Время успешно изменено на <b>{time_input}</b>")
        await show_task_edit_menu_after_edit(message, task)
        
    except Exception as e:
        await message.answer("❌ Ошибка при обновлении времени")
        logger.error(f"Ошибка обновления времени: {e}")
    
    await state.clear()

@router.message(EditTaskState.waiting_for_duration)
async def process_duration_input(message: Message, state: FSMContext):
    """Обрабатывает ввод новой длительности"""
    duration_input = message.text.strip()
    
    # Проверяем, что введено число
    if not duration_input.isdigit() or int(duration_input) <= 0:
        await message.answer("❌ Неверный формат длительности!\n\n"
                           "Введите число (минуты)\n"
                           "Например: <code>60</code> или <code>90</code>")
        return
    
    duration = int(duration_input)
    
    # Обновляем длительность в базе данных
    data = await state.get_data()
    task_id = data.get('task_id')
    
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE planner_actions SET duration = ? WHERE id = ?",
                (duration, task_id)
            )
            conn.commit()
        
        task = get_task_by_id(task_id)
        await message.answer(f"✅ Длительность успешно изменена на <b>{duration}</b> минут")
        await show_task_edit_menu_after_edit(message, task)
        
    except Exception as e:
        await message.answer("❌ Ошибка при обновлении длительности")
        logger.error(f"Ошибка обновления длительности: {e}")
    
    await state.clear()

@router.message(EditTaskState.waiting_for_price)
async def process_price_input(message: Message, state: FSMContext):
    """Обрабатывает ввод новой стоимости"""
    price_input = message.text.strip()
    
    # Проверяем, что введено число
    if not price_input.isdigit() or int(price_input) <= 0:
        await message.answer("❌ Неверный формат стоимости!\n\n"
                           "Введите число (рубли)\n"
                           "Например: <code>1500</code> или <code>2000</code>")
        return
    
    price = int(price_input)
    
    # Обновляем стоимость в базе данных
    data = await state.get_data()
    task_id = data.get('task_id')
    
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE planner_actions SET price = ? WHERE id = ?",
                (price, task_id)
            )
            conn.commit()
        
        task = get_task_by_id(task_id)
        await message.answer(f"✅ Стоимость успешно изменена на <b>{price}</b> рублей")
        await show_task_edit_menu_after_edit(message, task)
        
    except Exception as e:
        await message.answer("❌ Ошибка при обновлении стоимости")
        logger.error(f"Ошибка обновления стоимости: {e}")
    
    await state.clear()
