# handlers/students/handlers.py
import logging
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest
from aiogram import Router, types, F
from database import db

from handlers.students.keyboards_student import get_students_menu_keyboard
from .keyboards import get_student_detail_keyboard
from .utils import format_student_info

router = Router()
logger = logging.getLogger(__name__)

@router.callback_query(F.data.startswith("student_"))
async def show_student_detail(callback_query: types.CallbackQuery):
    await callback_query.answer()
    
    # Извлекаем ID ученика из callback_data (формат: "student_123")
    student_id = int(callback_query.data.split("_")[1])
    
    # Получаем данные ученика из БД
    student = db.get_student_by_id(student_id)
    
    if not student:
        await callback_query.message.edit_text("❌ Ученик не найден!")
        return
    
    # Форматируем информацию об ученике
    student_info = format_student_info(student)
    
    # Показываем детальную информацию с клавиатурой
    try:
        await callback_query.message.edit_text(
            student_info,
            reply_markup=get_student_detail_keyboard(student_id),
            parse_mode="HTML"
        )
    except Exception as e:
        # Если не удалось изменить сообщение, отправляем новое
        await callback_query.message.answer(
            student_info,
            reply_markup=get_student_detail_keyboard(student_id),
            parse_mode="HTML"
        )


@router.callback_query(F.data == "back_to_students_menu")
async def back_to_students_menu(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.answer()
    
    # Очищаем состояние если было активно
    current_state = await state.get_state()
    if current_state:
        await state.clear()
    
    text = (
        "👥 <b>Учет учеников</b>\n\n"
        "Здесь вы можете управлять вашими учениками: добавлять новых, "
        "просматривать и редактировать информацию о существующих."
    )
    
    try:
        await callback_query.message.edit_text(
            text,
            reply_markup=get_students_menu_keyboard(),
            parse_mode="HTML"
        )
    except TelegramBadRequest:
        await callback_query.message.answer(
            text,
            reply_markup=get_students_menu_keyboard(),
            parse_mode="HTML"
        )