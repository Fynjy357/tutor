from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter
from datetime import datetime, date
import math
from aiogram.exceptions import TelegramBadRequest

from database import db
from handlers.students.keyboards_student import (
    get_dates_keyboard, 
    get_reports_keyboard, 
    get_report_edit_keyboard,
    get_cancel_edit_keyboard,
    get_students_menu_keyboard
)

router = Router()

class ReportEditStates:
    waiting_for_comment = "waiting_for_comment"

# Начало редактирования отчетов
@router.callback_query(F.data == "edit_reports")
async def start_report_editing(callback_query: CallbackQuery):
    """Начало редактирования отчетов"""
    try:
        await callback_query.answer()
    except TelegramBadRequest as e:
        if "query is too old" in str(e):
            # Игнорируем устаревшие запросы
            return
        raise
    
    tutor_id = db.get_tutor_id_by_telegram_id(callback_query.from_user.id)
    if not tutor_id:
        await callback_query.message.answer("Ошибка: репетитор не найден")
        return
    
    # Получаем даты занятий с отчетами
    dates = db.get_dates_with_reports(tutor_id)
    
    if not dates:
        await callback_query.message.answer("Нет отчетов для редактирования")
        return
    
    total_pages = math.ceil(len(dates) / 6)
    keyboard = get_dates_keyboard(dates, page=0, total_pages=total_pages)
    
    await callback_query.message.edit_text(
        "📅 Выберите дату занятия для редактирования отчетов:",
        reply_markup=keyboard
    )

# Навигация по страницам дат
@router.callback_query(F.data.startswith("reports_page_"))
async def navigate_dates_pages(callback_query: CallbackQuery):
    """Навигация по страницам с датами"""
    await callback_query.answer()
    
    page = int(callback_query.data.split("_")[2])
    tutor_id = db.get_tutor_id_by_telegram_id(callback_query.from_user.id)
    
    dates = db.get_dates_with_reports(tutor_id)
    total_pages = math.ceil(len(dates) / 6)
    
    keyboard = get_dates_keyboard(dates, page=page, total_pages=total_pages)
    
    await callback_query.message.edit_text(
        "📅 Выберите дату занятия для редактирования отчетов:",
        reply_markup=keyboard
    )

# Выбор даты
@router.callback_query(F.data.startswith("report_date_"))
async def select_date(callback_query: CallbackQuery):
    """Выбор даты для просмотра отчетов"""
    await callback_query.answer()
    
    date_str = callback_query.data.split("_")[2]
    selected_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    tutor_id = db.get_tutor_id_by_telegram_id(callback_query.from_user.id)
    
    # Получаем отчеты для выбранной даты
    reports = db.get_reports_by_date(tutor_id, selected_date)
    
    if not reports:
        await callback_query.message.answer("Нет отчетов для выбранной даты")
        return
    
    total_pages = math.ceil(len(reports) / 6)
    keyboard = get_reports_keyboard(reports, page=0, total_pages=total_pages)
    
    await callback_query.message.edit_text(
        f"📋 Отчеты за {selected_date.strftime('%d.%m.%Y')}:\nВыберите отчет для редактирования:",
        reply_markup=keyboard
    )

# Навигация по страницам отчетов
@router.callback_query(F.data.startswith("reports_list_page_"))
async def navigate_reports_pages(callback_query: CallbackQuery):
    """Навигация по страницам с отчетами"""
    await callback_query.answer()
    
    page = int(callback_query.data.split("_")[3])
    # Извлекаем дату из текста сообщения
    message_text = callback_query.message.text
    date_str = message_text.split("за ")[1].split(":")[0].strip()
    selected_date = datetime.strptime(date_str, "%d.%m.%Y").date()
    
    tutor_id = db.get_tutor_id_by_telegram_id(callback_query.from_user.id)
    reports = db.get_reports_by_date(tutor_id, selected_date)
    
    total_pages = math.ceil(len(reports) / 6)
    keyboard = get_reports_keyboard(reports, page=page, total_pages=total_pages)
    
    await callback_query.message.edit_text(
        f"📋 Отчеты за {selected_date.strftime('%d.%m.%Y')}:\nВыберите отчет для редактирования:",
        reply_markup=keyboard
    )

# Выбор отчета для редактирования
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
        
        # Формируем текст отчета - используем lesson_time вместо time
        report_text = f"""📋 Отчет ученика: {report['student_name']}
📅 Дата: {report['lesson_date'].strftime('%d.%m.%Y')}
⏰ Время: {report.get('lesson_time', 'Не указано')}

✅ Присутствие: {'Да' if report['lesson_held'] else 'Нет'}
💰 Оплачено: {'Да' if report['lesson_paid'] else 'Нет'}
📚 ДЗ выполнено: {'Да' if report['homework_done'] else 'Нет'}
📝 Комментарий: {report['student_performance'] or 'Нет комментария'}"""
        
        keyboard = get_report_edit_keyboard(report_id)
        await callback_query.message.edit_text(report_text, reply_markup=keyboard)
        
    except ValueError:
        await callback_query.answer("Ошибка обработки запроса", show_alert=True)
    except Exception as e:
        await callback_query.answer(f"Произошла ошибка: {str(e)}", show_alert=True)

# Переключение присутствия
@router.callback_query(F.data.startswith("toggle_attendance_"))
async def toggle_attendance(callback_query: CallbackQuery):
    """Переключение статуса присутствия"""
    await callback_query.answer()
    
    report_id = int(callback_query.data.split("_")[2])
    report = db.get_report_by_id(report_id)
    
    if report:
        new_value = not report['lesson_held']
        db.update_report_attendance(report_id, new_value)
        
        # Обновляем сообщение
        report = db.get_report_by_id(report_id)
        report_text = f"""📋 Отчет ученика: {report['student_name']}
📅 Дата: {report['lesson_date'].strftime('%d.%m.%Y')}
⏰ Время: {report['lesson_time']}

✅ Присутствие: {'Да' if report['lesson_held'] else 'Нет'}
💰 Оплачено: {'Да' if report['lesson_paid'] else 'Нет'}
📚 ДЗ выполнено: {'Да' if report['homework_done'] else 'Нет'}
📝 Комментарий: {report['student_performance'] or 'Нет комментария'}"""
        
        keyboard = get_report_edit_keyboard(report_id)
        await callback_query.message.edit_text(report_text, reply_markup=keyboard)

# Переключение оплаты
@router.callback_query(F.data.startswith("toggle_payment_"))
async def toggle_payment(callback_query: CallbackQuery):
    """Переключение статуса оплаты"""
    await callback_query.answer()
    
    report_id = int(callback_query.data.split("_")[2])
    report = db.get_report_by_id(report_id)
    
    if report:
        new_value = not report['lesson_paid']
        db.update_report_payment(report_id, new_value)
        
        # Обновляем сообщение
        report = db.get_report_by_id(report_id)
        report_text = f"""📋 Отчет ученика: {report['student_name']}
📅 Дата: {report['lesson_date'].strftime('%d.%m.%Y')}
⏰ Время: {report['lesson_time']}

✅ Присутствие: {'Да' if report['lesson_held'] else 'Нет'}
💰 Оплачено: {'Да' if report['lesson_paid'] else 'Нет'}
📚 ДЗ выполнено: {'Да' if report['homework_done'] else 'Нет'}
📝 Комментарий: {report['student_performance'] or 'Нет комментария'}"""
        
        keyboard = get_report_edit_keyboard(report_id)
        await callback_query.message.edit_text(report_text, reply_markup=keyboard)

# Переключение домашнего задания
@router.callback_query(F.data.startswith("toggle_homework_"))
async def toggle_homework(callback_query: CallbackQuery):
    """Переключение статуса домашнего задания"""
    await callback_query.answer()
    
    report_id = int(callback_query.data.split("_")[2])
    report = db.get_report_by_id(report_id)
    
    if report:
        new_value = not report['homework_done']
        db.update_report_homework(report_id, new_value)
        
        # Обновляем сообщение
        report = db.get_report_by_id(report_id)
        report_text = f"""📋 Отчет ученика: {report['student_name']}
📅 Дата: {report['lesson_date'].strftime('%d.%m.%Y')}
⏰ Время: {report['lesson_time']}

✅ Присутствие: {'Да' if report['lesson_held'] else 'Нет'}
💰 Оплачено: {'Да' if report['lesson_paid'] else 'Нет'}
📚 ДЗ выполнено: {'Да' if report['homework_done'] else 'Нет'}
📝 Комментарий: {report['student_performance'] or 'Нет комментария'}"""
        
        keyboard = get_report_edit_keyboard(report_id)
        await callback_query.message.edit_text(report_text, reply_markup=keyboard)

# Редактирование комментария
@router.callback_query(F.data.startswith("edit_comment_"))
async def start_comment_editing(callback_query: CallbackQuery, state: FSMContext):
    """Начало редактирования комментария"""
    await callback_query.answer()
    
    report_id = int(callback_query.data.split("_")[2])
    report = db.get_report_by_id(report_id)
    
    if report:
        await state.set_state(ReportEditStates.waiting_for_comment)
        await state.update_data(editing_report_id=report_id)
        
        keyboard = get_cancel_edit_keyboard()
        
        await callback_query.message.edit_text(
            f"✏️ Введите новый комментарий для отчета ученика {report['student_name']}:\n\nТекущий комментарий: {report['student_performance'] or 'Нет комментария'}",
            reply_markup=keyboard
        )

# Обработка нового комментария
@router.message(StateFilter(ReportEditStates.waiting_for_comment))
async def process_new_comment(message: Message, state: FSMContext):
    """Обработка нового комментария"""
    data = await state.get_data()
    report_id = data.get('editing_report_id')
    
    if report_id:
        db.update_report_comment(report_id, message.text)
        await message.answer("✅ Комментарий обновлен!")
        
        # Возвращаемся к редактированию отчета
        report = db.get_report_by_id(report_id)
        report_text = f"""📋 Отчет ученика: {report['student_name']}
📅 Дата: {report['lesson_date'].strftime('%d.%m.%Y')}
⏰ Время: {report['lesson_time']}

✅ Присутствие: {'Да' if report['lesson_held'] else 'Нет'}
💰 Оплачено: {'Да' if report['lesson_paid'] else 'Нет'}
📚 ДЗ выполнено: {'Да' if report['homework_done'] else 'Нет'}
📝 Комментарий: {message.text}"""
        
        keyboard = get_report_edit_keyboard(report_id)
        await message.answer(report_text, reply_markup=keyboard)
    
    await state.clear()

# Отмена редактирования комментария
@router.callback_query(F.data == "cancel_edit")
async def cancel_comment_editing(callback_query: CallbackQuery, state: FSMContext):
    """Отмена редактирования комментария"""
    await callback_query.answer()
    
    data = await state.get_data()  # Сначала получаем данные
    report_id = data.get('editing_report_id')
    await state.clear()
    
    if report_id:
        report = db.get_report_by_id(report_id)
        report_text = f"""📋 Отчет ученика: {report['student_name']}
📅 Дата: {report['lesson_date'].strftime('%d.%m.%Y')}
⏰ Время: {report['lesson_time']}

✅ Присутствие: {'Да' if report['lesson_held'] else 'Нет'}
💰 Оплачено: {'Да' if report['lesson_paid'] else 'Нет'}
📚 ДЗ выполнено: {'Да' if report['homework_done'] else 'Нет'}
📝 Комментарий: {report['student_performance'] or 'Нет комментария'}"""
        
        keyboard = get_report_edit_keyboard(report_id)
        await callback_query.message.edit_text(report_text, reply_markup=keyboard)

# Назад к отчетам
@router.callback_query(F.data == "back_to_reports")
async def back_to_reports(callback_query: CallbackQuery):
    """Возврат к списку отчетов"""
    await callback_query.answer()
    
    # Извлекаем дату из предыдущего сообщения
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

# Назад к датам
@router.callback_query(F.data == "back_to_dates")
async def back_to_dates(callback_query: CallbackQuery):
    """Возврат к выбору даты"""
    await callback_query.answer()
    
    tutor_id = db.get_tutor_id_by_telegram_id(callback_query.from_user.id)
    dates = db.get_dates_with_reports(tutor_id)
    
    total_pages = math.ceil(len(dates) / 6)
    keyboard = get_dates_keyboard(dates, page=0, total_pages=total_pages)
    
    await callback_query.message.edit_text(
        "📅 Выберите дату занятия для редактирования отчетов:",
        reply_markup=keyboard
    )

# Назад в главное меню учеников
@router.callback_query(F.data == "back_to_students_menu")
async def back_to_students_menu(callback_query: CallbackQuery):
    """Возврат в главное меню учеников"""
    await callback_query.answer()
    
    keyboard = get_students_menu_keyboard()
    await callback_query.message.edit_text(
        "👨‍🎓 Управление учениками\n\nВыберите действие:",
        reply_markup=keyboard
    )

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
        
        # Формируем текст отчета - используем lesson_time вместо time
        report_text = f"""📋 Отчет ученика: {report['student_name']}
📅 Дата: {report['lesson_date'].strftime('%d.%m.%Y')}
⏰ Время: {report['lesson_time']}

✅ Присутствие: {'Да' if report['lesson_held'] else 'Нет'}
💰 Оплачено: {'Да' if report['lesson_paid'] else 'Нет'}
📚 ДЗ выполнено: {'Да' if report['homework_done'] else 'Нет'}
📝 Комментарий: {report['student_performance'] or 'Нет комментария'}"""
        
        keyboard = get_report_edit_keyboard(report_id)
        await callback_query.message.edit_text(report_text, reply_markup=keyboard)
        
    except ValueError:
        await callback_query.answer("Ошибка обработки запроса", show_alert=True)
    except Exception as e:
        await callback_query.answer(f"Произошла ошибка: {str(e)}", show_alert=True)