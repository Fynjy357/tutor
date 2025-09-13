from aiogram import Router, types
from aiogram.filters import Command
from aiogram.types import Message
from database import db
from commands.config import SUPER_ADMIN_ID

router = Router()

@router.message(Command("ref"))
async def admin_referral_info(message: Message):
    # Проверяем, является ли пользователь суперадмином
    if message.from_user.id != SUPER_ADMIN_ID:
        await message.answer("❌ У вас нет прав для выполнения этой команды")
        return
    
    # Получаем аргументы после команды
    if message.text and len(message.text.split()) > 1:
        args = message.text.split()[1:]
        telegram_id = args[0] if args else None
    else:
        await message.answer("❌ Укажите Telegram ID репетитора: /ref <telegram_id>")
        return
    
    if not telegram_id.isdigit():
        await message.answer("❌ Telegram ID должен быть числом")
        return
    
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            # 1. Находим репетитора по telegram_id
            cursor.execute(
                "SELECT id, full_name, phone FROM tutors WHERE telegram_id = ?", 
                (int(telegram_id),)
            )
            tutor_data = cursor.fetchone()
            
            if not tutor_data:
                await message.answer("❌ Репетитор с таким Telegram ID не найден")
                return
            
            tutor_id, tutor_name, tutor_phone = tutor_data
            
            # 2. Ищем всех активных рефералов этого репетитора
            cursor.execute("""
                SELECT r.id, r.referral_code, r.visited_at, r.status, 
                       r.visitor_telegram_id
                FROM referrals r
                WHERE r.referrer_id = ? AND r.status = 'active'
                ORDER BY r.visited_at DESC
            """, (tutor_id,))
            
            referrals = cursor.fetchall()
            
            if not referrals:
                response = (
                    f"📊 Рефералы репетитора: {tutor_name}\n"
                    f"👤 Telegram ID: {telegram_id}\n"
                    f"📞 Телефон: {tutor_phone}\n"
                    f"🆔 ID в системе: {tutor_id}\n\n"
                    f"❌ Активных рефералов не найдено"
                )
            else:
                response = (
                    f"📊 Рефералы репетитора: {tutor_name}\n"
                    f"👤 Telegram ID: {telegram_id}\n"
                    f"📞 Телефон: {tutor_phone}\n"
                    f"🆔 ID в системе: {tutor_id}\n\n"
                    f"✅ Активных рефералов: {len(referrals)}\n\n"
                )
                
                for i, ref in enumerate(referrals, 1):
                    ref_id, code, visited_at, status, visitor_tg_id = ref
                    
                    # Ищем информацию о приглашенном пользователе
                    cursor.execute(
                        "SELECT full_name, phone FROM tutors WHERE telegram_id = ?",
                        (visitor_tg_id,)
                    )
                    invited_tutor = cursor.fetchone()
                    
                    if invited_tutor:
                        invited_name, invited_phone = invited_tutor
                    else:
                        invited_name = "Не зарегистрирован"
                        invited_phone = "Нет данных"
                    
                    response += (
                        f"{i}. ФИО: {invited_name}\n"
                        f"   📞 Телефон: {invited_phone}\n"
                        f"   🔗 Реферальный код: {code}\n"
                        f"   📅 Дата перехода: {visited_at}\n"
                        f"   ---\n"
                    )
            
            await message.answer(response)
            
    except Exception as e:
        await message.answer(f"❌ Ошибка при проверке рефералов: {e}")
        print(f"Ошибка: {e}")