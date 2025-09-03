from aiogram import types
import logging
from database import db
from handlers.start.welcome import show_welcome_message

logger = logging.getLogger(__name__)

async def handle_deep_link(message: types.Message, deep_link_args: str):
    """Обработка deep link приглашений"""
    logger.info(f"Deep link: {deep_link_args} from user: {message.from_user.id}")
    
    # Обрабатываем пригласительные ссылки
    if deep_link_args.startswith(('student_', 'parent_')):
        await process_invitation_link(message, deep_link_args)
    else:
        logger.info("Неизвестный формат deep link")
        await show_welcome_message(message)

async def process_invitation_link(message: types.Message, deep_link_args: str):
    """Обработка пригласительной ссылки"""
    try:
        parts = deep_link_args.split('_', 1)
        if len(parts) < 2:
            await message.answer("❌ Неверная ссылка приглашения.")
            return
            
        invite_type, token = parts
        
        if invite_type not in ['student', 'parent']:
            await message.answer("❌ Неверная ссылка приглашения.")
            return
        
        # Находим ученика по токену
        student = db.get_student_by_token(token, invite_type)
        if not student:
            await message.answer("❌ Ссылка приглашения недействительна или устарела.")
            return
        
        # Привязываем Telegram аккаунт
        success, role, tutor_message = await link_telegram_account(
            message, student, invite_type
        )
        
        if success:
            await send_success_response(message, student, role)
            await notify_tutor(message, student, tutor_message)
        else:
            await send_error_response(message)
            
    except Exception as e:
        logger.error(f"Ошибка в обработке deep link: {e}")
        await message.answer("❌ Произошла ошибка при обработке приглашения.")

async def link_telegram_account(message: types.Message, student: dict, invite_type: str):
    """Привязка Telegram аккаунта к ученику"""
    username = f"@{message.from_user.username}" if message.from_user.username else "не указан"
    
    if invite_type == 'student':
        success = db.update_student_telegram_id(
            student['id'], message.from_user.id, username, 'student'
        )
        role = "ученика"
        tutor_message = f"✅ Ученик {student['full_name']} привязал свой Telegram аккаунт!"
    else:
        success = db.update_student_telegram_id(
            student['id'], message.from_user.id, username, 'parent'
        )
        role = "родителя"
        tutor_message = f"✅ Родитель ученика {student['full_name']} привязал свой Telegram аккаунт!"
    
    return success, role, tutor_message

async def send_success_response(message: types.Message, student: dict, role: str):
    """Отправка сообщения об успешной привязке"""
    await message.answer(
        f"✅ <b>Вы успешно привязаны как {role} ученика {student['full_name']}!</b>\n\n"
        f"Теперь вы будете получать уведомления о занятиях и успехах.",
        parse_mode="HTML"
    )

async def send_error_response(message: types.Message):
    """Отправка сообщения об ошибке"""
    await message.answer(
        "❌ <b>Ошибка при привязке аккаунта!</b>\n\n"
        "Пожалуйста, попробуйте позже или обратитесь к репетитору.",
        parse_mode="HTML"
    )

async def notify_tutor(message: types.Message, student: dict, tutor_message: str):
    """Уведомление репетитора"""
    try:
        tutor = db.get_tutor_by_id(student['tutor_id'])
        if tutor and tutor[1]:
            await message.bot.send_message(
                chat_id=tutor[1],
                text=tutor_message
            )
    except Exception as e:
        logger.error(f"Ошибка при отправке уведомления репетитору: {e}")