from aiogram import types
from database import db
from handlers.schedule.schedule_utils import get_today_schedule_text
from handlers.start.keyboards_start import get_student_welcome_keyboard, get_parent_welcome_keyboard, get_registration_keyboard
from keyboards.main_menu import get_main_menu_keyboard
from handlers.start.config import WELCOME_BACK_TEXT, REGISTRATION_TEXT
from aiogram.exceptions import TelegramBadRequest
from datetime import datetime

from aiogram.exceptions import TelegramBadRequest
import logging

logger = logging.getLogger(__name__)

# И добавьте функцию safe_edit_message в первый файл
async def safe_edit_message(message, text, reply_markup=None, parse_mode=None):
    """
    Безопасное редактирование сообщения с обработкой ошибки 'message not modified'
    """
    try:
        await message.edit_text(
            text=text,
            reply_markup=reply_markup,
            parse_mode=parse_mode
        )
        return True
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            # Сообщение не изменилось - это нормально
            return False
        else:
            logger.error(f"Error editing message: {e}")
            return False
    except Exception as e:
        logger.error(f"Error editing message: {e}")
        return False

logger = logging.getLogger(__name__)

async def show_welcome_message(message: types.Message):
    """Показ приветственного сообщения"""
    # 1) Проверяем, является ли пользователь учеником в main_students
    main_student = db.get_main_student_by_telegram_id(message.from_user.id)
    
    if main_student and main_student['student_telegram_id'] == message.from_user.id:
        await show_student_welcome(message, main_student)
        return
    
    # 2) Проверяем, является ли пользователь родителем в main_parents
    main_parent = db.get_main_parent_by_telegram_id(message.from_user.id)
    
    if main_parent:
        await show_parent_welcome(message, main_parent)
        return
    
    # 3) Проверяем, является ли пользователь репетитором
    existing_tutor = db.get_tutor_by_telegram_id(message.from_user.id)
    
    if existing_tutor:
        await show_welcome_back(message, existing_tutor)
        return
    
    # 4) Если ни одно из условий не выполнилось - показываем регистрацию
    await show_registration_message(message)

async def show_student_welcome(message: types.Message, main_student: dict):
    """Приветствие для ученика из main_students"""
    main_student_id = main_student['id']
    
    # Получаем всех репетиторов студента
    tutors = db.get_tutors_for_main_student(main_student_id)
    
    # Формируем текст приветствия для ученика
    welcome_text = format_student_welcome(main_student, tutors)
    
    keyboard = get_student_welcome_keyboard()
    
    await message.answer(
        welcome_text,
        reply_markup=keyboard,
        parse_mode="HTML"
    )

async def show_parent_welcome(message: types.Message, main_parent: dict):
    """Приветствие для родителя из main_parents"""
    # Получаем учеников родителя
    students = db.get_parent_students(main_parent['parent_telegram_id'])
    
    # Получаем всех репетиторов родителя
    tutors = db.get_tutors_for_parent(main_parent['parent_telegram_id'])
    
    # Формируем текст приветствия для родителя
    welcome_text = format_parent_welcome(main_parent, students, tutors)
    
    keyboard = get_parent_welcome_keyboard()
    
    await message.answer(
        welcome_text,
        reply_markup=keyboard,
        parse_mode="HTML"
    )

def format_student_welcome(main_student: dict, tutors: list) -> str:
    """Форматирует приветственное сообщение для ученика"""
    
    student_name = main_student['full_name']
    
    header = f"🎓 Привет, {student_name}!\n\n"
    header += "Рад тебя видеть! Вот твоя информация:\n\n"
    
    # Информация о репетиторах
    tutors_text = "📚 <b>Твои репетиторы:</b>\n"
    if tutors:
        for i, tutor in enumerate(tutors, 1):
            tutors_text += f"{i}. {tutor['full_name']}"
            if tutor.get('phone'):
                tutors_text += f" - {tutor['phone']}"
            tutors_text += "\n"
    else:
        tutors_text += "Пока не назначены\n"
    tutors_text += "\n"
    
    # Общая информация для ученика
    info_text = f"⏰ <b>Часовой пояс:</b> {main_student.get('timezone', 'Europe/Moscow')}\n"
    info_text += f"🔔 <b>Уведомления:</b> {'включены ✅' if main_student.get('notification_enabled', True) else 'выключены 🔕'}\n"
    
    return f"{header}{tutors_text}{info_text}"

def format_parent_welcome(main_parent: dict, students: list, tutors: list) -> str:
    """Форматирует приветственное сообщение для родителя"""
    
    header = f"👨‍👩‍👧‍👦 Здравствуйте!\n\n"
    
    # Информация о детях
    if students:
        student_names = ", ".join([student['full_name'] for student in students])
        header += f"Ваши дети: <b>{student_names}</b>\n\n"
        
        # Статистика по детям
        active_count = sum(1 for student in students if student.get('status') == 'active')
        paused_count = sum(1 for student in students if student.get('status') == 'paused')
        
        header += f"📊 <b>Статистика:</b>\n"
        header += f"✅ Активных: {active_count}\n"
        if paused_count > 0:
            header += f"⏸️ На паузе: {paused_count}\n"
        header += "\n"
    else:
        header += "Ожидайте привязки учеников.\n\n"
    
    # Информация о репетиторах
    tutors_text = "👨‍🏫 <b>Репетиторы ваших детей:</b>\n"
    if tutors:
        # Убираем дубликаты репетиторов
        unique_tutors = {tutor['id']: tutor for tutor in tutors}.values()
        
        for i, tutor in enumerate(unique_tutors, 1):
            tutors_text += f"{i}. {tutor['full_name']}"
            if tutor.get('phone'):
                tutors_text += f" - {tutor['phone']}"
            tutors_text += "\n"
        tutors_text += "\n<b>Вы можете связаться с любым из них!</b>\n"
    else:
        tutors_text += "Пока не назначены\n"
    tutors_text += "\n"
    
    # Что можно сделать
    info_text = "👀 <b>Что вы можете сделать:</b>\n"
    info_text += "• Посмотреть расписание занятий\n"
    info_text += "• Проверить домашние задания\n"  
    info_text += "• Увидеть отчеты об успеваемости\n"
    info_text += "• Настроить уведомления\n\n"
    
    info_text += f"⏰ <b>Часовой пояс:</b> {main_parent.get('timezone', 'Europe/Moscow')}\n"
    
    return f"{header}{tutors_text}{info_text}"

async def show_welcome_back(message: types.Message, tutor: tuple):
    """Приветствие для зарегистрированного репетитора с расписанием на сегодня"""
    await show_main_menu(
        chat_id=message.from_user.id,
        message=message
    )
# # В любом другом месте, где нужно вернуться в главное меню
# await show_main_menu(chat_id=user_id, message=message)
# # или
# await show_main_menu(chat_id=user_id, callback_query=callback_query)

async def show_registration_message(message: types.Message):
    """Приветствие для нового пользователя"""
    await message.answer(
        REGISTRATION_TEXT,
        reply_markup=get_registration_keyboard(),
        parse_mode="HTML"
    )

async def show_main_menu(chat_id: int, message: types.Message = None, callback_query: types.CallbackQuery = None):
    """Универсальная функция для показа главного меню"""
    from database import Database
    from aiogram.exceptions import TelegramBadRequest
    
    db = Database()
    
    # Получаем данные репетитора
    tutor = db.get_tutor_by_telegram_id(chat_id)
    
    if not tutor:
        error_text = "❌ Ошибка: не найдены данные репетитора"
        if callback_query:
            # Используем safe_edit_message вместо прямого edit_text
            success = await safe_edit_message(
                callback_query.message,
                text=error_text,
                parse_mode="HTML"
            )
            if not success:
                await callback_query.message.answer(error_text, parse_mode="HTML")
        elif message:
            await message.answer(error_text, parse_mode="HTML")
        return
    
    tutor_name = tutor[2] if tutor else "Пользователь"
    tutor_id = tutor[0]
    
    # Получаем расписание на сегодня
    schedule_text = await get_today_schedule_text(tutor_id)

    # Получаем текст подписки
    subscription_text = ""
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('SELECT telegram_id FROM tutors WHERE id = ?', (tutor_id,))
            tutor_data = cursor.fetchone()
            
            if tutor_data:
                telegram_id = tutor_data[0]
                
                cursor.execute('''
                SELECT valid_until FROM payments 
                WHERE user_id = ? 
                AND status = 'succeeded'
                AND valid_until >= datetime('now')
                ORDER BY created_at DESC
                LIMIT 1
                ''', (telegram_id,))
                
                subscription_data = cursor.fetchone()
                
                if subscription_data:
                    valid_until = subscription_data[0]
                    
                    if isinstance(valid_until, str):
                        try:
                            valid_until = datetime.strptime(valid_until, '%Y-%m-%d %H:%M:%S')
                        except:
                            pass
                    
                    if isinstance(valid_until, datetime):
                        formatted_date = valid_until.strftime('%d.%m.%Y %H:%M')
                        subscription_text = f"💎 Подписка активна до: {formatted_date}\n"
                    else:
                        subscription_text = "💎 Подписка активна\n"
    
    except Exception as e:
        logger.error(f"Error getting subscription details: {e}")
        if db.check_tutor_subscription(tutor_id):
            subscription_text = "💎 Подписка активна\n\n"

    # Формируем полный текст
    formatted_text = WELCOME_BACK_TEXT.format(
        tutor_name=tutor_name,
        schedule_text=schedule_text
    )
    welcome_text = f"{subscription_text}{formatted_text}"
    
    # Отправляем сообщение в зависимости от контекста
    if callback_query:
        # Используем safe_edit_message
        success = await safe_edit_message(
            callback_query.message,
            text=welcome_text,
            reply_markup=get_main_menu_keyboard(),
            parse_mode="HTML"
        )
        # Если редактирование не удалось, отправляем новое сообщение
        if not success:
            await callback_query.message.answer(
                welcome_text,
                reply_markup=get_main_menu_keyboard(),
                parse_mode="HTML"
            )
    elif message:
        await message.answer(
            welcome_text,
            reply_markup=get_main_menu_keyboard(),
            parse_mode="HTML"
        )

