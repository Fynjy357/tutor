from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
import pytz
from datetime import datetime

# Создаем роутер для команд времени
time_router = Router()

@time_router.message(Command("mytime"))
async def my_time_command(message: Message):
    """Команда для проверки локального времени пользователя (только РФ)"""
    
    # Получаем информацию о пользователе
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name
    
    # Создаем клавиатуру с часовыми поясами РФ
    builder = InlineKeyboardBuilder()
    
    # Часовые пояса России
    russian_timezones = [
        ("🇷🇺 Калининград (UTC+2)", "Europe/Kaliningrad"),
        ("🇷🇺 Москва (UTC+3)", "Europe/Moscow"),
        ("🇷🇺 Самара (UTC+4)", "Europe/Samara"),
        ("🇷🇺 Екатеринбург (UTC+5)", "Asia/Yekaterinburg"),
        ("🇷🇺 Омск (UTC+6)", "Asia/Omsk"),
        ("🇷🇺 Красноярск (UTC+7)", "Asia/Krasnoyarsk"),
        ("🇷🇺 Иркутск (UTC+8)", "Asia/Irkutsk"),
        ("🇷🇺 Якутск (UTC+9)", "Asia/Yakutsk"),
        ("🇷🇺 Владивосток (UTC+10)", "Asia/Vladivostok"),
        ("🇷🇺 Магадан (UTC+11)", "Asia/Magadan"),
        ("🇷🇺 Камчатка (UTC+12)", "Asia/Kamchatka")
    ]
    
    # Добавляем кнопки (по 1 в ряд для удобства)
    for tz_name, tz_code in russian_timezones:
        builder.button(text=tz_name, callback_data=f"show_tz:{tz_code}")
    
    builder.adjust(1)  # 1 кнопка в ряд
    
    await message.answer(
        f"👋 Привет, {username}!\n\n"
        "🕐 **Проверка локального времени (Россия)**\n\n"
        "Выберите ваш часовой пояс:",
        reply_markup=builder.as_markup()
    )

@time_router.callback_query(F.data.startswith("show_tz:"))
async def show_timezone_time(callback: CallbackQuery):
    """Показывает время в выбранном часовом поясе"""
    
    # Извлекаем часовой пояс из callback_data
    timezone_code = callback.data.split(":")[1]
    
    try:
        # Получаем текущее время в указанном часовом поясе
        tz = pytz.timezone(timezone_code)
        local_time = datetime.now(tz)
        
        # Форматируем время
        time_str = local_time.strftime("%d.%m.%Y %H:%M:%S")
        timezone_name = timezone_code.split("/")[1]  # Берем только название города
        
        # Отправляем результат
        await callback.message.edit_text(
            f"🕐 **Время в {timezone_name}:**\n"
            f"📅 **{time_str}**\n"
            f"🌍 **Часовой пояс:** {timezone_code}\n\n"
            "Для повторной проверки используйте команду /mytime"
        )
        
    except Exception as e:
        await callback.message.edit_text(
            f"❌ Ошибка при получении времени: {e}\n"
            "Попробуйте снова: /mytime"
        )
    
    await callback.answer()

# Дополнительная команда для быстрой проверки текущего времени в Москве
@time_router.message(Command("moscow_time"))
async def moscow_time_command(message: Message):
    """Быстрая проверка времени в Москве"""
    
    moscow_tz = pytz.timezone("Europe/Moscow")
    moscow_time = datetime.now(moscow_tz)
    
    time_str = moscow_time.strftime("%d.%m.%Y %H:%M:%S")
    
    await message.answer(
        f"🇷🇺 **Текущее время в Москве:**\n"
        f"📅 **{time_str}**\n"
        f"🌍 Часовой пояс: Europe/Moscow (UTC+3)\n\n"
        f"Для других городов используйте /mytime"
    )
