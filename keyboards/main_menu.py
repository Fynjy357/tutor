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
            text="👥 Учет учеников",
            callback_data="students"
        ),
        types.InlineKeyboardButton(
            text="👨‍👩‍👧‍👦 Управление группами",
            callback_data="groups"
        )
    )
    
    # Третий ряд
    builder.row(
        types.InlineKeyboardButton(
            text="💰 Оплаты",
            callback_data="payments"
        ),
        types.InlineKeyboardButton(
            text="⚙️ Настройки",
            callback_data="settings"
        )
    )
    
    return builder.as_markup()

# Просто добавьте эти обработчики, оставив клавиатуру без изменений
@router.callback_query(F.data == "payments")
async def payments_stub(callback_query: types.CallbackQuery):
    await callback_query.answer("⏳ В разработке", show_alert=False)

@router.callback_query(F.data == "settings")
async def settings_stub(callback_query: types.CallbackQuery):
    await callback_query.answer("⏳ В разработке", show_alert=False)