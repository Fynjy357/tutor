from aiogram import Router, types
from aiogram.filters import Command
from aiogram.types import Message
from database import db

from commands.config import SUPER_ADMIN_ID

router = Router()

async def send_long_message(message: Message, text: str, max_length: int = 4096):
    """Разбивает длинное сообщение на части и отправляет"""
    if len(text) <= max_length:
        await message.answer(text)
        return
    
    # Разбиваем текст на части
    parts = []
    while text:
        if len(text) <= max_length:
            parts.append(text)
            break
        
        # Ищем последний перенос строки перед лимитом
        split_pos = text.rfind('\n', 0, max_length)
        if split_pos == -1:
            # Если переносов нет, разбиваем по границе слова
            split_pos = text.rfind(' ', 0, max_length)
            if split_pos == -1:
                # Если и пробелов нет, просто обрезаем
                split_pos = max_length
        
        parts.append(text[:split_pos])
        text = text[split_pos:].lstrip()
    
    # Отправляем части
    for i, part in enumerate(parts, 1):
        if len(parts) > 1:
            part = f"📄 Часть {i}/{len(parts)}\n\n{part}"
        await message.answer(part)

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
                await message.answer(response)
            else:
                # Заголовок сообщения
                header = (
                    f"📊 Рефералы репетитора: {tutor_name}\n"
                    f"👤 Telegram ID: {telegram_id}\n"
                    f"📞 Телефон: {tutor_phone}\n"
                    f"🆔 ID в системе: {tutor_id}\n\n"
                    f"✅ Активных рефералов: {len(referrals)}\n\n"
                )
                
                # Формируем список рефералов
                referrals_text = ""
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
                    
                    referral_info = (
                        f"{i}. ФИО: {invited_name}\n"
                        f"   📞 Телефон: {invited_phone}\n"
                        f"   🔗 Реферальный код: {code}\n"
                        f"   📅 Дата перехода: {visited_at}\n"
                        f"   ---\n"
                    )
                    
                    # Проверяем, не превысит ли добавление этого реферала лимит
                    if len(header + referrals_text + referral_info) > 4000:
                        # Отправляем текущую часть
                        await send_long_message(message, header + referrals_text)
                        # Начинаем новую часть
                        referrals_text = referral_info
                        header = f"📊 Рефералы репетитора: {tutor_name} (продолжение)\n\n"
                    else:
                        referrals_text += referral_info
                
                # Отправляем оставшуюся часть
                if referrals_text:
                    await send_long_message(message, header + referrals_text)
            
    except Exception as e:
        await message.answer(f"❌ Ошибка при проверке рефералов: {e}")
        print(f"Ошибка: {e}")
