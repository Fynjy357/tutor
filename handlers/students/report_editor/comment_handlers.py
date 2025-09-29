# handlers/report_editor/comment_handlers.py
import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter

from database import db
from .states import ReportEditStates
from .keyboards import get_cancel_edit_keyboard, get_report_edit_keyboard
from .report_handlers import format_report_text

router = Router()
logger = logging.getLogger(__name__)

@router.callback_query(F.data.startswith("edit_student_comment_"))
async def start_student_comment_editing(callback_query: CallbackQuery, state: FSMContext):
    """Начало редактирования комментария ученику"""
    await callback_query.answer()

    print(f"DEBUG: callback data = {callback_query.data}")
    print(f"DEBUG: split result = {callback_query.data.split('_')}")
    
    try:
        # Берем ID отчета (последний элемент после разделения по '_')
        report_id = int(callback_query.data.split("_")[-1])
        report = db.get_report_by_id(report_id)
        
        if report:
            await state.set_state(ReportEditStates.waiting_for_student_comment)
            await state.update_data(editing_report_id=report_id)
            
            keyboard = get_cancel_edit_keyboard()
            
            await callback_query.message.edit_text(
                f"✏️ Введите новый комментарий для ученика {report['student_name']}:\n\n"
                f"Текущий комментарий: {report['student_performance'] or 'Нет комментария'}",
                reply_markup=keyboard
            )
        else:
            await callback_query.message.edit_text("❌ Отчет не найден!")
            
    except (ValueError, IndexError) as e:
        logger.error(f"Ошибка парсинга callback data: {e}")
        await callback_query.message.edit_text("❌ Ошибка при обработке запроса!")

@router.callback_query(F.data.startswith("edit_parent_comment_"))
async def start_parent_comment_editing(callback_query: CallbackQuery, state: FSMContext):
    """Начало редактирования заметки родителям"""
    await callback_query.answer()
    
    report_id = int(callback_query.data.split("_")[-1])
    report = db.get_report_by_id(report_id)
    
    if report:
        await state.set_state(ReportEditStates.waiting_for_parent_comment)
        await state.update_data(editing_report_id=report_id)
        
        keyboard = get_cancel_edit_keyboard()
        
        await callback_query.message.edit_text(
            f"✏️ Введите новую заметку для родителей ученика {report['student_name']}:\n\nТекущая заметка: {report['parent_performance'] or 'Нет заметки'}",
            reply_markup=keyboard
        )

@router.message(StateFilter(ReportEditStates.waiting_for_student_comment))
async def process_student_comment(message: Message, state: FSMContext):
    """Обработка нового комментария ученику"""
    data = await state.get_data()
    report_id = data.get('editing_report_id')
    
    if report_id:
        # Используем существующий метод для комментария ученику
        db.update_report_comment(report_id, message.text)
        await message.answer("✅ Комментарий ученику обновлен!")
        
        report = db.get_report_by_id(report_id)
        report_text = format_report_text(report)
        keyboard = get_report_edit_keyboard(report_id)
        await message.answer(report_text, reply_markup=keyboard)
    
    await state.clear()

@router.message(StateFilter(ReportEditStates.waiting_for_parent_comment))
async def process_parent_comment(message: Message, state: FSMContext):
    """Обработка новой заметки родителям"""
    data = await state.get_data()
    report_id = data.get('editing_report_id')
    
    if report_id:
        # Используем новый метод для заметки родителям
        db.update_parent_comment(report_id, message.text)
        await message.answer("✅ Заметка родителям обновлена!")
        
        report = db.get_report_by_id(report_id)
        report_text = format_report_text(report)
        keyboard = get_report_edit_keyboard(report_id)
        await message.answer(report_text, reply_markup=keyboard)
    
    await state.clear()

@router.callback_query(F.data == "cancel_edit")
async def cancel_comment_editing(callback_query: CallbackQuery, state: FSMContext):
    """Отмена редактирования комментария"""
    await callback_query.answer()
    
    data = await state.get_data()
    report_id = data.get('editing_report_id')
    await state.clear()
    
    if report_id:
        report = db.get_report_by_id(report_id)
        report_text = format_report_text(report)
        keyboard = get_report_edit_keyboard(report_id)
        await callback_query.message.edit_text(report_text, reply_markup=keyboard)
