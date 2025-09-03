from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from handlers.groups.state import GroupStates
from database import db
from handlers.groups.keyboards import *

router = Router()

# Сохранение группы
@router.callback_query(F.data == "save_group")
async def save_group(callback_query: CallbackQuery, state: FSMContext):
    """Сохранение новой группы"""
    await callback_query.answer()
    
    data = await state.get_data()
    group_name = data.get('group_name')
    tutor_id = db.get_tutor_id_by_telegram_id(callback_query.from_user.id)
    
    if group_name and tutor_id:
        group_id = db.add_group(group_name, tutor_id)
        text = f"✅ Группа создана!\nНазвание: {group_name}" if group_id else "❌ Ошибка при создании!"
    else:
        text = "❌ Ошибка данных!"
    
    await callback_query.message.edit_text(text)
    await state.clear()
    # Обработчик удаления группы
@router.callback_query(F.data.startswith("delete_group_"))
async def delete_group_confirmation(callback_query: CallbackQuery):
    """Подтверждение удаления группы"""
    await callback_query.answer()
    
    group_id = int(callback_query.data.split("_")[2])
    group = db.get_group_by_id(group_id)
    
    await callback_query.message.edit_text(
        f"⚠️ <b>Удалить группу?</b>\n\n{group['name']}\n\nЭто действие нельзя отменить!",
        reply_markup=get_delete_confirmation_keyboard(group_id),
        parse_mode="HTML"
    )

# Подтверждение удаления группы
@router.callback_query(F.data.startswith("confirm_delete_"))
async def confirm_delete_group(callback_query: CallbackQuery):
    """Подтвержденное удаление группы"""
    await callback_query.answer()
    
    group_id = int(callback_query.data.split("_")[2])
    group = db.get_group_by_id(group_id)
    
    success = db.delete_group(group_id)
    text = f"✅ Группа удалена!\n{group['name']}" if success else "❌ Ошибка!"
    
    await callback_query.message.edit_text(text)

# Обработчик редактирования группы
@router.callback_query(F.data.startswith("edit_group_"))
async def edit_group_name(callback_query: CallbackQuery, state: FSMContext):
    """Редактирование названия группы"""
    await callback_query.answer()
    
    group_id = int(callback_query.data.split("_")[2])
    group = db.get_group_by_id(group_id)
    
    await callback_query.message.edit_text(
        f"✏️ <b>Редактирование группы</b>\n\n"
        f"Текущее название: {group['name']}\n\n"
        "Введите новое название:",
        reply_markup=get_back_to_groups_menu_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(GroupStates.editing_group)
    await state.update_data(editing_group_id=group_id)

# Обработчик нового названия группы
@router.message(GroupStates.editing_group)
async def process_new_group_name(message: Message, state: FSMContext):
    """Обработка нового названия группы"""
    new_name = message.text.strip()
    data = await state.get_data()
    group_id = data.get('editing_group_id')
    
    if len(new_name) > 50:
        await message.answer("❌ Название слишком длинное! Максимум 50 символов.")
        return
    
    success = db.update_group_name(group_id, new_name)
    text = f"✅ Название обновлено!\n{new_name}" if success else "❌ Ошибка!"
    
    await message.answer(text)
    await state.clear()