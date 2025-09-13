from aiogram import Router, types
from aiogram.filters import Command
from aiogram.types import Message
from database import db
from datetime import datetime
from commands.config import SUPER_ADMIN_ID

router = Router()

@router.message(Command("payments"))
async def admin_payments_info(message: Message):
    # Проверяем, является ли пользователь суперадмином
    if message.from_user.id != SUPER_ADMIN_ID:
        await message.answer("❌ У вас нет прав для выполнения этой команды")
        return
    
    # Получаем аргументы после команды
    args = message.text.split()[1:] if message.text and len(message.text.split()) > 1 else []
    
    if len(args) < 1:
        await message.answer("❌ Укажите месяц и год: /payments <месяц><год>")
        await message.answer("📝 Примеры:\n• /payments 0925 (сентябрь 2025)\n• /payments 925 (сентябрь 2025)")
        return
    
    month_year = args[0]
    
    # Проверяем формат месяца и года (MMYY или MYY)
    if len(month_year) not in [3, 4]:
        await message.answer("❌ Неверный формат. Используйте: <месяц><год> (например: 0925 или 925)")
        await message.answer("📝 Год указывается двумя последними цифрами: 25 = 2025")
        return
    
    # Извлекаем месяц и год
    if len(month_year) == 3:  # Формат MYY (например: 925)
        month = month_year[0].zfill(2)  # '9' → '09'
        year_short = month_year[1:3]    # '25'
    else:  # Формат MMYY (например: 0925)
        month = month_year[0:2]         # '09'
        year_short = month_year[2:4]    # '25'
    
    # Преобразуем короткий год в полный (25 → 2025)
    try:
        year = f"20{year_short}"  # Предполагаем 21 век
        if not (23 <= int(year_short) <= 99):  # Проверяем диапазон 2023-2099
            year = f"19{year_short}"  # Для годов до 2000
    except:
        await message.answer("❌ Неверный формат года")
        return
    
    # Проверяем валидность месяца
    if not month.isdigit() or not (1 <= int(month) <= 12):
        await message.answer("❌ Месяц должен быть от 01 до 12")
        return
    
    # Проверяем валидность года
    if not year.isdigit() or not (1900 <= int(year) <= 2100):
        await message.answer("❌ Год должен быть от 1900 до 2100")
        return
    
    await show_all_payments(message, month, year)

async def show_all_payments(message: Message, month: str, year: str):
    """Показать все платежи за указанный месяц и год"""
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            # Получаем название месяца
            month_names = {
                '01': 'Январь', '02': 'Февраль', '03': 'Март', '04': 'Апрель',
                '05': 'Май', '06': 'Июнь', '07': 'Июль', '08': 'Август',
                '09': 'Сентябрь', '10': 'Октябрь', '11': 'Ноябрь', '12': 'Декабрь'
            }
            month_name = month_names.get(month, f"Месяц {month}")
            
            # Получаем все успешные платежи за указанный месяц и год
            cursor.execute("""
                SELECT p.id, p.user_id, t.full_name, p.payment_id, 
                       p.tariff_name, p.amount, p.created_at, p.valid_until
                FROM payments p
                LEFT JOIN tutors t ON t.telegram_id = p.user_id
                WHERE p.status = 'succeeded'
                AND strftime('%m', p.created_at) = ?
                AND strftime('%Y', p.created_at) = ?
                ORDER BY p.created_at DESC
            """, (month.zfill(2), year))
            
            payments = cursor.fetchall()
            
            # Получаем статистику
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_payments,
                    SUM(p.amount) as total_amount,
                    COUNT(DISTINCT p.user_id) as unique_users
                FROM payments p
                WHERE p.status = 'succeeded'
                AND strftime('%m', p.created_at) = ?
                AND strftime('%Y', p.created_at) = ?
            """, (month.zfill(2), year))
            
            stats = cursor.fetchone()
            total_payments, total_amount, unique_users = stats if stats else (0, 0, 0)
            
            if not payments:
                response = (
                    f"💳 Отчет по платежам за {month_name} {year} года\n\n"
                    f"📊 Статистика:\n"
                    f"• Всего платежей: 0\n"
                    f"• Уникальных пользователей: 0\n"
                    f"• Общая сумма: 0 руб.\n\n"
                    f"❌ Платежей не найдено"
                )
            else:
                response = (
                    f"💳 Отчет по платежам за {month_name} {year} года\n\n"
                    f"📊 Статистика:\n"
                    f"• Всего платежей: {total_payments}\n"
                    f"• Уникальных пользователей: {unique_users}\n"
                    f"• Общая сумма: {total_amount:.2f} руб.\n\n"
                    f"📋 Список платежей:\n\n"
                )
                
                for i, payment in enumerate(payments, 1):
                    payment_id, user_id, full_name, payment_system_id, tariff_name, amount, created_at, valid_until = payment
                    
                    # Форматируем даты
                    try:
                        payment_date = datetime.strptime(created_at, '%Y-%m-%d %H:%M:%S').strftime('%d.%m.%Y %H:%M')
                    except:
                        payment_date = str(created_at)
                    
                    try:
                        if valid_until:
                            valid_date = datetime.strptime(valid_until, '%Y-%m-%d %H:%M:%S').strftime('%d.%m.%Y')
                        else:
                            valid_date = "Не указано"
                    except:
                        valid_date = str(valid_until)
                    
                    # Обрабатываем возможные None значения
                    full_name = full_name or "Неизвестно"
                    user_id = user_id or "Неизвестен"
                    
                    response += (
                        f"{i}. 💰 {amount:.2f} руб. - {tariff_name}\n"
                        f"   👤 {full_name} (ID: {user_id})\n"
                        f"   📅 Оплата: {payment_date}\n"
                        f"   🎫 ID платежа: {payment_system_id}\n"
                        f"   📆 Действует до: {valid_date}\n"
                        f"   {'─' * 30}\n"
                    )
                
                # Если платежей много, разбиваем на части
                if len(response) > 4000:
                    parts = [response[i:i+4000] for i in range(0, len(response), 4000)]
                    for part in parts:
                        await message.answer(part)
                        # Небольшая задержка между сообщениями
                        import asyncio
                        await asyncio.sleep(0.5)
                else:
                    await message.answer(response)
            
    except Exception as e:
        await message.answer(f"❌ Ошибка при получении списка платежей: {e}")
        print(f"Ошибка: {e}")

# Дополнительная команда для быстрой статистики
@router.message(Command("payments_stats"))
async def payments_stats(message: Message):
    """Быстрая статистика по платежам за текущий месяц"""
    if message.from_user.id != SUPER_ADMIN_ID:
        await message.answer("❌ У вас нет прав для выполнения этой команды")
        return
    
    try:
        current_month = datetime.now().strftime('%m')
        current_year = datetime.now().strftime('%Y')
        
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_payments,
                    SUM(amount) as total_amount,
                    COUNT(DISTINCT user_id) as unique_users
                FROM payments 
                WHERE status = 'succeeded'
                AND strftime('%m', created_at) = ?
                AND strftime('%Y', created_at) = ?
            """, (current_month, current_year))
            
            stats = cursor.fetchone()
            
            if stats:
                total_payments, total_amount, unique_users = stats
                month_names = {
                    '01': 'Январь', '02': 'Февраль', '03': 'Март', '04': 'Апрель',
                    '05': 'Май', '06': 'Июнь', '07': 'Июль', '08': 'Август',
                    '09': 'Сентябрь', '10': 'Октябрь', '11': 'Ноябрь', '12': 'Декабрь'
                }
                month_name = month_names.get(current_month, f"Месяц {current_month}")
                
                await message.answer(
                    f"📊 Статистика за {month_name} {current_year}:\n\n"
                    f"• Всего платежей: {total_payments or 0}\n"
                    f"• Уникальных пользователей: {unique_users or 0}\n"
                    f"• Общая сумма: {total_amount or 0:.2f} руб."
                )
            else:
                await message.answer("❌ Нет данных за текущий месяц")
                
    except Exception as e:
        await message.answer(f"❌ Ошибка при получении статистики: {e}")