# keyboards/main_menu.py
from aiogram import types
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram import types, F, Router
router = Router()


def get_main_menu_keyboard():
    builder = InlineKeyboardBuilder()
    
    # Первый ряд
    builder.row(
        types.InlineKeyboardButton(
            text="📅 Расписание занятий",
            callback_data="schedule"
        )
    )
    
    # Второй ряд
    builder.row(
        types.InlineKeyboardButton(
            text="👥 Мои ученики",
            callback_data="students"
        ),
        types.InlineKeyboardButton(
            text="👨‍👩‍👧‍👦 Список групп",
            callback_data="groups"
        )
    )
    
    # Третий ряд - добавлена кнопка Статистика
    builder.row(
        types.InlineKeyboardButton(
            text="📊 Отчеты",
            callback_data="statistics_menu"  # Ведет в меню отчетов
        ),
        types.InlineKeyboardButton(
            text="📞 Техподдержка",
            callback_data="contact_developers"
        )
    )
    
    # Четвертый ряд
    builder.row(
        types.InlineKeyboardButton(
            text="💎 Премиум",
            callback_data="settings"
        )
    )
    
    return builder.as_markup()

# Просто добавьте эти обработчики, оставив клавиатуру без изменений
@router.callback_query(F.data == "payments")
async def payments_stub(callback_query: types.CallbackQuery):
    await callback_query.answer("⏳ В разработке", show_alert=False)