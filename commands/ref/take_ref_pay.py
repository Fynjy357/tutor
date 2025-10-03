from aiogram import Router, types
from aiogram.filters import Command
from aiogram.types import Message
from database import db

from datetime import datetime
from commands.config import SUPER_ADMIN_ID

router = Router()

@router.message(Command("ref_pay"))
async def admin_paid_referrals_info(message: Message):
    # Проверяем, является ли пользователь суперадмином
    if message.from_user.id != SUPER_ADMIN_ID:
        await message.answer("❌ У вас нет прав для выполнения этой команды")
        return
    
    # Получаем аргументы после команды
    args = message.text.split()[1:] if message.text and len(message.text.split()) > 1 else []
    
    if len(args) < 2:
        await message.answer("❌ Укажите Telegram ID репетитора, месяц и год: /ref_pay <telegram_id> <месяц><год>")
        await message.answer("📝 Примеры:\n• /ref_pay 123456789 0925 (сентябрь 2025)\n• /ref_pay 123456789 925 (сентябрь 2025)")
        return
    
    telegram_id = args[0]
    month_year = args[1]
    
    if not telegram_id.isdigit():
        await message.answer("❌ Telegram ID должен быть числом")
        return
    
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
    
    await show_paid_referrals(message, telegram_id, month, year)

async def show_paid_referrals(message: Message, telegram_id: str, month: str, year: str):
    """Показать оплаченные рефералы за указанный месяц и год"""
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            # Находим репетитора по telegram_id
            cursor.execute(
                "SELECT id, full_name, phone FROM tutors WHERE telegram_id = ?", 
                (int(telegram_id),)
            )
            tutor_data = cursor.fetchone()
            
            if not tutor_data:
                await message.answer("❌ Репетитор с таким Telegram ID не найден")
                return
            
            tutor_id, tutor_name, tutor_phone = tutor_data
            
            # Получаем название месяца
            month_names = {
                '01': 'Январь', '02': 'Февраль', '03': 'Март', '04': 'Апрель',
                '05': 'Май', '06': 'Июнь', '07': 'Июль', '08': 'Август',
                '09': 'Сентябрь', '10': 'Октябрь', '11': 'Ноябрь', '12': 'Декабрь'
            }
            month_name = month_names.get(month, f"Месяц {month}")
            
            # Ищем оплаченные рефералы за указанный месяц и год
            cursor.execute("""
                SELECT t.full_name, p.created_at, p.tariff_name, p.amount, 
                       r.visitor_telegram_id
                FROM referrals r
                JOIN tutors t ON t.telegram_id = r.visitor_telegram_id
                JOIN payments p ON p.user_id = r.visitor_telegram_id
                WHERE r.referrer_id = ? 
                AND r.status = 'active'
                AND p.status = 'succeeded'
                AND strftime('%m', p.created_at) = ?
                AND strftime('%Y', p.created_at) = ?
                ORDER BY p.created_at DESC
            """, (tutor_id, month.zfill(2), year))
            
            paid_referrals = cursor.fetchall()
            
            if not paid_referrals:
                response = (
                    f"📊 Отчет за {month_name} {year} года\n"
                    f"👤 Репетитор: {tutor_name}\n"
                    f"🆔 Telegram ID: {telegram_id}\n"
                    f"📞 Телефон: {tutor_phone}\n"
                    f"🏷️ ID в системе: {tutor_id}\n\n"
                    f"❌ Рефералов оплатило подписку: 0"
                )
            else:
                total_amount = 0
                response = (
                    f"📊 Отчет за {month_name} {year} года\n"
                    f"👤 Репетитор: {tutor_name}\n"
                    f"🆔 Telegram ID: {telegram_id}\n"
                    f"📞 Телефон: {tutor_phone}\n"
                    f"🏷️ ID в системе: {tutor_id}\n\n"
                    f"✅ Рефералов оплатило подписку: {len(paid_referrals)}\n\n"
                )
                
                for i, referral in enumerate(paid_referrals, 1):
                    full_name, created_at, tariff_name, amount, visitor_tg_id = referral
                    
                    # Добавляем к общей сумме
                    total_amount += amount
                    
                    # Форматируем дату в русский формат
                    try:
                        payment_date = datetime.strptime(created_at, '%Y-%m-%d %H:%M:%S').strftime('%d.%m.%Y %H:%M')
                    except:
                        payment_date = str(created_at)
                    
                    response += (
                        f"{i}. 👤 {full_name}\n"
                        f"   📅 Оплата: {payment_date}\n"
                        f"   📦 Тариф: {tariff_name}\n"
                        f"   💰 Сумма: {amount} руб.\n"
                        f"   🆔 TG ID: {visitor_tg_id}\n"
                        f"   {'─' * 25}\n"
                    )
                
                # Добавляем итоговую строку
                response += f"\n💰 ИТОГО: {total_amount} руб."
            
            await message.answer(response)
            
    except Exception as e:
        await message.answer(f"❌ Ошибка при проверке оплаченных рефералов: {e}")
        print(f"Ошибка: {e}")