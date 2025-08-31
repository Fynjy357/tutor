# handlers/about.py
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.exceptions import TelegramBadRequest

from keyboards.about import get_about_keyboard
from keyboards.registration import get_registration_keyboard

router = Router()

# Обработчик команды /about
@router.message(Command("about"))
async def cmd_about(message: types.Message):
    about_text = """
🤖 <b>Ежедневник репетитора</b>

Этот бот поможет вам:
• Управлять расписанием занятий
• Вести учет учеников и групп
• Отслеживать оплаты и статистику
• Получать уведомления о предстоящих занятиях

Для начала работы необходимо зарегистрироваться.
"""
    await message.answer(
        about_text,
        reply_markup=get_about_keyboard(),
        parse_mode="HTML"
    )

# Обработчик нажатия на кнопку "О боте"
@router.callback_query(F.data == "about_bot")
async def about_bot(callback_query: types.CallbackQuery):
    await callback_query.answer()
    about_text = """
🤖 <b>Ежедневник репетитора</b>

Этот бот поможет вам:
• Управлять расписанием занятий
• Вести учет учеников и групп
• Отслеживать оплаты и статистику
• Получать уведомления о предстоящих занятиях

Для начала работы необходимо зарегистрироваться.
"""
    try:
        await callback_query.message.edit_text(
            about_text,
            reply_markup=get_about_keyboard(),
            parse_mode="HTML"
        )
    except TelegramBadRequest:
        # Если сообщение уже удалено, отправляем новое
        await callback_query.message.answer(
            about_text,
            reply_markup=get_about_keyboard(),
            parse_mode="HTML"
        )

# Обработчик нажатия на кнопку "Назад"
@router.callback_query(F.data == "back_to_main")
async def back_to_main(callback_query: types.CallbackQuery):
    await callback_query.answer()
    welcome_text = """
<b>Ежедневник репетитора</b>

Привет! Этот бот для репетиторов

🔲 Зарегистрироваться в боте
✅ Написать сообщение...
    """
    
    try:
        await callback_query.message.edit_text(
            welcome_text,
            reply_markup=get_registration_keyboard(),
            parse_mode="HTML"
        )
    except TelegramBadRequest:
        # Если сообщение уже удалено, отправляем новое
        await callback_query.message.answer(
            welcome_text,
            reply_markup=get_registration_keyboard(),
            parse_mode="HTML"
        )