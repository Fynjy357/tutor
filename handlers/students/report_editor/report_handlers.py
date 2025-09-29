# handlers/report_editor/report_handlers.py
import math
from aiogram import Router, F
from aiogram.types import CallbackQuery

from database import db
from .keyboards import get_report_edit_keyboard, get_reports_keyboard
from datetime import datetime

router = Router()

def format_report_text(report):
    """Форматирование текста отчета"""
    # Безопасное форматирование даты
    lesson_date = report.get('lesson_date', 'Не указано')
    if lesson_date and lesson_date != 'Не указано':
        if isinstance(lesson_date, str):
            # Если дата в строковом формате
            try:
                lesson_date = datetime.strptime(lesson_date, '%Y-%m-%d').strftime('%d.%m.%Y')
            except:
                pass
        elif hasattr(lesson_date, 'strftime'):
            # Если объект date/datetime
            lesson_date = lesson_date.strftime('%d.%m.%Y')
    
    return f"""📋 Отчет ученика: {report['student_name']}
📅 Дата: {lesson_date}
⏰ Время: {report.get('lesson_time', 'Не указано')}

✅ Присутствие: {'Да' if report['lesson_held'] else 'Нет'}
💰 Оплачено: {'Да' if report['lesson_paid'] else 'Нет'}
📚 ДЗ выполнено: {'Да' if report['homework_done'] else 'Нет'}
📝 Комментарий ученику: {report['student_performance'] or 'Нет комментария'}
👨‍👩‍👧‍👦 Заметка родителям: {report['parent_performance'] or 'Нет заметки'}"""

@router.callback_query(F.data.startswith("select_report:"))
async def select_report(callback_query: CallbackQuery):
    """Обработчик выбора конкретного отчета"""
    await callback_query.answer()
    
    try:
        report_id = int(callback_query.data.split(":")[1])
        report = db.get_report_by_id(report_id)
        
        if not report:
            await callback_query.message.answer("Отчет не найден")
            return
        
        report_text = format_report_text(report)
        keyboard = get_report_edit_keyboard(report_id)
        await callback_query.message.edit_text(report_text, reply_markup=keyboard)
        
    except ValueError:
        await callback_query.answer("Ошибка обработки запроса", show_alert=True)
    except Exception as e:
        await callback_query.answer(f"Произошла ошибка: {str(e)}", show_alert=True)

@router.callback_query(F.data.startswith("toggle_attendance_"))
async def toggle_attendance(callback_query: CallbackQuery):
    """Переключение статуса присутствия"""
    await callback_query.answer()
    
    report_id = int(callback_query.data.split("_")[2])
    report = db.get_report_by_id(report_id)
    
    if report:
        new_value = not report['lesson_held']
        db.update_report_attendance(report_id, new_value)
        
        report = db.get_report_by_id(report_id)
        report_text = format_report_text(report)
        keyboard = get_report_edit_keyboard(report_id)
        await callback_query.message.edit_text(report_text, reply_markup=keyboard)

@router.callback_query(F.data.startswith("toggle_payment_"))
async def toggle_payment(callback_query: CallbackQuery):
    """Переключение статуса оплаты"""
    await callback_query.answer()
    
    report_id = int(callback_query.data.split("_")[2])
    report = db.get_report_by_id(report_id)
    
    if report:
        new_value = not report['lesson_paid']
        db.update_report_payment(report_id, new_value)
        
        report = db.get_report_by_id(report_id)
        report_text = format_report_text(report)
        keyboard = get_report_edit_keyboard(report_id)
        await callback_query.message.edit_text(report_text, reply_markup=keyboard)

@router.callback_query(F.data.startswith("toggle_homework_"))
async def toggle_homework(callback_query: CallbackQuery):
    """Переключение статуса домашнего задания"""
    await callback_query.answer()
    
    report_id = int(callback_query.data.split("_")[2])
    report = db.get_report_by_id(report_id)
    
    if report:
        new_value = not report['homework_done']
        db.update_report_homework(report_id, new_value)
        
        report = db.get_report_by_id(report_id)
        report_text = format_report_text(report)
        keyboard = get_report_edit_keyboard(report_id)
        await callback_query.message.edit_text(report_text, reply_markup=keyboard)

@router.callback_query(F.data == "back_to_reports")
async def back_to_reports(callback_query: CallbackQuery):
    """Возврат к списку отчетов"""
    await callback_query.answer()
    
    message_text = callback_query.message.text
    if "Дата:" in message_text:
        date_line = [line for line in message_text.split('\n') if 'Дата:' in line][0]
        date_str = date_line.split("Дата: ")[1].strip()
        selected_date = datetime.strptime(date_str, "%d.%m.%Y").date()
        
        tutor_id = db.get_tutor_id_by_telegram_id(callback_query.from_user.id)
        reports = db.get_reports_by_date(tutor_id, selected_date)
        
        total_pages = math.ceil(len(reports) / 6)
        keyboard = get_reports_keyboard(reports, page=0, total_pages=total_pages)
        
        await callback_query.message.edit_text(
            f"📋 Отчеты за {selected_date.strftime('%d.%m.%Y')}:\nВыберите отчет для редактирования:",
            reply_markup=keyboard
        )
