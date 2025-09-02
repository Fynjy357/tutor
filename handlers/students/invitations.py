# handlers/students/invitations.py
from aiogram import Router, types, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest
import logging
import re

from handlers.start import cmd_start

from .keyboards import get_invite_keyboard, get_student_detail_keyboard
from .utils import format_student_info, get_students_stats
from keyboards.students import get_students_menu_keyboard, get_students_list_keyboard
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
            invite_link = f"https://t.me/{bot_username}?start=invite_{invite_type}_{token}"
            
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

# Обработчик для стартовой команды с приглашением
@router.message(CommandStart(deep_link=True))
async def handle_deep_link(message: types.Message):
    logger.info("=== DEEP LINK HANDLER STARTED ===")
    logger.info(f"Полное сообщение: {message.text}")
    logger.info(f"Пользователь: {message.from_user.id} @{message.from_user.username}")
    
    # Правильное извлечение аргументов
    args = message.text.split()
    if len(args) < 2:
        logger.warning("Нет аргументов в deep link")
        await cmd_start(message)
        return
    
    deep_link_args = args[1]
    logger.info(f"Аргументы deep link: {deep_link_args}")
    
    # Обрабатываем пригласительные ссылки
    if deep_link_args.startswith('student_') or deep_link_args.startswith('parent_'):
        try:
            parts = deep_link_args.split('_', 1)
            if len(parts) < 2:
                logger.error("Неверный формат deep link")
                await message.answer("❌ Неверная ссылка приглашения.")
                return
                
            invite_type, token = parts
            logger.info(f"Тип приглашения: {invite_type}, Токен: {token}")
            
            if invite_type not in ['student', 'parent']:
                logger.error(f"Неизвестный тип приглашения: {invite_type}")
                await message.answer("❌ Неверная ссылка приглашения.")
                return
            
            # Находим ученика по токену
            student = db.get_student_by_token(token, invite_type)
            logger.info(f"Найден ученик: {student is not None}")
            
            if not student:
                logger.error(f"Ученик не найден по токену: {token}")
                await message.answer("❌ Ссылка приглашения недействительна или устарела.")
                return
            
            logger.info(f"Данные ученика: ID={student['id']}, Name={student['full_name']}")
            
            # Получаем username пользователя
            username = f"@{message.from_user.username}" if message.from_user.username else "не указан"
            logger.info(f"Username пользователя: {username}")
            
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
            
            logger.info(f"Привязка аккаунта: {success}")
            
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
                    logger.info(f"Найден репетитор: {tutor is not None}")
                    if tutor and tutor[1]:  # tutor[1] - telegram_id
                        await message.bot.send_message(
                            chat_id=tutor[1],
                            text=tutor_message
                        )
                        logger.info(f"Уведомление отправлено репетитору: {tutor[1]}")
                except Exception as e:
                    logger.error(f"Ошибка при отправке уведомления репетитору: {e}")
            else:
                await message.answer(
                    "❌ <b>Ошибка при привязке аккаунта!</b>\n\n"
                    "Пожалуйста, попробуйте позже или обратитесь к репетитору.",
                    parse_mode="HTML"
                )
            
        except Exception as e:
            logger.error(f"Ошибка в обработке deep link: {e}")
            await message.answer("❌ Произошла ошибка при обработке приглашения.")
    
    else:
        logger.info("Неизвестный формат deep link, выполняется стандартный старт")
        await cmd_start(message)
    
    logger.info("=== DEEP LINK HANDLER FINISHED ===")