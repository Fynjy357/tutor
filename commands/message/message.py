from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import logging

# Импортируем конфиг с ID суперадмина
from commands.config import SUPER_ADMIN_ID

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Создаем роутер
message_router = Router()

# Состояния для отправки сообщения
class AdminMessageStates(StatesGroup):
    waiting_user_id = State()
    waiting_message_text = State()

# Функция проверки суперадмина
async def is_superadmin(user_id: int) -> bool:
    """Проверяет, является ли пользователь суперадмином"""
    return user_id == SUPER_ADMIN_ID

# Команда для отправки сообщения пользователю
@message_router.message(Command("send_message"))
async def send_message_command(message: types.Message, state: FSMContext):
    """Команда для отправки сообщения пользователю по ID (только для суперадмина)"""
    # Проверяем права доступа
    if not await is_superadmin(message.from_user.id):
        await message.answer("❌ Эта команда доступна только для суперадминистратора.")
        return
    
    await message.answer(
        "📨 <b>Отправка сообщения пользователю</b>\n\n"
        "Введите Telegram ID пользователя:",
        parse_mode='HTML'
    )
    await state.set_state(AdminMessageStates.waiting_user_id)

# Обработчик ввода ID пользователя
@message_router.message(AdminMessageStates.waiting_user_id)
async def process_user_id(message: types.Message, state: FSMContext):
    """Обработка введенного ID пользователя"""
    try:
        user_id = int(message.text.strip())
        await state.update_data(user_id=user_id)
        
        await message.answer(
            "✅ ID пользователя принят.\n\n"
            "Теперь введите текст сообщения:",
            parse_mode='HTML'
        )
        await state.set_state(AdminMessageStates.waiting_message_text)
        
    except ValueError:
        await message.answer("❌ Неверный формат ID. Введите числовой ID пользователя:")

# Обработчик ввода текста сообщения
@message_router.message(AdminMessageStates.waiting_message_text)
async def process_message_text(message: types.Message, state: FSMContext, bot):
    """Обработка текста сообщения и отправка"""
    try:
        data = await state.get_data()
        user_id = data['user_id']
        message_text = message.text
        
        # Пытаемся отправить сообщение
        try:
            await bot.send_message(
                chat_id=user_id,
                text=f"📩 <b>Сообщение от администратора:</b>\n\n{message_text}",
                parse_mode='HTML'
            )
            
            await message.answer(
                f"✅ Сообщение успешно отправлено пользователю с ID: {user_id}",
                parse_mode='HTML'
            )
            
            # Логируем отправку
            logger.info(f"Superadmin {message.from_user.id} sent message to user {user_id}: {message_text}")
            
        except Exception as e:
            error_msg = f"❌ Не удалось отправить сообщение пользователю {user_id}. Ошибка: {e}"
            await message.answer(error_msg)
            logger.error(f"Failed to send message to user {user_id}: {e}")
        
        # Очищаем состояние
        await state.clear()
        
    except Exception as e:
        await message.answer("❌ Произошла ошибка. Попробуйте снова.")
        logger.error(f"Error in process_message_text: {e}")
        await state.clear()

# Команда для проверки прав (удобно для отладки)
@message_router.message(Command("check_admin"))
async def check_admin_command(message: types.Message):
    """Команда для проверки прав суперадмина"""
    if await is_superadmin(message.from_user.id):
        await message.answer("✅ Вы являетесь суперадминистратором!")
    else:
        await message.answer("❌ Вы не являетесь суперадминистратором.")

# Добавляем обработчик отмены
@message_router.message(Command("cancel"))
async def cancel_command(message: types.Message, state: FSMContext):
    """Команда отмены текущей операции"""
    current_state = await state.get_state()
    if current_state:
        await state.clear()
        await message.answer("❌ Операция отменена.")
    else:
        await message.answer("❌ Нет активных операций для отмены.")
