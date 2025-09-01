# handlers/invitations.py
from aiogram import Router, types, F
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.exceptions import TelegramBadRequest
import logging

from database import db
from handlers.start import cmd_start
from keyboards.students import get_students_menu_keyboard

router = Router()
logger = logging.getLogger(__name__)

def get_invite_keyboard(student_id):
    """Создает клавиатуру для меню приглашений"""
    keyboard = [
        [InlineKeyboardButton(text="👤 Пригласить ученика", callback_data=f"invite_student_{student_id}")],
        [InlineKeyboardButton(text="👨‍👩‍👧‍👦 Пригласить родителя", callback_data=f"invite_parent_{student_id}")],
        [InlineKeyboardButton(text="◀️ Назад к ученику", callback_data=f"back_to_student_{student_id}")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

@router.callback_query(F.data.startswith("invite_student_"))
async def invite_student(callback_query: types.CallbackQuery):
    await callback_query.answer()
    student_id = int(callback_query.data.split("_")[2])
    
    student = db.get_student_by_id(student_id)
    if not student:
        await callback_query.message.edit_text("❌ Ученик не найден!")
        return
    
    # Генерируем токен, если его нет
    if not student.get('student_token'):
        token = db.generate_invite_token()
        success = db.update_student_token(student_id, token, 'student')
        if not success:
            await callback_query.message.edit_text("❌ Ошибка при генерации токена!")
            return
    else:
        token = student['student_token']
    
    # Создаем ссылку для приглашения
    bot_username = (await callback_query.bot.get_me()).username
    invite_link = f"https://t.me/{bot_username}?start=student_{token}"
    
    await callback_query.message.edit_text(
        f"👤 <b>Приглашение для ученика</b>\n\n"
        f"Ученик: {student['full_name']}\n\n"
        f"Отправьте эту ссылку ученику:\n"
        f"<code>{invite_link}</code>\n\n"
        f"Ученик сможет привязать свой Telegram аккаунт к вашей базе.",
        parse_mode="HTML",
        reply_markup=get_invite_keyboard(student_id)
    )

@router.callback_query(F.data.startswith("invite_parent_"))
async def invite_parent(callback_query: types.CallbackQuery):
    await callback_query.answer()
    student_id = int(callback_query.data.split("_")[2])
    
    student = db.get_student_by_id(student_id)
    if not student:
        await callback_query.message.edit_text("❌ Ученик не найден!")
        return
    
    # Генерируем токен, если его нет
    if not student.get('parent_token'):
        token = db.generate_invite_token()
        success = db.update_student_token(student_id, token, 'parent')
        if not success:
            await callback_query.message.edit_text("❌ Ошибка при генерации токена!")
            return
    else:
        token = student['parent_token']
    
    # Создаем ссылку для приглашения
    bot_username = (await callback_query.bot.get_me()).username
    invite_link = f"https://t.me/{bot_username}?start=parent_{token}"
    
    await callback_query.message.edit_text(
        f"👨‍👩‍👧‍👦 <b>Приглашение для родителя</b>\n\n"
        f"Ученик: {student['full_name']}\n\n"
        f"Отправьте эту ссылку родителю:\n"
        f"<code>{invite_link}</code>\n\n"
        f"Родитель сможет привязать свой Telegram аккаунт к вашей базе.",
        parse_mode="HTML",
        reply_markup=get_invite_keyboard(student_id)
    )

@router.message(CommandStart(deep_link=True))
async def handle_deep_link(message: types.Message):
    # Извлекаем аргументы из deep link - используем правильное свойство
    args = message.text.split()[1] if len(message.text.split()) > 1 else None
    
    if not args:
        # Если нет аргументов, выполняем стандартный старт
        await cmd_start(message)
        return
    
    # Обрабатываем пригласительные ссылки
    if args.startswith('student_') or args.startswith('parent_'):
        invite_type, token = args.split('_', 1)
        
        if invite_type not in ['student', 'parent']:
            await message.answer("❌ Неверная ссылка приглашения.")
            return
        
        # Находим ученика по токену
        student = db.get_student_by_token(token, invite_type)
        if not student:
            await message.answer("❌ Ссылка приглашения недействительна или устарела.")
            return
        
        # Получаем username пользователя
        username = message.from_user.username
        if username:
            username = f"@{username}"
        else:
            username = "не указан"
        
        # Привязываем Telegram аккаунт к ученику
        if invite_type == 'student':
            success = db.update_student_telegram_id(
                student['id'], 
                message.from_user.id, 
                username, 
                'student'
            )
            role = "ученика"
            tutor_message = f"✅ Ученик {student['full_name']} привязал свой Telegram аккаунт!"
        else:
            success = db.update_student_telegram_id(
                student['id'], 
                message.from_user.id, 
                username, 
                'parent'
            )
            role = "родителя"
            tutor_message = f"✅ Родитель ученика {student['full_name']} привязал свой Telegram аккаунт!"
        
        if success:
            # Отправляем сообщение пользователю
            await message.answer(
                f"✅ <b>Вы успешно привязаны как {role} ученика {student['full_name']}!</b>\n\n"
                f"Теперь вы будете получать уведомления о занятиях и успехах.",
                parse_mode="HTML"
            )
            
            # Отправляем уведомление репетитору
            try:
                tutor = db.get_tutor_by_id(student['tutor_id'])
                if tutor and tutor[1]:  # tutor[1] - telegram_id
                    await message.bot.send_message(
                        chat_id=tutor[1],
                        text=tutor_message
                    )
            except Exception as e:
                print(f"Ошибка при отправке уведомления репетитору: {e}")
        else:
            await message.answer(
                "❌ <b>Ошибка при привязке аккаунта!</b>\n\n"
                "Пожалуйста, попробуйте позже или обратитесь к репетитору.",
                parse_mode="HTML"
            )
        return
    
    # Если неизвестный формат, выполняем стандартный старт
    await cmd_start(message)

    
@router.callback_query(F.data.startswith("back_to_student_"))
async def back_to_student_from_invite(callback_query: types.CallbackQuery):
    await callback_query.answer()
    
    student_id = int(callback_query.data.split("_")[3])
    student = db.get_student_by_id(student_id)
    
    if not student:
        await callback_query.message.edit_text("❌ Ученик не найден!")
        return
    
    # Формируем текст сообщения
    status_text = student['status']
    if student.get('delete_after'):
        status_text = f"{status_text} (будет удален {student['delete_after']})"
    
    student_tg = f"@{student['student_username']}" if student.get('student_username') else "не привязан"
    parent_tg = f"@{student['parent_username']}" if student.get('parent_username') else "не привязан"
    
    text = (
        f"👤 <b>Информация об ученике</b>\n\n"
        f"<b>ФИО:</b> {student['full_name']}\n"
        f"<b>Телефон:</b> {student['phone'] if student['phone'] != '-' else 'не указан'}\n"
        f"<b>Телефон родителя:</b> {student['parent_phone'] if student['parent_phone'] != '-' else 'не указан'}\n"
        f"<b>Статус:</b> {status_text}\n"
        f"<b>ТГ ученика:</b> {student_tg}\n"
        f"<b>ТГ родителя:</b> {parent_tg}\n"
        f"<b>Дата добавления:</b> {student['created_at']}"
    )
    
    # Создаем клавиатуру для управления учеником
    keyboard = [
        [InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"edit_student_{student_id}")],
        [InlineKeyboardButton(text="📤 Пригласить", callback_data=f"invite_{student_id}")],
        [InlineKeyboardButton(text="◀️ Назад к списку", callback_data="back_to_students_list")]
    ]
    
    try:
        await callback_query.message.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
            parse_mode="HTML"
        )
    except TelegramBadRequest:
        await callback_query.message.answer(
            text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
            parse_mode="HTML"
        )

@router.callback_query(F.data == "back_to_students_menu")
async def back_to_students_menu(callback_query: types.CallbackQuery):
    await callback_query.answer()
    
    await callback_query.message.edit_text(
        "👥 <b>Учет учеников</b>\n\n"
        "Здесь вы можете управлять вашими учениками: добавлять новых, "
        "просматривать и редактировать информацию о существующих.",
        reply_markup=get_students_menu_keyboard(),
        parse_mode="HTML"
    )