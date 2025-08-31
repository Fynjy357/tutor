from aiogram import Router, types
from aiogram.filters import Command

from keyboards.registration import get_registration_keyboard
from keyboards.main_menu import get_main_menu_keyboard  # Импортируем новое меню
from database import db

router = Router()

@router.message(Command("start"))
async def cmd_start(message: types.Message):
    # Проверяем, зарегистрирован ли пользователь
    existing_tutor = db.get_tutor_by_telegram_id(message.from_user.id)
    
    if existing_tutor:
        # Если пользователь уже зарегистрирован, показываем приветственное сообщение с главным меню
        welcome_text = f"""
<b>Добро пожаловать назад, {existing_tutor[2]}!</b>

Рады снова видеть вас в ежедневнике репетитора.

Ваши данные:
📝 ФИО: {existing_tutor[2]}
📞 Телефон: {existing_tutor[3]}
🎫 Промокод: {existing_tutor[4] if existing_tutor[4] != '0' else 'не указан'}

Выберите нужный раздел:
"""
        await message.answer(
            welcome_text,
            reply_markup=get_main_menu_keyboard(),
            parse_mode="HTML"
        )
    else:
        # Если пользователь не зарегистрирован, показываем стандартное приветствие
        welcome_text = """
<b>Ежедневник репетитора</b>

Привет! Этот бот для репетиторов

🔲 Зарегистрироваться в боте
✅ Написать сообщение...
"""
        
        await message.answer(
            welcome_text,
            reply_markup=get_registration_keyboard(),
            parse_mode="HTML"
        )

# Добавим обработчики для кнопок (пустые, без функционала)
@router.callback_query(lambda c: c.data in ["schedule", "students", "groups", "payments", "settings"])
async def process_main_menu(callback_query: types.CallbackQuery):
    await callback_query.answer()
    
    # Временные ответы на нажатие кнопок
    menu_responses = {
        "schedule": "Раздел 'Расписание занятий' находится в разработке.",
        "students": "Раздел 'Учет учеников' находится в разработке.",
        "groups": "Раздел 'Управление группами' находится в разработке.",
        "payments": "Раздел 'Оплаты' находится в разработке.",
        "settings": "Раздел 'Настройки' находится в разработке."
    }
    
    await callback_query.message.answer(menu_responses[callback_query.data])