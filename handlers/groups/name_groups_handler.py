from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from handlers.groups.keyboards import *
from handlers.groups.state import GroupStates

router = Router()


# Экран 2 - Ввод названия группы
@router.callback_query(F.data == "add_group")
async def add_group_name(callback_query: CallbackQuery, state: FSMContext):
    """Ввод названия новой группы"""
    await callback_query.answer()
    
    await callback_query.message.edit_text(
        "📝 <b>Введите название новой группы:</b>\n\n"
        "Например: 'Начинающие', 'Продвинутые', 'Подготовка к ЕГЭ'",
        reply_markup=get_back_to_groups_menu_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(GroupStates.waiting_for_group_name)

    # Обработчик ввода названия группы
@router.message(GroupStates.waiting_for_group_name)
async def process_group_name(message: Message, state: FSMContext):
    """Обработка ввода названия группы"""
    group_name = message.text.strip()
    
    if len(group_name) > 50:
        await message.answer("❌ Название слишком длинное! Максимум 50 символов.")
        return
    
    await state.update_data(group_name=group_name)
    
    await message.answer(
        f"✅ <b>Подтвердите создание группы:</b>\n\n"
        f"Название: {group_name}\n\nСохранить группу?",
        reply_markup=get_group_confirm_keyboard(),
        parse_mode="HTML"
    )