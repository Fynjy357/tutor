from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
import logging
import asyncio
from database import Database

from .keyboards import (
    get_inactive_students_keyboard,
    get_activate_student_keyboard,
    get_back_to_students_keyboard
)

logger = logging.getLogger(__name__)

# Вспомогательная функция для асинхронного вызова синхронных методов
async def run_in_executor(func, *args):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, func, *args)

# Создаем экземпляр роутера (а не функцию)
inactive_students_router = Router()

@inactive_students_router.callback_query(F.data == "show_inactive_menu")
async def show_inactive_students(callback: types.CallbackQuery, state: FSMContext):
    """Показать неактивных учеников"""
    try:
        logger.info(f"🔄 Показать неактивных учеников. User: {callback.from_user.id}")
        await callback.answer()
        
        db = Database()
        telegram_id = callback.from_user.id
        
        # Сначала получаем tutor_id из базы данных
        tutor_id = await run_in_executor(db.get_tutor_id_by_telegram_id, telegram_id)
        
        if not tutor_id:
            await callback.message.edit_text(
                "❌ Ошибка: не найден ID репетитора",
                parse_mode="HTML"
            )
            return
        
        logger.debug(f"📋 Получение неактивных учеников для tutor_id: {tutor_id}")
        inactive_students = await run_in_executor(db.get_inactive_students, tutor_id)
        logger.debug(f"📊 Найдено неактивных учеников: {len(inactive_students)}")
        
        if not inactive_students:
            await callback.message.edit_text(
                "🌙 <b>Неактивные ученики</b>\n\n"
                "У вас пока нет неактивных учеников.",
                reply_markup=get_back_to_students_keyboard(),
                parse_mode="HTML"
            )
            return
        
        text = (
            "🌙 <b>Неактивные ученики</b>\n\n"
            f"Найдено: {len(inactive_students)}\n\n"
            "Выберите ученика для активации:"
        )
        
        await callback.message.edit_text(
            text,
            reply_markup=get_inactive_students_keyboard(inactive_students),
            parse_mode="HTML"
        )
        
    except Exception as e:
        logger.error(f"Error showing inactive students: {e}")
        await callback.answer("❌ Ошибка загрузки", show_alert=True)

@inactive_students_router.callback_query(F.data.startswith("inactive_page_"))
async def handle_inactive_pagination(callback: types.CallbackQuery, state: FSMContext):
    """Пагинация неактивных учеников"""
    try:
        await callback.answer()
        
        page = int(callback.data.split("_")[2])
        db = Database()
        telegram_id = callback.from_user.id
        
        # Сначала получаем tutor_id
        tutor_id = await run_in_executor(db.get_tutor_id_by_telegram_id, telegram_id)
        
        if not tutor_id:
            await callback.answer("❌ Ошибка: не найден ID репетитора", show_alert=True)
            return
        
        inactive_students = await run_in_executor(db.get_inactive_students, tutor_id)
        
        text = (
            "🌙 <b>Неактивные ученики</b>\n\n"
            f"Найдено: {len(inactive_students)}\n\n"
            "Выберите ученика для активации:"
        )
        
        await callback.message.edit_text(
            text,
            reply_markup=get_inactive_students_keyboard(inactive_students, page),
            parse_mode="HTML"
        )
        
    except Exception as e:
        logger.error(f"Error in pagination: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)

@inactive_students_router.callback_query(F.data.startswith("inactive_student_"))
async def show_inactive_student_detail(callback: types.CallbackQuery, state: FSMContext):
    """Показать детали неактивного ученика"""
    try:
        await callback.answer()
        
        student_id = int(callback.data.split("_")[2])
        db = Database()
        
        student = await run_in_executor(db.get_student_by_id, student_id)
        
        if not student:
            await callback.answer("❌ Ученик не найден", show_alert=True)
            return
        
        text = (
            "👤 <b>Неактивный ученик</b>\n\n"
            f"<b>Имя:</b> {student.get('full_name', 'Не указано')}\n"
            f"<b>Телефон:</b> {student.get('phone', 'Не указан')}\n"
            f"<b>Статус:</b> ❌ Неактивный\n\n"
            "Хотите активировать ученика?"
        )
        
        await callback.message.edit_text(
            text,
            reply_markup=get_activate_student_keyboard(student_id),
            parse_mode="HTML"
        )
        
    except Exception as e:
        logger.error(f"Error showing student detail: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)

@inactive_students_router.callback_query(F.data.startswith("activate_student_"))
async def activate_student_handler(callback: types.CallbackQuery, state: FSMContext):
    """Активировать ученика"""
    try:
        await callback.answer()
        
        student_id = int(callback.data.split("_")[2])
        logger.info(f"🔄 Активация ученика ID: {student_id}")
        
        db = Database()
        success = await run_in_executor(db.activate_student, student_id)
        
        if success:
            await callback.message.edit_text(
                "✅ <b>Ученик активирован!</b>\n\n"
                "Статус успешно изменен на 'active'.",
                reply_markup=get_back_to_students_keyboard(),
                parse_mode="HTML"
            )
        else:
            await callback.message.edit_text(
                "❌ <b>Ошибка активации</b>\n\n"
                "Не удалось активировать ученика.",
                reply_markup=get_back_to_students_keyboard(),
                parse_mode="HTML"
            )
            
    except Exception as e:
        logger.error(f"Error activating student: {e}")
        await callback.answer("❌ Ошибка активации", show_alert=True)