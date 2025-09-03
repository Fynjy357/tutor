# handlers/students/invitations.py
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest
import logging
import re

from .keyboards import get_invite_keyboard, get_student_detail_keyboard
from .utils import format_student_info, get_students_stats
from handlers.students.keyboards_student import get_students_menu_keyboard, get_students_list_keyboard
from database import db

router = Router()
logger = logging.getLogger(__name__)

# Регулярное выражение для проверки формата invite_число
INVITE_PATTERN = re.compile(r'^invite_(\d+)$')

@router.callback_query(F.data.regexp(INVITE_PATTERN))
async def invite_menu(callback_query: types.CallbackQuery):
    """Меню приглашения для ученика"""
    await callback_query.answer()
    
    try:
        match = INVITE_PATTERN.match(callback_query.data)
        if not match:
            return
            
        student_id = int(match.group(1))
        student = db.get_student_by_id(student_id)
        
        if not student:
            await callback_query.message.edit_text("❌ Ученик не найден!")
            return
        
        await callback_query.message.edit_text(
            f"👤 <b>Приглашение для {student['full_name']}</b>\n\n"
            "Выберите, кого вы хотите пригласить:",
            parse_mode="HTML",
            reply_markup=get_invite_keyboard(student_id)
        )
    except Exception as e:
        logger.error(f"Ошибка в invite_menu: {e}")
        await callback_query.message.edit_text("❌ Ошибка при обработке запроса")

@router.callback_query(F.data.startswith("generate_invite_"))
async def generate_invite(callback_query: types.CallbackQuery):
    """Генерация приглашения"""
    await callback_query.answer()
    
    try:
        parts = callback_query.data.split("_")
        if len(parts) < 4:
            await callback_query.message.edit_text("❌ Неверный формат запроса!")
            return
            
        student_id = int(parts[2])
        invite_type = parts[3]  # student или parent
        
        student = db.get_student_by_id(student_id)
        if not student:
            await callback_query.message.edit_text("❌ Ученик не найден!")
            return
        
        # Генерируем токен
        token = db.generate_invite_token()
        if db.update_student_token(student_id, token, invite_type):
            # Формируем ссылку приглашения
            bot_username = (await callback_query.bot.get_me()).username
            invite_link = f"https://t.me/{bot_username}?start={invite_type}_{token}"
            
            user_type = "ученика" if invite_type == "student" else "родителя"
            await callback_query.message.edit_text(
                f"✅ <b>Приглашение для {user_type} создано!</b>\n\n"
                f"👤 Ученик: {student['full_name']}\n"
                f"🔗 Ссылка: {invite_link}\n\n"
                "Отправьте эту ссылку пользователю. "
                "При переходе по ссылке аккаунт будет автоматически привязан к ученику.",
                parse_mode="HTML",
                reply_markup=get_invite_keyboard(student_id)
            )
        else:
            await callback_query.message.edit_text(
                "❌ Ошибка при создании приглашения!",
                reply_markup=get_invite_keyboard(student_id)
            )
    except (ValueError, IndexError) as e:
        logger.error(f"Ошибка парсинга callback data: {e}")
        await callback_query.message.edit_text("❌ Ошибка при обработке запроса!")
    except Exception as e:
        logger.error(f"Ошибка в generate_invite: {e}")
        await callback_query.message.edit_text("❌ Ошибка при создании приглашения")

# Обработчик возврата к ученику из меню приглашения
@router.callback_query(F.data.startswith("back_to_student_"))
async def back_to_student_from_invite(callback_query: types.CallbackQuery):
    await callback_query.answer()
    
    try:
        student_id = int(callback_query.data.split("_")[3])
        student = db.get_student_by_id(student_id)
        
        if not student:
            await callback_query.message.edit_text("❌ Ученик не найден!")
            return
        
        # Используем безопасную функцию форматирования
        text = format_student_info(student)
        
        try:
            await callback_query.message.edit_text(
                text,
                reply_markup=get_student_detail_keyboard(student_id),
                parse_mode="HTML"
            )
        except TelegramBadRequest:
            await callback_query.message.answer(
                text,
                reply_markup=get_student_detail_keyboard(student_id),
                parse_mode="HTML"
            )
            
    except (ValueError, IndexError) as e:
        logger.error(f"Ошибка парсинга callback data: {e}")
        await callback_query.message.edit_text("❌ Ошибка при обработке запроса")
    except Exception as e:
        logger.error(f"Ошибка в back_to_student_from_invite: {e}")
        await callback_query.message.edit_text("❌ Произошла ошибка при загрузке информации")

# Обработчик возврата к списку учеников
@router.callback_query(F.data == "back_to_students_list")
async def back_to_students_list(callback_query: types.CallbackQuery):
    await callback_query.answer()
    
    tutor_id = db.get_tutor_id_by_telegram_id(callback_query.from_user.id)
    
    if not tutor_id:
        await callback_query.message.edit_text("❌ Ошибка: не найден ID репетитора.")
        return
    
    students = db.get_students_by_tutor(tutor_id)
    
    if not students:
        await callback_query.message.edit_text(
            "📝 <b>Список учеников пуст</b>\n\n"
            "У вас пока нет добавленных учеников.",
            reply_markup=get_students_menu_keyboard(),
            parse_mode="HTML"
        )
        return
    
    text = "👥 <b>Список ваших учеников</b>\n\n" + get_students_stats(students)
    
    try:
        await callback_query.message.edit_text(
            text,
            reply_markup=get_students_list_keyboard(students, page=0),
            parse_mode="HTML"
        )
    except TelegramBadRequest:
        await callback_query.message.answer(
            text,
            reply_markup=get_students_list_keyboard(students, page=0),
            parse_mode="HTML"
        )

# Обработчик переключения страниц списка учеников
@router.callback_query(F.data.startswith("students_page_"))
async def students_list_page(callback_query: types.CallbackQuery):
    await callback_query.answer()
    
    page = int(callback_query.data.split("_")[2])
    tutor_id = db.get_tutor_id_by_telegram_id(callback_query.from_user.id)
    
    if not tutor_id:
        await callback_query.message.edit_text("❌ Ошибка: не найден ID репетитора.")
        return
    
    students = db.get_students_by_tutor(tutor_id)
    text = "👥 <b>Список ваших учеников</b>\n\n" + get_students_stats(students)
    
    await callback_query.message.edit_text(
        text,
        reply_markup=get_students_list_keyboard(students, page=page),
        parse_mode="HTML"
    )