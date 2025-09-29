# handlers/report_editor/navigation_handlers.py
from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.exceptions import TelegramBadRequest
import math
from datetime import datetime

from database import db
from .keyboards import get_dates_keyboard, get_reports_keyboard, get_students_menu_keyboard

router = Router()

@router.callback_query(F.data == "edit_reports")
async def start_report_editing(callback_query: CallbackQuery):
    """Начало редактирования отчетов"""
    try:
        await callback_query.answer()
    except TelegramBadRequest as e:
        if "query is too old" in str(e):
            return
        raise
    
    tutor_id = db.get_tutor_id_by_telegram_id(callback_query.from_user.id)
    if not tutor_id:
        await callback_query.message.answer("Ошибка: репетитор не найден")
        return
    
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

@router.callback_query(F.data.startswith("report_date_"))
async def select_date(callback_query: CallbackQuery):
    """Выбор даты для просмотра отчетов"""
    await callback_query.answer()
    
    date_str = callback_query.data.split("_")[2]
    selected_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    tutor_id = db.get_tutor_id_by_telegram_id(callback_query.from_user.id)
    
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

@router.callback_query(F.data.startswith("reports_list_page_"))
async def navigate_reports_pages(callback_query: CallbackQuery):
    """Навигация по страницам с отчетами"""
    await callback_query.answer()
    
    page = int(callback_query.data.split("_")[3])
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

# @router.callback_query(F.data == "back_to_students_menu")
# async def back_to_students_menu(callback_query: CallbackQuery):
#     """Возврат в главное меню учеников"""
#     await callback_query.answer()
    
#     keyboard = get_students_menu_keyboard()
#     await callback_query.message.edit_text(
#         "👨‍🎓 Управление учениками\n\nВыберите действие:",
#         reply_markup=keyboard
#     )
