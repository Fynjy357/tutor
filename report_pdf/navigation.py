# report_pdf/navigation.py
from aiogram import types, F, Router
from keyboards.main_menu import get_main_menu_keyboard
from .keyboards import get_reports_keyboard

# Создаем роутер для навигации отчетов
navigation_router = Router()

# Обработчик возврата в главное меню
@navigation_router.callback_query(F.data == "main_menu")
async def back_to_main_menu(callback_query: types.CallbackQuery):
    await callback_query.message.edit_text(
        "🏠 <b>Главное меню</b>",
        reply_markup=get_main_menu_keyboard(),
        parse_mode="HTML"
    )

# Обработчик для входа в меню отчетов
@navigation_router.callback_query(F.data == "report_menu")
async def show_reports_menu(callback_query: types.CallbackQuery):
    await callback_query.message.edit_text(
        "📊 <b>Генерация отчетов</b>\n\n"
        "Выберите тип отчета:",
        reply_markup=get_reports_keyboard(),
        parse_mode="HTML"
    )
