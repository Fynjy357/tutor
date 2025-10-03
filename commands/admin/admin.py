from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command, CommandObject
from database import db

from commands.config import SUPER_ADMIN_ID

router = Router()

# ID супер-администратора (только он может назначать других админов)

@router.message(Command("make_admin"))
async def make_admin_command(message: Message, command: CommandObject):
    """Назначить пользователя администратором"""
    
    # ✅ Только супер-админ может использовать
    if message.from_user.id != SUPER_ADMIN_ID:
        await message.answer("❌ Только супер-администратор может использовать эту команду")
        return
    
    if not command.args:
        return await message.answer("❌ Использование: /make_admin user_id")
    
    target_user_id = command.args.strip()
    
    try:
        target_user_id = int(target_user_id)
    except ValueError:
        return await message.answer("❌ User ID должен быть числом")
    
    # Устанавливаем роль 'admin'
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'UPDATE tutors SET user_role = ? WHERE telegram_id = ?',
                ('admin', target_user_id)
            )
            conn.commit()
            
            if cursor.rowcount == 0:
                await message.answer(f"❌ Пользователь с ID {target_user_id} не найден")
            else:
                await message.answer(f"✅ Пользователь {target_user_id} теперь администратор!")
                
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")

@router.message(Command("make_user"))
async def make_user_command(message: Message, command: CommandObject):
    """Вернуть пользователя в обычную роль"""
    
    # ✅ Только супер-админ может использовать
    if message.from_user.id != SUPER_ADMIN_ID:
        await message.answer("❌ Только супер-администратор может использовать эту команду")
        return
    
    if not command.args:
        return await message.answer("❌ Использование: /make_user user_id")
    
    target_user_id = command.args.strip()
    
    try:
        target_user_id = int(target_user_id)
    except ValueError:
        return await message.answer("❌ User ID должен быть числом")
    
    # Устанавливаем роль 'user' (или другую стандартную роль)
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'UPDATE tutors SET user_role = ? WHERE telegram_id = ?',
                ('user', target_user_id)  # Или 'student', 'tutor' - в зависимости от вашей системы
            )
            conn.commit()
            
            if cursor.rowcount == 0:
                await message.answer(f"❌ Пользователь с ID {target_user_id} не найден")
            else:
                await message.answer(f"✅ Пользователь {target_user_id} теперь обычный пользователь!")
                
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")