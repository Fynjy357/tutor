from aiogram import Router, types
from aiogram.filters import Command
from aiogram.types import Message
from commands.config import SUPER_ADMIN_ID

router = Router()

@router.message(Command("help_admin"))
async def admin_help_command(message: Message):
    """Справочник команд для суперадмина"""
    # Проверяем, является ли пользователь суперадмином
    if message.from_user.id != SUPER_ADMIN_ID:
        await message.answer("❌ У вас нет прав для просмотра этой информации")
        return
    
    # Формируем справочник команд
    help_text = (
        "🔧 <b>СПРАВОЧНИК КОМАНД ДЛЯ СУПЕРАДМИНА</b>\n\n"
        
        "👥 <b>Управление пользователями:</b>\n"
        
        "• <code>/broadcast</code> - написать всем репетиторам\n"
        "• <code>/send_message</code> - написать пользователю по id\n"
        "• <code>/last_users</code> - посмотреть 50 последних репетиторов\n"
        "• <code>/take_user 111</code> - сделать пользователя user\n"
        "• <code>/take_admin 111 </code> - сделать пользователя admin\n"

        
        "💰 <b>Платежи и финансы:</b>\n"
        "• <code>/payments MMYY</code> - посмотреть все платежи\n"
        
        "📊 <b>Рефералы и системное:</b>\n"
        "• <code>/ref 111</code> - посмотреть всех рефералов пользователя\n"
        "• <code>/ref_pay 111 MMYY</code> - посмотреть всех, кто оплачивал в указанном месяце\n"
        "• <code>/mailing_help</code> - управление рассылками подписки\n"

        
        "⚙️ <b>Системные команды:</b>\n"
        "• <code>/broadcast Привет всем!</code> - рассылка сообщения\n"
        "• <code>/logs</code> - Последние 50 строк логов (по умолчанию)\n"
        "• <code>/logs xx</code> - Последние xx строк логов\n"
        "• <code>/logs_search error</code> - Поиск строк с ошибками, можно другое\n"
        "• <code>/logs_info</code> - Информация о файле логов\n"

        "• <code>/backup</code> - Полный бэкап (база + логи + конфиги)\n"
        "• <code>/backup db </code> - Бэкап только база данных\n"
        "• <code>/backup logs</code> - Бэкап только логов\n"
        "• <code>/backups_list</code> - Список всех бэкапов\n"
        "• <code>/db_status</code> - Проверка состояния базы\n"
        
        
        "• <code>/system_help</code> - информация о системе\n\n"
        
        "❓ <b>Справка:</b>\n"
        "• <code>/help_admin</code> - эта справка\n\n"
        
        "📝 <b>Формат дат:</b>\n"
        "• Месяцы: 01-12 (01=Январь, 09=Сентябрь и т.д.)\n"
        "• ID пользователя: числовой Telegram ID\n"
        "• ID платежа: строка (например, PAY_12345)\n\n"
        
        "⚠️ <b>Внимание:</b> Все команды доступны только суперадминам!"
    )
    
    await message.answer(help_text, parse_mode='HTML')

# Дополнительная функция для быстрого доступа к форматам
@router.message(Command("formats"))
async def admin_formats_command(message: Message):
    """Быстрая справка по форматам"""
    # Проверяем, является ли пользователь суперадмином
    if message.from_user.id != SUPER_ADMIN_ID:
        await message.answer("❌ У вас нет прав для просмотра этой информации")
        return
    
    formats_text = (
        "📋 <b>БЫСТРАЯ СПРАВКА ПО ФОРМАТАМ</b>\n\n"
        
        "👤 <b>ID пользователя:</b>\n"
        "<code>123456789</code> - числовой Telegram ID\n\n"
        
        "📅 <b>Месяцы:</b>\n"
        "• <code>01</code> - Январь\n"
        "• <code>02</code> - Февраль\n"
        "• <code>03</code> - Март\n"
        "• <code>04</code> - Апрель\n"
        "• <code>05</code> - Май\n"
        "• <code>06</code> - Июнь\n"
        "• <code>07</code> - Июль\n"
        "• <code>08</code> - Август\n"
        "• <code>09</code> - Сентябрь\n"
        "• <code>10</code> - Октябрь\n"
        "• <code>11</code> - Ноябрь\n"
        "• <code>12</code> - Декабрь\n\n"
        
        "💰 <b>Роли пользователей:</b>\n"
        "• <code>user</code> - обычный пользователь\n"
        "• <code>admin</code> - администратор\n"
        "• <code>superadmin</code> - суперадмин\n\n"
        
        "📊 <b>Статусы платежей:</b>\n"
        "• <code>pending</code> - ожидание\n"
        "• <code>succeeded</code> - успешно\n"
        "• <code>failed</code> - ошибка\n"
        "• <code>refunded</code> - возврат\n\n"
        
        "🔗 <b>Статусы рефералов:</b>\n"
        "• <code>awaiting</code> - ожидание регистрации\n"
        "• <code>active</code> - активен\n"
        "• <code>inactive</code> - неактивен"
    )
    
    await message.answer(formats_text, parse_mode='HTML')