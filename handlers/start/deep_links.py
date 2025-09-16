from aiogram import types
import logging
from datetime import datetime, timezone, timedelta
import pytz
import tzlocal
from database import db
from handlers.start.welcome import show_registration_message, show_welcome_back, show_welcome_message

logger = logging.getLogger(__name__)

async def detect_user_timezone(message: types.Message) -> str:
    """Определение часового пояса по времени отправки сообщения"""
    try:
        if hasattr(message, 'date'):
            # message.date уже является datetime объектом в UTC
            message_time_utc = message.date.replace(tzinfo=timezone.utc)
            
            # Текущее время сервера в UTC
            server_time_utc = datetime.now(timezone.utc)
            
            # Вычисляем разницу во времени (в часах)
            time_diff_hours = (server_time_utc - message_time_utc).total_seconds() / 3600
            
            # Корректируем разницу с учетом задержки сети (0-5 минут)
            if 0 <= time_diff_hours <= 0.083:  # 0-5 минут
                time_diff_hours = 0
            elif time_diff_hours > 0.083:
                time_diff_hours -= 0.083  # Вычитаем 5 минут задержки
            
            logger.info(f"Разница во времени: {time_diff_hours:.2f} часов")
            
            # Определяем часовой пояс по разнице
            return determine_timezone_by_offset(time_diff_hours)
            
    except Exception as e:
        logger.error(f"Ошибка определения часового пояса по времени: {e}")
    
    # По умолчанию возвращаем московское время
    return 'Europe/Moscow'

def determine_timezone_by_offset(hours_diff: float) -> str:
    """Определение часового пояса по разнице во времени"""
    user_utc_offset = round(hours_diff)
    
    # Сопоставляем смещение с российскими часовыми поясами
    timezone_mapping = {
        2: 'Europe/Kaliningrad',     # UTC+2
        3: 'Europe/Moscow',          # UTC+3
        5: 'Asia/Yekaterinburg',     # UTC+5
        6: 'Asia/Omsk',              # UTC+6
        7: 'Asia/Krasnoyarsk',       # UTC+7
        8: 'Asia/Irkutsk',           # UTC+8
        9: 'Asia/Yakutsk',           # UTC+9
        10: 'Asia/Vladivostok',      # UTC+10
        11: 'Asia/Magadan',          # UTC+11
        12: 'Asia/Kamchatka'         # UTC+12
    }
    
    return timezone_mapping.get(user_utc_offset, 'Europe/Moscow')

async def is_user_tutor(telegram_id: int) -> bool:
    """Проверяет, является ли пользователь репетитором"""
    try:
        tutor = db.get_tutor_by_telegram_id(telegram_id)
        return tutor is not None
    except Exception as e:
        logger.error(f"Ошибка при проверке пользователя на репетитора: {e}")
        return False

async def handle_deep_link(message: types.Message):
    args = message.text.split()
    print(args)
    
    if len(args) < 2:
        await show_welcome_message(message)
        return
        
    deep_link_args = args[1]
    
    """Обработка deep link приглашений"""
    logger.info(f"Deep link: {deep_link_args} from user: {message.from_user.id}")
    
    # Обрабатываем пригласительные ссылки
    if deep_link_args.startswith(('student_', 'parent_')):
        await process_invitation_link(message, deep_link_args)
   # Обрабатываем реферальные ссылки
    elif deep_link_args.startswith('ref_'):
        await process_referral_link(message, deep_link_args)
    else:
        logger.info("Неизвестный формат deep link")
        await show_welcome_message(message)

async def process_invitation_link(message: types.Message, deep_link_args: str):
    """Обработка пригласительной ссылки"""
    try:
        # Проверяем, не является ли пользователь репетитором
        if await is_user_tutor(message.from_user.id):
            await message.answer(
                "❌ <b>Репетиторы не могут использовать пригласительные ссылки!</b>\n\n"
                "Вы уже зарегистрированы как репетитор. Пригласительные ссылки предназначены "
                "только для учеников и их родителей.",
                parse_mode="HTML"
            )
            return
            
        parts = deep_link_args.split('_', 1)
        if len(parts) < 2:
            await message.answer("❌ Неверная ссылка приглашения.")
            return
            
        invite_type, token = parts
        
        if invite_type not in ['student', 'parent']:
            await message.answer("❌ Неверная ссылка приглашения.")
            return
        
        # Находим ученика по токену (с проверкой, что токен еще действителен)
        student = db.get_student_by_token(token, invite_type)
        if not student:
            await message.answer(
                "❌ Ссылка приглашения недействительна или уже использована!\n"
                "Обратитесь к вашему репетитору за новой ссылкой."
            )
            return
        
        # Проверяем, не привязан ли уже аккаунт этого типа
        if invite_type == 'student' and student.get('student_telegram_id'):
            await message.answer(
                "❌ У ученика уже привязан Telegram аккаунт!\n"
                "Обратитесь к репетитору за помощью."
            )
            return
        elif invite_type == 'parent' and student.get('parent_telegram_id'):
            await message.answer(
                "❌ У родителя уже привязан Telegram аккаунт!\n"
                "Обратитесь к репетитору за помощью."
            )
            return
        
        # Привязываем Telegram аккаунт с определением часового пояса
        success, role, tutor_message, user_timezone = await link_telegram_account(
            message, student, invite_type
        )
        
        if success:
            await send_success_response(message, student, role, user_timezone)
            await notify_tutor(message, student, tutor_message)
        else:
            await send_error_response(message)
            
    except Exception as e:
        logger.error(f"Ошибка в обработке deep link: {e}")
        await message.answer("❌ Произошла ошибка при обработке приглашения.")

async def link_telegram_account(message: types.Message, student: dict, invite_type: str):
    """Привязка Telegram аккаунта к ученику с определением часового пояса"""
    username = f"@{message.from_user.username}" if message.from_user.username else "не указан"
    
    # Определяем часовой пояс пользователя
    user_timezone = await detect_user_timezone(message)
    
    # Получаем понятное название часового пояса
    timezone_name = get_timezone_display_name(user_timezone)
    
    if invite_type == 'student':
        success = db.update_student_telegram_id(
            student['id'], 
            message.from_user.id, 
            username, 
            'student',
            user_timezone
        )
        role = "ученик"
        tutor_message = f"✅ Ученик {student['full_name']} привязал свой Telegram аккаунт!\nЧасовой пояс: {timezone_name}"
    else:
        success = db.update_student_telegram_id(
            student['id'], 
            message.from_user.id, 
            username, 
            'parent',
            user_timezone
        )
        role = "родитель"
        tutor_message = f"✅ Родитель ученика {student['full_name']} привязал свой Telegram аккаунт!\nЧасовой пояс: {timezone_name}"
    
    return success, role, tutor_message, timezone_name

def get_timezone_display_name(timezone_str: str) -> str:
    """Получение понятного названия часового пояса"""
    try:
        tz = pytz.timezone(timezone_str)
        now = datetime.now(tz)
        offset = now.utcoffset().total_seconds() / 3600
        
        # Сопоставляем с российскими часовыми поясами
        timezone_names = {
            'Europe/Kaliningrad': 'Калининград (+2)',
            'Europe/Moscow': 'Москва (+3)',
            'Asia/Yekaterinburg': 'Екатеринбург (+5)',
            'Asia/Omsk': 'Омск (+6)',
            'Asia/Krasnoyarsk': 'Красноярск (+7)',
            'Asia/Irkutsk': 'Иркутск (+8)',
            'Asia/Yakutsk': 'Якутск (+9)',
            'Asia/Vladivostok': 'Владивосток (+10)',
            'Asia/Magadan': 'Магадан (+11)',
            'Asia/Kamchatka': 'Камчатка (+12)'
        }
        
        return timezone_names.get(timezone_str, f"{timezone_str} (UTC+{int(offset)})")
        
    except Exception:
        return timezone_str

async def send_success_response(message: types.Message, student: dict, role: str, timezone: str):
    """Отправка сообщения об успешной привязке с информацией о часовом поясе"""
    tutor = db.get_tutor_by_id(student['tutor_id'])
    await message.answer(
        f"✅ <b>Вы успешно привязаны как {role}</b>\n\n" 
        f"<b>Ваш репетитор: {tutor['full_name']}!</b>\n\n"
        # f"🌍 <b>Часовой пояс:</b> {timezone}\n"
        f" С помощью этого бота вы можете:\n\n"
        f"📚 Посмотреть информацию о домашних заданиях\n\n"
        f"💳 Узнать статус оплаты занятий\n"
        f"📅 Своевременно получать напоминания о занятиях\n"
        f"Вы можете воспользоваться командой /start чтобы узнать актуальную информацию.",
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

# Добавляем новую функцию для обработки реферальных ссылок
async def process_referral_link(message: types.Message, deep_link_args: str):
    """Обработка реферальной ссылки с системой статусов"""
    try:
        user_id = message.from_user.id
        referral_code = deep_link_args
        
        logger.info(f"Обрабатываем реферальный код: {referral_code} для пользователя: {user_id}")
        
        # ✅ ПРОВЕРКА: если пользователь уже зарегистрирован как репетитор
        existing_tutor = db.get_tutor_by_telegram_id(user_id)
        if existing_tutor:
            logger.info(f"Пользователь {user_id} уже зарегистрирован как репетитор {existing_tutor['id']}, пропускаем реферальную обработку")
            await show_welcome_back(message, existing_tutor)  # ✅ Используем вашу существующую функцию
            return
        
        if referral_code:
            referrer = db.get_tutor_by_referral_code(referral_code)
            logger.info(f"Найден репетитор: {referrer}")
            
            if referrer:
                result = db.create_or_update_referral_visit(
                    referrer_id=referrer['id'],
                    visitor_telegram_id=user_id,
                    referral_code=referral_code
                )
                logger.info(f"Результат создания записи: {result}")
        
        await show_registration_message(message)
        
    except Exception as e:
        logger.error(f"Ошибка обработки реферальной ссылки: {e}")
        await show_registration_message(message)
