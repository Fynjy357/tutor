from aiogram import Router, F
from aiogram.types import CallbackQuery
from database import db

from handlers.groups.keyboards import *

router = Router()

# Экран 4 - Управление группами (список групп)
@router.callback_query(F.data == "manage_groups")
async def manage_groups(callback_query: CallbackQuery):
    """Список групп для управления"""
    await callback_query.answer()
    
    tutor_id = db.get_tutor_id_by_telegram_id(callback_query.from_user.id)
    groups = db.get_groups_by_tutor(tutor_id)
    
    if not groups:
        await callback_query.message.edit_text(
            "📋 У вас пока нет групп\nСоздайте первую группу.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="➕ Добавить группу", callback_data="add_group")],
                [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_groups_menu")]
            ])
        )
        return
    
    await callback_query.message.edit_text(
        "👨‍👩‍👧‍👦 <b>Ваши группы:</b>\n\nВыберите группу:",
        reply_markup=get_groups_list_keyboard(groups),
        parse_mode="HTML"
    )

# Обработчик выбора конкретной группы
@router.callback_query(F.data.startswith("group_"))
async def group_management(callback_query: CallbackQuery):
    """Управление конкретной группой"""
    await callback_query.answer()
    
    group_id = int(callback_query.data.split("_")[1])
    group = db.get_group_by_id(group_id)
    
    if not group:
        await callback_query.message.edit_text("❌ Группа не найдена!")
        return
    
    students = db.get_students_in_group(group_id)
    
    # Фильтруем только активных учеников
    active_students = [s for s in students if s.get('status') != 'inactive']
    active_count = len(active_students)
    
    # Формируем список ВСЕХ активных учеников
    if active_count > 0:
        students_list = "\n".join([f"• {s['full_name']}" for s in active_students])
    else:
        students_list = "Нет активных учеников"
    
    await callback_query.message.edit_text(
        f"👥 <b>Группа: {group['name']}</b>\n\n"
        f"Активных учеников: {active_count}\n\n"
        f"Ученики:\n{students_list}",
        reply_markup=get_group_management_keyboard(group_id),
        parse_mode="HTML"
    )