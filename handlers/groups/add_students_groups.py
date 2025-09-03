from aiogram import Router, F
from aiogram.types import CallbackQuery
from database import db
from handlers.groups.keyboards import *

router = Router()

# Экран 5 - Добавление учеников в группу
@router.callback_query(F.data.startswith("add_to_group_"))
async def add_students_to_group(callback_query: CallbackQuery):
    """Добавление учеников в группу"""
    await callback_query.answer()
    
    group_id = int(callback_query.data.split("_")[3])
    tutor_id = db.get_tutor_id_by_telegram_id(callback_query.from_user.id)
    students = db.get_available_students_for_group(tutor_id, group_id)
    
    if not students:
        await callback_query.message.edit_text(
            "ℹ️ Нет доступных учеников для добавления",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Назад", callback_data=f"group_{group_id}")]
            ])
        )
        return
    
    await callback_query.message.edit_text(
        "👥 <b>Выберите ученика для добавления:</b>",
        reply_markup=get_students_list_keyboard(students, "add_student", group_id),
        parse_mode="HTML"
    )

# Обработчик добавления ученика
@router.callback_query(F.data.startswith("add_student_"))
async def add_specific_student(callback_query: CallbackQuery):
    """Добавление конкретного ученика в группу"""
    await callback_query.answer()
    
    parts = callback_query.data.split("_")
    student_id = int(parts[2])
    group_id = int(parts[4])
    
    success = db.add_student_to_group(student_id, group_id)
    text = "✅ Ученик добавлен!" if success else "❌ Ошибка!"
    
    await callback_query.message.edit_text(text)

# Экран 6 - Удаление учеников из группы
@router.callback_query(F.data.startswith("remove_from_group_"))
async def remove_students_from_group(callback_query: CallbackQuery):
    """Удаление учеников из группы"""
    await callback_query.answer()
    
    group_id = int(callback_query.data.split("_")[3])
    students = db.get_students_in_group(group_id)
    
    if not students:
        await callback_query.message.edit_text(
            "ℹ️ В группе нет учеников",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Назад", callback_data=f"group_{group_id}")]
            ])
        )
        return
    
    await callback_query.message.edit_text(
        "👥 <b>Выберите ученика для удаления:</b>",
        reply_markup=get_students_list_keyboard(students, "remove_student", group_id),
        parse_mode="HTML"
    )

# Обработчик удаления ученика
@router.callback_query(F.data.startswith("remove_student_"))
async def remove_specific_student(callback_query: CallbackQuery):
    """Удаление конкретного ученика из группы"""
    await callback_query.answer()
    
    parts = callback_query.data.split("_")
    student_id = int(parts[2])
    group_id = int(parts[4])
    
    success = db.remove_student_from_group(student_id, group_id)
    text = "✅ Ученик удален!" if success else "❌ Ошибка!"
    
    await callback_query.message.edit_text(text)