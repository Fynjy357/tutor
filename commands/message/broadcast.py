import logging
import html
import re
from aiogram import Router, F, Bot
from aiogram.types import Message, ReplyKeyboardRemove
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database import db
from commands.config import SUPER_ADMIN_ID

logger = logging.getLogger(__name__)

class BroadcastStates(StatesGroup):
    waiting_for_message = State()
    waiting_for_confirmation = State()

router = Router()

def sanitize_html(text: str) -> str:
    """Очистка HTML с сохранением корректных тегов"""
    # Разрешенные HTML теги
    allowed_tags = ['b', 'strong', 'i', 'em', 'u', 'ins', 's', 'strike', 'del', 'code', 'pre']
    
    # Шаблон для поиска HTML тегов
    tag_pattern = re.compile(r'</?([a-zA-Z]+)[^>]*>')
    
    def replace_tag(match):
        tag_name = match.group(1).lower()
        if tag_name in allowed_tags:
            # Возвращаем оригинальный тег для разрешенных тегов
            return match.group(0)
        else:
            # Удаляем неразрешенные теги
            return ''
    
    # Убираем только неразрешенные теги, разрешенные оставляем как есть
    cleaned = tag_pattern.sub(replace_tag, text)
    
    # Убираем вариационные селекторы из эмодзи
    cleaned = cleaned.replace('\ufe0f', '')
    
    return cleaned


@router.message(Command("broadcast"))
async def broadcast_command(message: Message, state: FSMContext):
    """Команда для рассылки сообщений всем репетиторам"""
    
    # Проверяем, является ли пользователь супер-админом
    if message.from_user.id != SUPER_ADMIN_ID:
        await message.answer("❌ У вас нет прав для выполнения этой команды.")
        return
    
    await message.answer(
        "📢 <b>Рассылка сообщений всем репетиторам</b>\n\n"
        "Пожалуйста, введите сообщение для рассылки.\n"
        "Вы можете использовать простую HTML-разметку: <b>жирный</b>, <i>курсив</i>, <u>подчеркивание</u>\n\n"
        "<i>Для отмены введите /cancel</i>",
        parse_mode="HTML"
    )
    await state.set_state(BroadcastStates.waiting_for_message)

@router.message(BroadcastStates.waiting_for_message, F.text)
async def process_broadcast_message(message: Message, state: FSMContext):
    """Обрабатывает введенное сообщение для рассылки"""
    
    # Сохраняем ОРИГИНАЛЬНОЕ сообщение
    await state.update_data(broadcast_message=message.text)
    
    # Получаем количество активных репетиторов
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM tutors WHERE status = 'active'")
        tutors_count = cursor.fetchone()[0]
    
    # Очищаем сообщение для предпросмотра
    preview_message = sanitize_html(message.text)
    
    # Дополнительная проверка баланса тегов
    def check_html_balance(text):
        """Проверяет баланс открывающих и закрывающих тегов"""
        stack = []
        tag_pattern = re.compile(r'</?([a-zA-Z]+)[^>]*>')
        
        for match in tag_pattern.finditer(text):
            tag_name = match.group(1).lower()
            if match.group(0).startswith('</'):
                if not stack or stack[-1] != tag_name:
                    return False
                stack.pop()
            else:
                stack.append(tag_name)
        
        return len(stack) == 0
    
    is_html_valid = check_html_balance(preview_message)
    
    if is_html_valid:
        try:
            # Пробуем отправить предпросмотр с HTML разметкой
            await message.answer(
                f"📋 <b>Подтверждение рассылки</b>\n\n"
                f"📝 <b>Сообщение:</b>\n{preview_message}\n\n"
                f"👥 <b>Получатели:</b> {tutors_count} активных репетиторов\n\n"
                f"✅ <b>Отправить сообщение?</b>\n\n"
                f"<i>Ответьте 'да' для отправки или 'нет' для отмены</i>",
                parse_mode="HTML"
            )
        except Exception as e:
            logger.warning(f"HTML parsing error in preview: {e}")
            is_html_valid = False
    
    if not is_html_valid:
        # Если HTML невалиден, показываем сообщение без разметки
        safe_preview = html.escape(preview_message)
        
        await message.answer(
            f"📋 <b>Подтверждение рассылки</b>\n\n"
            f"⚠️ <b>Внимание:</b> Обнаружена ошибка в HTML разметке\n\n"
            f"📝 <b>Сообщение (без форматирования):</b>\n<code>{safe_preview}</code>\n\n"
            f"👥 <b>Получатели:</b> {tutors_count} активных репетиторов\n\n"
            f"✅ <b>Отправить сообщение?</b>\n\n"
            f"<i>Ответьте 'да' для отправки или 'нет' для отмены</i>",
            parse_mode="HTML"
        )
    
    await state.set_state(BroadcastStates.waiting_for_confirmation)

@router.message(BroadcastStates.waiting_for_confirmation, F.text.lower() == 'да')
async def confirm_broadcast(message: Message, state: FSMContext, bot: Bot):
    """Подтверждает и отправляет рассылку"""
    
    data = await state.get_data()
    original_message = data.get('broadcast_message', '')
    
    if not original_message:
        await message.answer("❌ Ошибка: сообщение не найдено.")
        await state.clear()
        return
    
    # Очищаем сообщение от недопустимых HTML-тегов
    broadcast_message = sanitize_html(original_message)
    
    # Получаем список всех активных репетиторов
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT telegram_id, full_name FROM tutors WHERE status = 'active'")
        tutors = cursor.fetchall()
    
    total_tutors = len(tutors)
    successful_sends = 0
    failed_sends = 0
    
    # Отправляем сообщение каждому репетитору
    progress_message = await message.answer(f"🔄 Начинаю рассылку для {total_tutors} репетиторов...")
    
    for i, tutor in enumerate(tutors, 1):
        telegram_id, full_name = tutor
        
        try:
            await bot.send_message(
                chat_id=telegram_id,
                text=f"📢 <b>Сообщение от администратора:</b>\n\n{broadcast_message}",
                parse_mode="HTML"
            )
            successful_sends += 1
            
            # Обновляем прогресс каждые 10 отправок
            if i % 10 == 0:
                await progress_message.edit_text(
                    f"🔄 Рассылка в процессе...\n"
                    f"✅ Отправлено: {i}/{total_tutors}"
                )
            
        except Exception as e:
            logger.error(f"Ошибка отправки сообщения репетитору {full_name} (ID: {telegram_id}): {e}")
            failed_sends += 1
    
    # Формируем отчет о рассылке
    report_message = (
        f"📊 <b>Отчет о рассылке</b>\n\n"
        f"✅ Успешно отправлено: {successful_sends}\n"
        f"❌ Не удалось отправить: {failed_sends}\n"
        f"👥 Всего получателей: {total_tutors}"
    )
    
    await message.answer(report_message, parse_mode="HTML")
    await state.clear()


@router.message(BroadcastStates.waiting_for_confirmation, F.text.lower() == 'нет')
async def cancel_broadcast(message: Message, state: FSMContext):
    """Отменяет рассылку"""
    
    await message.answer("❌ Рассылка отменена.")
    await state.clear()

@router.message(BroadcastStates.waiting_for_confirmation)
async def invalid_confirmation(message: Message):
    """Обрабатывает некорректный ответ подтверждения"""
    
    await message.answer("❌ Пожалуйста, ответьте 'да' для отправки или 'нет' для отмены.")

@router.message(Command("cancel"))
@router.message(F.text.lower() == "отмена")
async def cancel_handler(message: Message, state: FSMContext):
    """Отмена любого состояния"""
    
    current_state = await state.get_state()
    if current_state is None:
        return
    
    await state.clear()
    await message.answer(
        "❌ Действие отменено.",
        reply_markup=ReplyKeyboardRemove()
    )
