from aiogram import Router, types
from aiogram.filters import Command
from aiogram.types import Message
from database import db

from commands.config import SUPER_ADMIN_ID

router = Router()

@router.message(Command("last_users"))
async def get_last_registered_users(message: Message):
    # Проверяем, является ли пользователь суперадмином
    if message.from_user.id != SUPER_ADMIN_ID:
        await message.answer("❌ У вас нет прав для выполнения этой команды")
        return
    
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            # Получаем 50 последних зарегистрированных пользователей
            cursor.execute("""
                SELECT full_name, telegram_id, promo_code, registration_date, status, user_role 
                FROM tutors 
                ORDER BY registration_date DESC 
                LIMIT 50
            """)
            
            users = cursor.fetchall()
            
            if not users:
                await message.answer("❌ В базе нет зарегистрированных пользователей")
                return
            
            response = "📋 Последние 50 зарегистрированных пользователей:\n\n"
            
            for i, user in enumerate(users, 1):
                full_name, telegram_id, promo_code, registration_date, status, user_role = user
                
                # Форматируем дату
                if registration_date:
                    try:
                        if hasattr(registration_date, 'strftime'):
                            reg_date_str = registration_date.strftime('%d.%m.%Y %H:%M')
                        else:
                            reg_date_str = str(registration_date)
                    except:
                        reg_date_str = str(registration_date)
                else:
                    reg_date_str = "Не указана"
                
                # Обрабатываем возможные None значения
                full_name = full_name or "Не указано"
                telegram_id = telegram_id or "Не указан"
                promo_code = promo_code or "Не указан"
                status = status or "Не указан"
                user_role = user_role or "Не указан"
                
                response += (
                    f"{i}. 👤 {full_name}\n"
                    f"   🆔 TG ID: {telegram_id}\n"
                    f"   🎫 Промокод: {promo_code}\n"
                    f"   📅 Регистрация: {reg_date_str}\n"
                    f"   🏷️ Роль: {user_role}\n"
                    f"   📊 Статус: {status}\n"
                    f"   {'─' * 30}\n"
                )
            
            # Разбиваем сообщение на части, если оно слишком длинное
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
        await message.answer(f"❌ Ошибка при получении списка пользователей: {e}")
        print(f"Ошибка: {e}")