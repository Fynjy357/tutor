from aiogram import Router, types, F, Bot
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import logging

# Импорты из того же пакета
from .models import consent_manager

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

consent_router = Router()

class ConsentStates(StatesGroup):
    """Состояния для работы с соглашениями"""
    waiting_consent = State()

@consent_router.message(Command("consent_status"))
async def consent_status_command(message: types.Message):
    """Команда для проверки статуса согласий"""
    try:
        await show_consent_status(message)
    except Exception as e:
        logger.error(f"Error in consent_status_command: {e}")
        await message.answer("❌ Произошла ошибка при получении статуса согласий.")

async def request_consents(message: types.Message, user_id: int):
    """Запрос согласий у пользователя с динамическими кнопками"""
    try:
        # Получаем текущий статус согласий пользователя
        status = consent_manager.get_user_consent_status(user_id)
        
        keyboard = []
        
        # Проверяем, принято ли пользовательское соглашение
        agreement_accepted = any(doc_type == 'user_agreement' and accepted for doc_type, accepted, _, _ in status)
        if not agreement_accepted:
            keyboard.append([InlineKeyboardButton(text="✅ Принять пользовательское соглашение", callback_data="accept_agreement")])
        
        # Проверяем, принята ли политика конфиденциальности
        privacy_accepted = any(doc_type == 'privacy_policy' and accepted for doc_type, accepted, _, _ in status)
        if not privacy_accepted:
            keyboard.append([InlineKeyboardButton(text="✅ Принять политику конфиденциальности", callback_data="accept_privacy")])
        
        # Всегда показываем кнопку отказа
        keyboard.append([InlineKeyboardButton(text="❌ Не соглашаюсь", callback_data="reject_all")])
        
        # Кнопки для чтения документов
        keyboard.append([InlineKeyboardButton(text="📖 Прочитать пользовательское соглашение", callback_data="read_agreement")])
        keyboard.append([InlineKeyboardButton(text="📖 Прочитать политику конфиденциальности", callback_data="read_privacy")])
        
        reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
        
        message_text = (
            "📋 <b>Для использования функционала бота</b>\n"
            "<b>необходимо ваше согласие со следующими документами:</b>\n\n"
        )
        
        # Добавляем статус каждого соглашения
        if agreement_accepted:
            message_text += "✅ <b>Пользовательское соглашение</b> - принято\n"
        else:
            message_text += "📄 <b>Пользовательское соглашение</b> - ожидает принятия\n"
        
        if privacy_accepted:
            message_text += "✅ <b>Политика конфиденциальности</b> - принята\n"
        else:
            message_text += "🔒 <b>Политика конфиденциальности</b> - ожидает принятия\n"
        
        message_text += "\nНажмите на соответствующие кнопки для принятия соглашений."
        
        await message.answer(message_text, reply_markup=reply_markup, parse_mode='HTML')
        
    except Exception as e:
        logger.error(f"Error in request_consents: {e}")
        await message.answer("❌ Не удалось загрузить соглашения. Пожалуйста, попробуйте позже.")

async def show_consent_status(message: types.Message):
    """Показать статус согласий пользователя"""
    try:
        user_id = message.from_user.id
        status = consent_manager.get_user_consent_status(user_id)
        
        if not status:
            await message.answer("❌ Информация о согласиях не найдена.")
            return
        
        response = "📊 <b>Статус ваших согласий:</b>\n\n"
        
        for doc_type, accepted, accepted_at, version in status:
            status_emoji = "✅" if accepted else "❌"
            status_text = "Принято" if accepted else "Не принято"
            
            doc_name = "Пользовательское соглашение" if doc_type == "user_agreement" else "Политика конфиденциальности"
            
            response += f"{status_emoji} <b>{doc_name}</b> v{version}\n"
            response += f"   Статус: {status_text}\n"
            if accepted_at:
                response += f"   Время: {accepted_at}\n"
            response += "\n"
        
        # Проверяем, приняты ли все необходимые согласия
        has_all_consents = consent_manager.has_user_consents(user_id)
        if has_all_consents:
            response += "🎉 <b>Все необходимые согласия приняты!</b>"
        else:
            response += "⚠️ <b>Не все необходимые согласия приняты.</b>\nИспользуйте кнопки для принятия соглашений."
        
        await message.answer(response, parse_mode='HTML')
        
    except Exception as e:
        logger.error(f"Error in show_consent_status: {e}")
        await message.answer("❌ Ошибка при получении статуса согласий.")

async def start_registration_process(message: types.Message, state: FSMContext, bot: Bot):
    """Функция запуска процесса регистрации"""
    try:
        # Импортируем состояния регистрации
        from handlers.registration.states import RegistrationStates
        
        # Очищаем предыдущие сообщения регистрации
        await state.update_data(registration_messages=[])
        
        # Начинаем процесс регистрации
        await message.answer(
            "📝 <b>Начинаем регистрацию!</b>\n\n"
            "Пожалуйста, введите ваше ФИО:",
            parse_mode="HTML"
        )
        
        # Устанавливаем состояние ожидания имени
        await state.set_state(RegistrationStates.waiting_for_name)
        
        logger.info("=== ПРОЦЕСС РЕГИСТРАЦИИ ЗАПУЩЕН ===")
        
    except Exception as e:
        logger.error(f"Error in start_registration_process: {e}")
        await message.answer("❌ Ошибка при запуске регистрации")

@consent_router.callback_query(F.data.in_(["accept_agreement", "accept_privacy", "reject_all", "read_agreement", "read_privacy"]))
async def consent_callback_handler(callback_query: CallbackQuery, state: FSMContext, bot: Bot):
    """Обработчик кнопок согласий"""
    try:
        user_id = callback_query.from_user.id
        ip_address = get_user_ip(callback_query) or "unknown"
        
        if callback_query.data == "read_agreement":
            text = consent_manager.read_document("user_agreement.txt")
            if len(text) > 4000:
                parts = [text[i:i+4000] for i in range(0, len(text), 4000)]
                for i, part in enumerate(parts, 1):
                    await callback_query.message.answer(
                        f"📄 <b>Пользовательское соглашение (часть {i}):</b>\n\n{part}", 
                        parse_mode='HTML'
                    )
            else:
                await callback_query.message.answer(
                    f"📄 <b>Пользовательское соглашение:</b>\n\n{text}", 
                    parse_mode='HTML'
                )
            await callback_query.answer()
            
        elif callback_query.data == "read_privacy":
            text = consent_manager.read_document("privacy_policy.txt")
            if len(text) > 4000:
                parts = [text[i:i+4000] for i in range(0, len(text), 4000)]
                for i, part in enumerate(parts, 1):
                    await callback_query.message.answer(
                        f"🔒 <b>Политика конфиденциальности (часть {i}):</b>\n\n{part}", 
                        parse_mode='HTML'
                    )
            else:
                await callback_query.message.answer(
                    f"🔒 <b>Политика конфиденциальности:</b>\n\n{text}", 
                    parse_mode='HTML'
                )
            await callback_query.answer()
            
        elif callback_query.data == "accept_agreement":
            # Сохраняем принятие пользовательского соглашения
            success = consent_manager.save_consent(user_id, ip_address, "user_agreement", "1.0", True)
            
            if success:
                await callback_query.answer("✅ Пользовательское соглашение принято!")
                
                # Проверяем, приняты ли все согласия
                if consent_manager.has_user_consents(user_id):
                    user_data = await state.get_data()
                    wants_registration = user_data.get('wants_registration', False)
                    
                    if wants_registration:
                        # Пользователь хотел зарегистрироваться
                        await callback_query.message.edit_text(
                            "🎉 <b>Спасибо! Вы успешно приняли все соглашения.</b>\n\n"
                            "Запускаем процесс регистрации...",
                            parse_mode='HTML'
                        )
                        
                        # Очищаем флаг, но НЕ очищаем состояние полностью!
                        await state.update_data(wants_registration=False)
                        
                        # Запускаем регистрацию
                        await start_registration_process(callback_query.message, state, bot)
                    else:
                        await callback_query.message.edit_text(
                            "🎉 <b>Спасибо! Вы успешно приняли все соглашения.</b>\n\n"
                            "Теперь вы можете пользоваться всеми функциями бота!",
                            parse_mode='HTML'
                        )
                        # Для обычного принятия согласий очищаем состояние
                        await state.clear()
                else:
                    # Обновляем сообщение с убранной кнопкой
                    await request_consents(callback_query.message, user_id)
            else:
                await callback_query.answer("❌ Ошибка при сохранении согласия")
            
        elif callback_query.data == "accept_privacy":
            # Сохраняем принятие политики конфиденциальности
            success = consent_manager.save_consent(user_id, ip_address, "privacy_policy", "1.0", True)
            
            if success:
                await callback_query.answer("✅ Политика конфиденциальности принята!")
                
                # Проверяем, приняты ли все согласия
                if consent_manager.has_user_consents(user_id):
                    user_data = await state.get_data()
                    wants_registration = user_data.get('wants_registration', False)
                    
                    if wants_registration:
                        # Пользователь хотел зарегистрироваться
                        await callback_query.message.edit_text(
                            "🎉 <b>Спасибо! Вы успешно приняли все соглашения.</b>\n\n"
                            "Запускаем процесс регистрации...",
                            parse_mode='HTML'
                        )
                        
                        # Очищаем флаг, но НЕ очищаем состояние полностью!
                        await state.update_data(wants_registration=False)
                        
                        # Запускаем регистрацию
                        await start_registration_process(callback_query.message, state, bot)
                    else:
                        await callback_query.message.edit_text(
                            "🎉 <b>Спасибо! Вы успешно приняли все соглашения.</b>\n\n"
                            "Теперь вы можете пользоваться всеми функциями бота!",
                            parse_mode='HTML'
                        )
                        # Для обычного принятия согласий очищаем состояние
                        await state.clear()
                else:
                    # Обновляем сообщение с убранной кнопкой
                    await request_consents(callback_query.message, user_id)
            else:
                await callback_query.answer("❌ Ошибка при сохранении согласия")
            
        elif callback_query.data == "reject_all":
            # Сохраняем отказ
            consent_manager.save_consent(user_id, ip_address, "user_agreement", "1.0", False)
            consent_manager.save_consent(user_id, ip_address, "privacy_policy", "1.0", False)
            
            # Очищаем флаг регистрации при отказе
            await state.update_data(wants_registration=False)
            
            await callback_query.message.edit_text(
                "❌ <b>Вы отказались от принятия соглашений.</b>\n\n"
                "Для использования бота необходимо принять все условия.\n\n"
                "Выполните команду /start чтобы начать сначала.",
                parse_mode='HTML'
            )
            await state.clear()
            await callback_query.answer()
        
    except Exception as e:
        logger.error(f"Error in consent_callback_handler: {e}")
        await callback_query.answer("❌ Произошла ошибка. Пожалуйста, попробуйте позже.")

def get_user_ip(callback_query: CallbackQuery) -> str:
    """
    Получение IP адреса пользователя
    В реальном проекте реализуйте получение IP из запроса
    """
    return "unknown"

# Middleware для проверки согласий при нажатии инлайн кнопки start_registration
class ConsentMiddleware:
    """Middleware для проверки согласий перед выполнением колбэка start_registration"""
    
    async def __call__(self, handler, event, data):
        # Проверяем, является ли это колбэком start_registration
        is_start_registration = False
        
        if hasattr(event, 'data') and event.data:
            if event.data == 'start_registration':
                is_start_registration = True
        
        # Если это не колбэк start_registration, пропускаем проверку
        if not is_start_registration:
            return await handler(event, data)
        
        # Для колбэка start_registration проверяем согласия
        user_id = event.from_user.id
        
        # Если согласия уже приняты - сразу вызываем регистрацию
        if consent_manager.has_user_consents(user_id):
            return await handler(event, data)
        
        # Получаем FSMContext из данных
        state = data.get('state')
        if state:
            # Сохраняем информацию о том, что пользователь хотел зарегистрироваться
            await state.update_data(wants_registration=True)
        
        # Если согласия не приняты - блокируем колбэк и предлагаем принять
        keyboard = [
            [InlineKeyboardButton(text="📋 Принять соглашения", callback_data="show_consents")]
        ]
        reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
        
        # Отвечаем на колбэк
        if hasattr(event, 'answer'):
            await event.answer(
                "⚠️ Для регистрации необходимо принять соглашения",
                show_alert=True
            )
        
        # Отправляем сообщение с предложением принять соглашения
        if hasattr(event, 'message'):
            await event.message.answer(
                "⚠️ <b>Для регистрации необходимо принять соглашения.</b>\n\n"
                "Используйте кнопку ниже для принятия соглашений.",
                reply_markup=reply_markup,
                parse_mode='HTML'
            )
        
        # Не вызываем оригинальный handler, так как колбэк заблокирован
        return

# Создаем экземпляр middleware
consent_middleware = ConsentMiddleware()

# Обработчик для кнопки показа соглашений
@consent_router.callback_query(F.data == "show_consents")
async def show_consents_callback(callback_query: CallbackQuery, state: FSMContext):
    """Обработчик кнопки показа соглашений"""
    await callback_query.answer()
    await request_consents(callback_query.message, callback_query.from_user.id)
    await state.set_state(ConsentStates.waiting_consent)

# Обработчик для любых сообщений в состоянии ожидания согласия
@consent_router.message(ConsentStates.waiting_consent)
async def handle_waiting_consent(message: types.Message):
    """Обработчик сообщений в состоянии ожидания согласия"""
    await message.answer(
        "⏳ <b>Ожидаю вашего решения по соглашениям.</b>\n\n"
        "Пожалуйста, используйте кнопки выше для принятия или отказа от соглашений.",
        parse_mode='HTML'
    )

# Обработчик для команды старта регистрации
@consent_router.message(Command("start_registration"))
async def start_registration_command(message: types.Message, state: FSMContext, bot: Bot):
    """Команда для начала регистрации"""
    try:
        user_id = message.from_user.id
        
        # Проверяем согласия
        if consent_manager.has_user_consents(user_id):
            # Согласия приняты - запускаем регистрацию
            await start_registration_process(message, state, bot)
        else:
            # Согласия не приняты - сохраняем флаг и показываем соглашения
            await state.update_data(wants_registration=True)
            await request_consents(message, user_id)
            await state.set_state(ConsentStates.waiting_consent)
            
    except Exception as e:
        logger.error(f"Error in start_registration_command: {e}")
        await message.answer("❌ Произошла ошибка. Пожалуйста, попробуйте позже.")

# Добавляем обработчик состояния ожидания имени на случай проблем с основным роутером
from handlers.registration.states import RegistrationStates

@consent_router.message(RegistrationStates.waiting_for_name)
async def process_name_fallback(message: types.Message, state: FSMContext, bot: Bot):
    """Фолбэк обработчик имени на случай проблем с основным роутером"""
    logger.info("=== ФОЛБЭК ОБРАБОТЧИК ИМЕНИ ВЫЗВАН ===")
    
    if not message.text:
        await message.answer("Пожалуйста, введите ФИО текстом:")
        return
    
    name = message.text.strip()
    
    if len(name) < 2:
        await message.answer("Пожалуйста, введите корректное ФИО (минимум 2 символа):")
        return
    
    # Сохраняем имя
    await state.update_data(name=name)
    
    # Запрашиваем телефон
    await message.answer(
        "Отлично! Теперь введите ваш номер телефона. "
        "Вы можете использовать кнопку ниже для быстрой отправки:",
        reply_markup=get_phone_keyboard()
    )
    
    await state.set_state(RegistrationStates.waiting_for_phone)
    logger.info("=== ИМЯ ОБРАБОТАНО ЧЕРЕЗ ФОЛБЭК ===")

def get_phone_keyboard():
    """Создает клавиатуру для запроса телефона"""
    return types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text="📱 Отправить номер телефона", request_contact=True)]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )

# Команда для проверки состояния
@consent_router.message(Command("state"))
async def check_state(message: types.Message, state: FSMContext):
    """Проверка текущего состояния"""
    current_state = await state.get_state()
    data = await state.get_data()
    await message.answer(f"Текущее состояние: {current_state}\nДанные: {data}")