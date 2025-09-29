from aiogram import F
from aiogram.types import Message, CallbackQuery, BufferedInputFile
from datetime import datetime
import io
from aiogram import Router

from handlers.start.welcome import show_main_menu

from .pdf_generator import PDFReportGenerator
from .schedule_generator import SchedulePDFGenerator
from .report_service import ReportService
from .schedule_service import ScheduleService
from .keyboards import (
    get_statistics_keyboard, 
    get_reports_months_keyboard, 
    get_schedule_months_keyboard,
    get_back_to_statistics_keyboard
)

router = Router()

@router.callback_query(F.data == "statistics_menu")
async def statistics_menu(callback: CallbackQuery):
    """Меню статистики"""
    await callback.message.edit_text(
        "📈 <b>Статистика</b>\n\nВыберите раздел:",
        reply_markup=get_statistics_keyboard(),
        parse_mode="HTML"
    )

@router.callback_query(F.data == "reports_menu")
async def reports_menu(callback: CallbackQuery):
    """Меню отчетов - выбор месяца"""
    from database import Database
    
    db = Database()
    tutor = db.get_tutor_by_telegram_id(callback.from_user.id)
    
    if not tutor:
        await callback.answer("❌ Репетитор не найден")
        return
    
    report_service = ReportService()
    available_months = report_service.get_available_months(tutor[0])
    
    if not available_months:
        await callback.message.edit_text(
            "📊 <b>Отчеты</b>\n\nНет данных для отчетов",
            reply_markup=get_back_to_statistics_keyboard(),
            parse_mode="HTML"
        )
        return
    
    await callback.message.edit_text(
        "📊 <b>Отчеты</b>\n\nВыберите месяц:",
        reply_markup=get_reports_months_keyboard(available_months),
        parse_mode="HTML"
    )

@router.callback_query(F.data == "schedule_menu")
async def schedule_menu(callback: CallbackQuery):
    """Меню расписания - выбор месяца"""
    from database import Database
    
    db = Database()
    tutor = db.get_tutor_by_telegram_id(callback.from_user.id)
    
    if not tutor:
        await callback.answer("❌ Репетитор не найден")
        return
    
    schedule_service = ScheduleService()
    available_months = schedule_service.get_available_months(tutor[0])
    
    if not available_months:
        await callback.message.edit_text(
            "🗓️ <b>Расписание</b>\n\nНет данных для расписания",
            reply_markup=get_back_to_statistics_keyboard(),
            parse_mode="HTML"
        )
        return
    
    await callback.message.edit_text(
        "🗓️ <b>Расписание</b>\n\nВыберите месяц:",
        reply_markup=get_schedule_months_keyboard(available_months),
        parse_mode="HTML"
    )

@router.callback_query(F.data.startswith("report_month_"))
async def generate_monthly_report(callback: CallbackQuery):
    """Генерация отчета за выбранный месяц"""
    from database import Database
    
    # Разбираем callback_data: report_month_2024_12
    parts = callback.data.split("_")
    year = int(parts[2])
    month = int(parts[3])
    
    db = Database()
    tutor = db.get_tutor_by_telegram_id(callback.from_user.id)
    
    if not tutor:
        await callback.answer("❌ Репетитор не найден")
        return
    
    await callback.answer("📊 Генерируем отчет...")
    
    try:
        report_service = ReportService()
        pdf_generator = PDFReportGenerator()
        
        # Получаем данные отчета
        report_data = report_service.get_monthly_report_data(tutor[0], month, year)
        
        # Генерируем PDF
        pdf_buffer = pdf_generator.create_monthly_report(
            report_data['tutor'],
            report_data['lessons'],
            report_data['month'],
            report_data['year']
        )
        
        # Отправляем файл
        month_name = report_service._get_month_name(month)
        filename = f"отчет_{month_name}_{year}.pdf"
        
        await callback.message.answer_document(
            document=BufferedInputFile(
                pdf_buffer.getvalue(),
                filename=filename
            ),
            caption=f"📊 Отчет за {month_name} {year} года"
        )
        
    except Exception as e:
        print(f"Error generating report: {e}")
        await callback.message.answer("❌ Ошибка при создании отчета")

@router.callback_query(F.data.startswith("schedule_month_"))
async def generate_monthly_schedule(callback: CallbackQuery):
    """Генерация расписания за выбранный месяц"""
    from database import Database
    
    # Разбираем callback_data: schedule_month_2024_12
    parts = callback.data.split("_")
    year = int(parts[2])
    month = int(parts[3])
    
    db = Database()
    tutor = db.get_tutor_by_telegram_id(callback.from_user.id)
    
    if not tutor:
        await callback.answer("❌ Репетитор не найден")
        return
    
    await callback.answer("🗓️ Генерируем расписание...")
    
    try:
        schedule_service = ScheduleService()
        schedule_generator = SchedulePDFGenerator()
        
        # Получаем данные расписания
        schedule_data = schedule_service.get_monthly_schedule_data(tutor[0], month, year)
        
        # Генерируем PDF
        pdf_buffer = schedule_generator.create_monthly_schedule(
            schedule_data['tutor'],
            schedule_data
        )
        
        # Отправляем файл
        month_name = schedule_service._get_month_name(month)
        filename = f"расписание_{month_name}_{year}.pdf"
        
        await callback.message.answer_document(
            document=BufferedInputFile(
                pdf_buffer.getvalue(),
                filename=filename
            ),
            caption=f"🗓️ Расписание на {month_name} {year} года"
        )
        
    except Exception as e:
        print(f"Error generating schedule: {e}")
        await callback.message.answer("❌ Ошибка при создании расписания")

@router.callback_query(F.data == "main_menu")
async def back_to_main_menu(callback: CallbackQuery):
    """Возврат в главное меню"""
    await callback.answer()
    
    # Вызываем универсальную функцию для показа главного меню
    await show_main_menu(callback.from_user.id, callback_query=callback)

