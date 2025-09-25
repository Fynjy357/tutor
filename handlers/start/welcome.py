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
    from datetime import datetime, date, timedelta
    
    db = Database()
    
    # Получаем данные репетитора
    tutor = db.get_tutor_by_telegram_id(chat_id)
    
    if not tutor:
        error_text = "❌ Ошибка: не найдены данные репетитора"
        if callback_query:
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
    
    # Русские названия месяцев
    month_names = {
        1: "января", 2: "февраля", 3: "марта", 4: "апреля",
        5: "мая", 6: "июня", 7: "июля", 8: "августа",
        9: "сентября", 10: "октября", 11: "ноября", 12: "декабря"
    }
    
    # Проверяем активность подписки
    has_active_subscription = False
    
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
                has_active_subscription = bool(subscription_data)
    except Exception as e:
        logger.error(f"Error checking subscription: {e}")
        has_active_subscription = db.check_tutor_subscription(tutor_id)

    # Получаем расписание на сегодня (без статистики)
    schedule_text = await get_today_schedule_text(tutor_id)

    # Формируем основной текст (приветствие + расписание)
    welcome_base_text = f"<b>Добро пожаловать, {tutor_name}</b>!\n\n{schedule_text}"

    # Формируем блок подписки/статистики (будет ПОСЛЕ расписания)
    subscription_block = ""
    
    if has_active_subscription:
        try:
            # Получаем статистику заработка (используем ту же логику, что в get_today_schedule_text)
            current_month = datetime.now().month
            current_year = datetime.now().year
            
            current_month_earnings = db.get_earnings_by_period(
                tutor_id, 
                date(current_year, current_month, 1), 
                datetime.now().date()
            )
            
            if current_month == 1:
                prev_month = 12
                prev_year = current_year - 1
            else:
                prev_month = current_month - 1
                prev_year = current_year
            
            prev_month_earnings = db.get_earnings_by_period(
                tutor_id,
                date(prev_year, prev_month, 1),
                date(prev_year, prev_month, 1).replace(day=28) + timedelta(days=4)
            )
            
            active_students_count = db.get_active_students_count(tutor_id)
            
            statistics_text = (
                f"👨‍🎓 Активных учеников: {active_students_count}\n"
                f"💰 Заработано в {month_names[current_month]}: {current_month_earnings} руб\n"
                f"📈 Заработано в {month_names[prev_month]}: {prev_month_earnings} руб\n\n"
            )
            
            # Получаем информацию о подписке
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
                                subscription_info = f"💎 Подписка активна до: {formatted_date}"
                            else:
                                subscription_info = "💎 Подписка активна"
                        else:
                            subscription_info = "💎 Подписка активна"
                    else:
                        subscription_info = "💎 Подписка активна"
            except Exception as e:
                logger.error(f"Error getting subscription info: {e}")
                subscription_info = "💎 Подписка активна"
            
            subscription_block = f"\n\n━━━━━━━━━━━━━━━━━━━━━━━━\n📊 Статистика\n\n{statistics_text}{subscription_info}"
            
        except Exception as e:
            logger.error(f"Error getting statistics: {e}")
            # В случае ошибки показываем только информацию о подписке
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
                                subscription_info = f"💎 Подписка активна до: {formatted_date}"
                            else:
                                subscription_info = "💎 Подписка активна"
                        else:
                            subscription_info = "💎 Подписка активна"
                    else:
                        subscription_info = "💎 Подписка активна"
            except Exception as e:
                logger.error(f"Error getting subscription info: {e}")
                subscription_info = "💎 Подписка активна"
            
            subscription_block = f"\n\n━━━━━━━━━━━━━━━━━━━━━━━━\n📊 Статистика\n\n📊 Статистика временно недоступна\n\n{subscription_info}"
        
    else:
        # Нет подписки
        subscription_block = (
            "\n\n━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "📊 Статистика\n\n"
            "❌ Сервис не оплачен\n\n"
            "Для доступа к статистике и полному функционалу бота "
            "необходимо оплатить подписку.\n\n"
            "При полной подписке доступны:\n"
            "• 📅 Планировщик регулярных занятий\n"
            "• ↩️ Возможность перенести занятие\n"
            "• 📊 Статистика на главном экране\n"

        )

    # Собираем финальный текст: приветствие + расписание + статистика
    welcome_text = f"{welcome_base_text}{subscription_block}"
    
    # Отправляем сообщение
    if callback_query:
        success = await safe_edit_message(
            callback_query.message,
            text=welcome_text,
            reply_markup=get_main_menu_keyboard(),
            parse_mode="HTML"
        )
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
