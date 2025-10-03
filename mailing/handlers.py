# mailing/handlers.py
import asyncio
from asyncio.log import logger
import os
import json
from datetime import datetime
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardButton, InlineKeyboardMarkup

from commands.config import SUPER_ADMIN_ID
from .models import BonusMailing, MailingConfig
from database import db


# Создаем роутер
mailing_router = Router()

# Состояния для создания рассылки
class CreateMailingStates(StatesGroup):
    waiting_for_message = State()
    confirm_message = State()
    waiting_for_files = State()
    waiting_for_tariffs = State()
    waiting_for_start_date = State()
    waiting_for_end_date = State()

# Состояния для редактирования рассылки
class EditMailingStates(StatesGroup):
    waiting_for_new_start_date = State()
    waiting_for_new_end_date = State()
    waiting_for_new_files = State()

# Инициализация модели
bonus_mailing = BonusMailing(db)

def is_admin(user_id: int) -> bool:
    """Проверяет, является ли пользователь администратором"""
    return user_id == SUPER_ADMIN_ID

def create_tariffs_keyboard(selected_tariffs=None, action="select"):
    """Создает клавиатуру для выбора тарифов"""
    if selected_tariffs is None:
        selected_tariffs = []
    
    available_tariffs = ["1 месяц", "6 месяцев", "1 год"]
    keyboard = []
    
    for tariff in available_tariffs:
        prefix = "✅ " if tariff in selected_tariffs else ""
        keyboard.append([
            InlineKeyboardButton(
                text=f"{prefix}{tariff}", 
                callback_data=f"tariff_{tariff}"
            )
        ])
    
    button_text = "✅ Завершить выбор" if action == "select" else "✅ Сохранить тарифы"
    callback_data = "finish_tariffs" if action == "select" else "save_tariffs"
    
    keyboard.append([InlineKeyboardButton(text=button_text, callback_data=callback_data)])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def create_edit_mailing_keyboard(mailing_id: int):
    """Создает клавиатуру для редактирования рассылки"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Запустить/Остановить", callback_data=f"toggle_mailing_{mailing_id}")],
        [InlineKeyboardButton(text="📅 Изменить дату начала", callback_data=f"change_start_{mailing_id}")],
        [InlineKeyboardButton(text="📅 Изменить дату окончания", callback_data=f"change_end_{mailing_id}")],
        [InlineKeyboardButton(text="💰 Изменить тарифы", callback_data=f"change_tariffs_{mailing_id}")],
        [InlineKeyboardButton(text="📎 Изменить файлы", callback_data=f"change_files_{mailing_id}")],
        [InlineKeyboardButton(text="🗑️ Удалить рассылку", callback_data=f"delete_mailing_{mailing_id}")],
        [InlineKeyboardButton(text="🔙 Назад к списку", callback_data="bonus_planner")]
    ])

async def show_mailing_menu(message: Message):
    """Показывает меню рассылок"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Запланировать бонус", callback_data="create_bonus")],
        [InlineKeyboardButton(text="📋 Планер бонусов", callback_data="bonus_planner")]
    ])
    
    await message.answer(
        "🎁 <b>Управление бонусными рассылками</b>\n\n"
        "Выберите действие:",
        reply_markup=keyboard
    )

async def update_mailing_message(message: Message, mailing_id: int):
    """Обновляет сообщение с информацией о рассылке"""
    mailing = bonus_mailing.get_mailing_by_id(mailing_id)
    if not mailing:
        return
    
    tariffs = json.loads(mailing['tariffs'])
    file_paths = json.loads(mailing['file_paths']) if mailing['file_paths'] else []
    start_date = datetime.fromisoformat(mailing['start_date'])
    end_date = datetime.fromisoformat(mailing['end_date'])
    
    status_text = "🟢 Активна" if mailing['is_active'] else "🔴 Неактивна"
    
    await message.edit_text(
        f"✏️ <b>Редактирование рассылки #{mailing_id}</b>\n\n"
        f"Статус: {status_text}\n"
        f"Тарифы: {', '.join(tariffs)}\n"
        f"Начало: {start_date.strftime('%d.%m.%Y %H:%M')}\n"
        f"Окончание: {end_date.strftime('%d.%m.%Y %H:%M')}\n"
        f"Файлов: {len(file_paths)}\n\n"
        f"<b>Сообщение:</b>\n{mailing['message_text'][:200]}...",
        reply_markup=create_edit_mailing_keyboard(mailing_id)
    )


# Основные команды
@mailing_router.message(Command("bonus_mailing"))
async def bonus_mailing_command(message: Message):
    """Команда управления бонусными рассылками"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет прав для использования этой команды.")
        return
    
    await show_mailing_menu(message)

@mailing_router.message(Command("mailing_stats"))
async def mailing_stats(message: Message):
    """Статистика по рассылкам"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет прав для этой команды.")
        return
    
    with db.get_connection() as conn:
        cursor = conn.cursor()
        
        # Статистика по рассылкам
        cursor.execute('''
            SELECT 
                COUNT(*) as total_mailings,
                SUM(CASE WHEN is_active = 1 THEN 1 ELSE 0 END) as active_mailings,
                SUM(CASE WHEN is_active = 0 THEN 1 ELSE 0 END) as inactive_mailings
            FROM bonus_mailings
        ''')
        stats = cursor.fetchone()
        
        # Активные рассылки в текущий период
        cursor.execute('''
            SELECT id, start_date, end_date 
            FROM bonus_mailings 
            WHERE is_active = 1 
            AND datetime(start_date) <= datetime('now') 
            AND datetime(end_date) >= datetime('now')
        ''')
        current_mailings = cursor.fetchall()
        
        # Статистика отправок
        cursor.execute('''
            SELECT COUNT(DISTINCT user_id) as total_users_sent 
            FROM mailing_logs
        ''')
        sent_stats = cursor.fetchone()
        
        # Статистика по последним рассылкам
        cursor.execute('''
            SELECT mailing_id, COUNT(*) as sent_count
            FROM mailing_logs 
            GROUP BY mailing_id 
            ORDER BY sent_count DESC 
            LIMIT 5
        ''')
        top_mailings = cursor.fetchall()
    
    text = (
        f"📊 <b>Статистика рассылок</b>\n\n"
        f"📧 Всего рассылок: {stats[0]}\n"
        f"🟢 Активных: {stats[1]}\n"
        f"🔴 Неактивных: {stats[2]}\n"
        f"📅 Сейчас активны: {len(current_mailings)}\n"
        f"👥 Всего отправок: {sent_stats[0] if sent_stats else 0}\n\n"
    )
    
    if current_mailings:
        text += "<b>Текущие активные рассылки:</b>\n"
        for mailing in current_mailings:
            text += f"• #{mailing[0]} ({mailing[1][:10]} - {mailing[2][:10]})\n"
    
    if top_mailings:
        text += "\n<b>Топ рассылок по отправкам:</b>\n"
        for mailing in top_mailings:
            text += f"• #{mailing[0]}: {mailing[1]} отправок\n"
    
    await message.answer(text)

# Создание рассылки
@mailing_router.callback_query(F.data == "create_bonus")
async def create_bonus_start(callback: CallbackQuery, state: FSMContext):
    """Начало создания бонусной рассылки"""
    await state.set_state(CreateMailingStates.waiting_for_message)
    await callback.message.edit_text(
        "📝 <b>Создание бонусной рассылки</b>\n\n"
        "Отправьте сообщение в формате HTML. Вы можете использовать:\n"
        "• <b>жирный текст</b>\n"
        "• <i>курсив</i>\n"
        "• ссылки\n"
        "• эмодзи\n\n"
        "<i>Сообщение будет показано с предпросмотром для подтверждения.</i>"
    )
    await callback.answer()

@mailing_router.message(CreateMailingStates.waiting_for_message)
async def process_message_input(message: Message, state: FSMContext):
    """Обработка ввода сообщения"""
    # ИСПРАВЛЕНИЕ: используем message.text вместо message.html_text
    await state.update_data(message_text=message.text)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Подтвердить", callback_data="confirm_message")],
        [InlineKeyboardButton(text="🔄 Изменить", callback_data="change_message")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_mailing")]
    ])
    
    await message.answer(
        "👀 <b>Предпросмотр сообщения:</b>\n\n" + message.text,
        reply_markup=keyboard,
        parse_mode="HTML"  # Добавляем HTML парсинг для предпросмотра
    )
    await state.set_state(CreateMailingStates.confirm_message)


@mailing_router.callback_query(F.data == "confirm_message")
async def confirm_message(callback: CallbackQuery, state: FSMContext):
    """Подтверждение сообщения"""
    await state.set_state(CreateMailingStates.waiting_for_files)
    
    # Обновляем текст с информацией о необязательности файлов
    await callback.message.edit_text(
        "📎 <b>Прикрепите файлы (необязательно)</b>\n\n"
        "Вы можете отправить:\n"
        "• PDF файлы\n" 
        "• Изображения (JPG, PNG)\n\n"
        "Можно отправить несколько файлов.\n"
        "Если файлы не нужны, нажмите кнопку ниже.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Продолжить без файлов", callback_data="finish_files")]
        ])
    )
    await state.update_data(file_paths=[])
    await callback.answer()

@mailing_router.callback_query(F.data == "change_message")
async def change_message(callback: CallbackQuery, state: FSMContext):
    """Изменение сообщения"""
    await state.set_state(CreateMailingStates.waiting_for_message)
    await callback.message.edit_text("📝 Отправьте новое сообщение в формате HTML:")
    await callback.answer()

@mailing_router.message(CreateMailingStates.waiting_for_files, F.document | F.photo)
async def process_file_input(message: Message, state: FSMContext):
    """Обработка загрузки файлов и изображений"""
    try:
        data = await state.get_data()
        file_paths = data.get('file_paths', [])
        
        # Определяем тип контента
        if message.document:
            # Документы - только PDF
            if message.document.mime_type != 'application/pdf':
                await message.answer("❌ Для документов принимаются только PDF файлы.")
                return
            file_id = message.document.file_id
            file_name = message.document.file_name
            file_type = 'document'
            
        elif message.photo:
            # Изображения - берем самое большое фото
            file_id = message.photo[-1].file_id
            file_name = f"image_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
            file_type = 'photo'
        else:
            await message.answer("❌ Пожалуйста, отправляйте PDF файлы или изображения.")
            return
        
        # Сохраняем файл
        file = await message.bot.get_file(file_id)
        file_path = file.file_path
        
        # Скачиваем файл
        downloaded_file = await message.bot.download_file(file_path)
        
        # Сохраняем локально
        filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file_name}"
        local_path = os.path.join(MailingConfig.FILES_DIR, filename)
        
        with open(local_path, 'wb') as f:
            f.write(downloaded_file.read())
        
        file_paths.append(local_path)
        await state.update_data(file_paths=file_paths)
        
        await message.answer(f"✅ Файл '{file_name}' сохранен!")
        
    except Exception as e:
        await message.answer(f"❌ Ошибка при загрузке файла: {str(e)}")

@mailing_router.callback_query(F.data == "finish_files")
async def finish_files(callback: CallbackQuery, state: FSMContext):
    """Завершение загрузки файлов - файлы теперь необязательны"""
    data = await state.get_data()
    file_paths = data.get('file_paths', [])
    
    # УБИРАЕМ проверку на обязательность файлов
    # if not file_paths:
    #     await callback.answer("❌ Нужно добавить хотя бы один файл!", show_alert=True)
    #     return
    
    await state.set_state(CreateMailingStates.waiting_for_tariffs)
    
    # Сообщение меняем в зависимости от наличия файлов
    if file_paths:
        file_text = f"📎 Загружено файлов: {len(file_paths)}"
    else:
        file_text = "📎 Файлы не добавлены"
    
    await callback.message.edit_text(
        f"💰 <b>Выберите тарифы для рассылки</b>\n\n"
        f"{file_text}\n\n"
        "Можно выбрать несколько тарифов. После выбора нажмите 'Завершить выбор'.",
        reply_markup=create_tariffs_keyboard(action="select")
    )
    await state.update_data(selected_tariffs=[])
    await callback.answer()

@mailing_router.callback_query(F.data.startswith("tariff_"))
async def select_tariff(callback: CallbackQuery, state: FSMContext):
    """Выбор тарифа"""
    tariff = callback.data.replace("tariff_", "")
    data = await state.get_data()
    selected_tariffs = data.get('selected_tariffs', [])
    
    if tariff in selected_tariffs:
        selected_tariffs.remove(tariff)
    else:
        selected_tariffs.append(tariff)
    
    await state.update_data(selected_tariffs=selected_tariffs)
    
    action = "select" if "finish_tariffs" in callback.message.reply_markup.inline_keyboard[-1][0].callback_data else "edit"
    await callback.message.edit_reply_markup(reply_markup=create_tariffs_keyboard(selected_tariffs, action))
    await callback.answer()

@mailing_router.callback_query(F.data == "finish_tariffs")
async def finish_tariffs(callback: CallbackQuery, state: FSMContext):
    """Завершение выбора тарифов"""
    data = await state.get_data()
    selected_tariffs = data.get('selected_tariffs', [])
    
    if not selected_tariffs:
        await callback.answer("❌ Нужно выбрать хотя бы один тариф!", show_alert=True)
        return
    
    await state.set_state(CreateMailingStates.waiting_for_start_date)
    await callback.message.edit_text(
        "📅 <b>Укажите дату начала рассылки</b>\n\n"
        "Формат: ДД.ММ.ГГГГ ЧЧ:ММ\n"
        "Пример: 25.12.2024 10:00"
    )
    await callback.answer()

@mailing_router.message(CreateMailingStates.waiting_for_start_date)
async def process_start_date(message: Message, state: FSMContext):
    """Обработка даты начала"""
    try:
        start_date = datetime.strptime(message.text, "%d.%m.%Y %H:%M")
        await state.update_data(start_date=start_date)
        await state.set_state(CreateMailingStates.waiting_for_end_date)
        await message.answer(
            "📅 <b>Укажите дату окончания рассылки</b>\n\n"
            "Формат: ДД.ММ.ГГГГ ЧЧ:ММ\n"
            "Пример: 31.12.2024 23:59"
        )
    except ValueError:
        await message.answer("❌ Неверный формат даты! Используйте: ДД.ММ.ГГГГ ЧЧ:ММ")

@mailing_router.message(CreateMailingStates.waiting_for_end_date)
async def process_end_date(message: Message, state: FSMContext):
    """Обработка даты окончания"""
    try:
        end_date = datetime.strptime(message.text, "%d.%m.%Y %H:%M")
        data = await state.get_data()
        start_date = data['start_date']
        
        if end_date <= start_date:
            await message.answer("❌ Дата окончания должна быть позже даты начала!")
            return
        
        # Создаем рассылку
        mailing_id = bonus_mailing.create_mailing(
            message_text=data['message_text'],
            file_paths=data.get('file_paths', []),  # Может быть пустым
            tariffs=data['selected_tariffs'],
            start_date=start_date,
            end_date=end_date
        )
        
        # Формируем сообщение в зависимости от наличия файлов
        file_info = f"Файлов: {len(data.get('file_paths', []))}" if data.get('file_paths') else "Файлы: не добавлены"
        
        await message.answer(
            f"✅ <b>Бонусная рассылка создана!</b>\n\n"
            f"ID: {mailing_id}\n"
            f"Тарифы: {', '.join(data['selected_tariffs'])}\n"
            f"Начало: {start_date.strftime('%d.%m.%Y %H:%M')}\n"
            f"Окончание: {end_date.strftime('%d.%m.%Y %H:%M')}\n\n"
            f"{file_info}"
        )
        
        await state.clear()
        await show_mailing_menu(message)
        
    except ValueError:
        await message.answer("❌ Неверный формат даты! Используйте: ДД.ММ.ГГГГ ЧЧ:ММ")


# Планер бонусов
@mailing_router.callback_query(F.data == "bonus_planner")
async def show_bonus_planner(callback: CallbackQuery):
    """Показывает список всех рассылок"""
    mailings = bonus_mailing.get_all_mailings()
    
    if not mailings:
        await callback.message.edit_text(
            "📋 <b>Планер бонусов</b>\n\n"
            "Нет созданных рассылок.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")]
            ])
        )
        return
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    
    for mailing in mailings:
        status = "🟢" if mailing['is_active'] else "🔴"
        tariffs = json.loads(mailing['tariffs'])
        keyboard.inline_keyboard.append([
            InlineKeyboardButton(
                text=f"{status} Рассылка #{mailing['id']} ({', '.join(tariffs)})",
                callback_data=f"edit_mailing_{mailing['id']}"
            )
        ])
    
    keyboard.inline_keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")])
    
    await callback.message.edit_text(
        "📋 <b>Планер бонусов</b>\n\n"
        "Выберите рассылку для редактирования:",
        reply_markup=keyboard
    )
    await callback.answer()

@mailing_router.callback_query(F.data.startswith("edit_mailing_"))
async def edit_mailing_menu(callback: CallbackQuery, state: FSMContext = None):
    """Меню редактирования рассылки"""
    mailing_id = int(callback.data.replace("edit_mailing_", ""))
    mailing = bonus_mailing.get_mailing_by_id(mailing_id)
    
    if not mailing:
        await callback.answer("❌ Рассылка не найдена!", show_alert=True)
        return
    
    if state:
        await state.update_data(editing_mailing_id=mailing_id)
    
    await update_mailing_message(callback.message, mailing_id)
    await callback.answer()



# Обработчики действий редактирования
@mailing_router.callback_query(F.data.startswith("toggle_mailing_"))
async def toggle_mailing(callback: CallbackQuery):
    """Включение/выключение рассылки"""
    try:
        mailing_id = int(callback.data.replace("toggle_mailing_", ""))
        mailing = bonus_mailing.get_mailing_by_id(mailing_id)
        
        if not mailing:
            await callback.answer("❌ Рассылка не найдена!", show_alert=True)
            return
        
        new_status = not mailing['is_active']
        bonus_mailing.update_mailing(mailing_id, is_active=new_status)
        
        status_text = "активирована" if new_status else "деактивирована"
        await callback.answer(f"✅ Рассылка {status_text}!", show_alert=True)
        
        # Обновляем сообщение
        await update_mailing_message(callback.message, mailing_id)
        
    except Exception as e:
        await callback.answer("❌ Ошибка при обработке запроса", show_alert=True)
        print(f"Ошибка в toggle_mailing: {e}")

@mailing_router.callback_query(F.data.startswith("change_start_"))
async def change_start_date(callback: CallbackQuery, state: FSMContext):
    """Изменение даты начала"""
    mailing_id = int(callback.data.replace("change_start_", ""))
    await state.set_state(EditMailingStates.waiting_for_new_start_date)
    await state.update_data(editing_mailing_id=mailing_id)
    
    await callback.message.edit_text(
        "📅 <b>Введите новую дату начала</b>\n\n"
        "Формат: ДД.ММ.ГГГГ ЧЧ:ММ\n"
        "Пример: 25.12.2024 10:00"
    )
    await callback.answer()

@mailing_router.callback_query(F.data.startswith("change_end_"))
async def change_end_date(callback: CallbackQuery, state: FSMContext):
    """Изменение даты окончания"""
    mailing_id = int(callback.data.replace("change_end_", ""))
    await state.set_state(EditMailingStates.waiting_for_new_end_date)
    await state.update_data(editing_mailing_id=mailing_id)
    
    await callback.message.edit_text(
        "📅 <b>Введите новую дату окончания</b>\n\n"
        "Формат: ДД.ММ.ГГГГ ЧЧ:ММ\n"
        "Пример: 31.12.2024 23:59"
    )
    await callback.answer()

@mailing_router.callback_query(F.data.startswith("change_tariffs_"))
async def change_tariffs(callback: CallbackQuery, state: FSMContext):
    """Изменение тарифов"""
    mailing_id = int(callback.data.replace("change_tariffs_", ""))
    mailing = bonus_mailing.get_mailing_by_id(mailing_id)
    
    if not mailing:
        await callback.answer("❌ Рассылка не найдена!", show_alert=True)
        return
    
    current_tariffs = json.loads(mailing['tariffs'])
    await state.update_data(editing_mailing_id=mailing_id, selected_tariffs=current_tariffs)
    
    await callback.message.edit_text(
        "💰 <b>Измените тарифы для рассылки</b>\n\n"
        "Выберите нужные тарифы и нажмите 'Сохранить тарифы'.",
        reply_markup=create_tariffs_keyboard(current_tariffs, action="edit")
    )
    await callback.answer()

@mailing_router.callback_query(F.data == "save_tariffs")
async def save_tariffs(callback: CallbackQuery, state: FSMContext):
    """Сохранение измененных тарифов"""
    data = await state.get_data()
    mailing_id = data.get('editing_mailing_id')
    selected_tariffs = data.get('selected_tariffs', [])
    
    if not selected_tariffs:
        await callback.answer("❌ Нужно выбрать хотя бы один тариф!", show_alert=True)
        return
    
    bonus_mailing.update_mailing(mailing_id, tariffs=selected_tariffs)
    await callback.answer("✅ Тарифы обновлены!", show_alert=True)
    await state.clear()
    
    # ИСПРАВЛЕНИЕ: Не изменяем callback.data, а вызываем функцию напрямую
    await update_mailing_message(callback.message, mailing_id)


@mailing_router.callback_query(F.data.startswith("change_files_"))
async def change_files(callback: CallbackQuery, state: FSMContext):
    """Изменение файлов"""
    mailing_id = int(callback.data.replace("change_files_", ""))
    await state.set_state(EditMailingStates.waiting_for_new_files)
    await state.update_data(editing_mailing_id=mailing_id, file_paths=[])
    
    await callback.message.edit_text(
        "📎 <b>Добавьте новые файлы</b>\n\n"
        "Вы можете отправить:\n"
        "• PDF файлы\n"
        "• Изображения (JPG, PNG)\n\n"
        "Текущие файлы будут заменены.\n"
        "Когда закончите, нажмите кнопку ниже.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Сохранить файлы", callback_data="save_files")]
        ])
    )
    await callback.answer()

@mailing_router.callback_query(F.data == "save_files")
async def save_files(callback: CallbackQuery, state: FSMContext):
    """Сохранение файлов"""
    data = await state.get_data()
    mailing_id = data.get('editing_mailing_id')
    file_paths = data.get('file_paths', [])
    
    # Удаляем старые файлы
    mailing = bonus_mailing.get_mailing_by_id(mailing_id)
    if mailing and mailing['file_paths']:
        old_files = json.loads(mailing['file_paths'])
        for old_file in old_files:
            try:
                if os.path.exists(old_file):
                    os.remove(old_file)
            except:
                pass
    
    bonus_mailing.update_mailing(mailing_id, file_paths=file_paths)
    await callback.answer("✅ Файлы обновлены!", show_alert=True)
    await state.clear()
    
    # ИСПРАВЛЕНИЕ: Используем update_mailing_message вместо изменения callback.data
    await update_mailing_message(callback.message, mailing_id)


# # Создаем вспомогательную функцию для вызова edit_mailing_menu
# async def edit_mailing_menu_from_callback(callback: CallbackQuery, mailing_id: int, state: FSMContext):
#     """Вспомогательная функция для вызова edit_mailing_menu"""
#     # Создаем временный callback с нужными данными
#     class TempCallback:
#         def __init__(self, original_callback, mailing_id):
#             self.message = original_callback.message
#             self.data = f"edit_mailing_{mailing_id}"
#             self.id = original_callback.id
#             self.from_user = original_callback.from_user
    
#     temp_callback = TempCallback(callback, mailing_id)
#     await edit_mailing_menu(temp_callback, state)

@mailing_router.callback_query(F.data.startswith("delete_mailing_"))
async def delete_mailing(callback: CallbackQuery):
    """Удаление рассылки"""
    mailing_id = int(callback.data.replace("delete_mailing_", ""))
    mailing = bonus_mailing.get_mailing_by_id(mailing_id)
    
    if not mailing:
        await callback.answer("❌ Рассылка не найдена!", show_alert=True)
        return
    
    # Удаляем файлы
    if mailing['file_paths']:
        file_paths = json.loads(mailing['file_paths'])
        for file_path in file_paths:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
            except:
                pass
    
    bonus_mailing.delete_mailing(mailing_id)
    await callback.answer("✅ Рассылка удалена!", show_alert=True)
    await show_bonus_planner(callback)

# Обработчики состояний для редактирования
@mailing_router.message(EditMailingStates.waiting_for_new_start_date)
async def process_new_start_date(message: Message, state: FSMContext):
    """Обработка новой даты начала"""
    try:
        start_date = datetime.strptime(message.text, "%d.%m.%Y %H:%M")
        data = await state.get_data()
        mailing_id = data['editing_mailing_id']
        
        bonus_mailing.update_mailing(mailing_id, start_date=start_date)
        await message.answer("✅ Дата начала обновлена!")
        await state.clear()
        
        # Возвращаемся к меню редактирования через прямое создание сообщения
        await update_mailing_message(message, mailing_id)
        
    except ValueError:
        await message.answer("❌ Неверный формат даты! Используйте: ДД.ММ.ГГГГ ЧЧ:ММ")

@mailing_router.message(EditMailingStates.waiting_for_new_end_date)
async def process_new_end_date(message: Message, state: FSMContext):
    """Обработка новой даты окончания"""
    try:
        end_date = datetime.strptime(message.text, "%d.%m.%Y %H:%M")
        data = await state.get_data()
        mailing_id = data['editing_mailing_id']
        
        # Проверяем что дата окончания позже даты начала
        mailing = bonus_mailing.get_mailing_by_id(mailing_id)
        start_date = datetime.fromisoformat(mailing['start_date'])
        
        if end_date <= start_date:
            await message.answer("❌ Дата окончания должна быть позже даты начала!")
            return
        
        bonus_mailing.update_mailing(mailing_id, end_date=end_date)
        await message.answer("✅ Дата окончания обновлена!")
        await state.clear()
        
        # Возвращаемся к меню редактирования через прямое создание сообщения
        await update_mailing_message(message, mailing_id)
        
    except ValueError:
        await message.answer("❌ Неверный формат даты! Используйте: ДД.ММ.ГГГГ ЧЧ:ММ")

@mailing_router.message(EditMailingStates.waiting_for_new_files, F.document | F.photo)
async def process_new_file_input(message: Message, state: FSMContext):
    """Обработка загрузки новых файлов и изображений"""
    data = await state.get_data()
    file_paths = data.get('file_paths', [])
    
    # Определяем тип контента
    if message.document:
        # Документы - только PDF
        if message.document.mime_type != 'application/pdf':
            await message.answer("❌ Для документов принимаются только PDF файлы.")
            return
        file_id = message.document.file_id
        file_name = message.document.file_name
        
    elif message.photo:
        # Изображения - берем самое большое фото
        file_id = message.photo[-1].file_id
        file_name = f"image_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
    else:
        await message.answer("❌ Пожалуйста, отправляйте PDF файлы или изображения.")
        return
    
    # Сохраняем файл
    file = await message.bot.get_file(file_id)
    file_path = file.file_path
    
    # Скачиваем файл
    downloaded_file = await message.bot.download_file(file_path)
    
    # Сохраняем локально
    filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file_name}"
    local_path = os.path.join(MailingConfig.FILES_DIR, filename)
    
    with open(local_path, 'wb') as f:
        f.write(downloaded_file.read())
    
    file_paths.append(local_path)
    await state.update_data(file_paths=file_paths)
    
    await message.answer(f"✅ Файл '{file_name}' сохранен!")

# Навигация назад
@mailing_router.callback_query(F.data == "back_to_menu")
async def back_to_menu(callback: CallbackQuery, state: FSMContext):
    """Возврат в главное меню"""
    await state.clear()
    await show_mailing_menu(callback.message)
    await callback.answer()


@mailing_router.callback_query(F.data == "cancel_mailing")
async def cancel_mailing(callback: CallbackQuery, state: FSMContext):
    """Отмена создания рассылки"""
    await state.clear()
    await callback.message.edit_text("❌ Создание рассылки отменено.")
    await show_mailing_menu(callback.message)
    await callback.answer()


# Команды отправки рассылок
@mailing_router.message(Command("send_mailings"))
async def send_mailings_now(message: Message):
    """Ручная отправка активных рассылок"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет прав для этой команды.")
        return
    
    from mailing.sender import MailingSender
    sender = MailingSender(message.bot)
    
    await message.answer("🔄 Начинаю отправку активных рассылок...")
    await sender.send_active_mailings()
    await message.answer("✅ Отправка завершена!")

@mailing_router.message(Command("test_mailing"))
async def test_mailing_now(message: Message):
    """Тестовая отправка активных рассылок"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет прав для этой команды.")
        return
    
    await message.answer("🔄 Начинаю тестовую отправку активных рассылок...")
    
    try:
        # Получаем активные рассылки через модель
        mailings = bonus_mailing.get_all_mailings()
        current_time = datetime.now()
        
        active_mailings = []
        for mailing in mailings:
            if not mailing['is_active']:
                continue
            
            start_date = datetime.fromisoformat(mailing['start_date'])
            end_date = datetime.fromisoformat(mailing['end_date'])
            
            if start_date <= current_time <= end_date:
                active_mailings.append(mailing)
        
        if not active_mailings:
            await message.answer("❌ Нет активных рассылок в текущий период времени")
            return
        
        await message.answer(f"📧 Найдено {len(active_mailings)} активных рассылок")
        
        # Отправляем каждую рассылку
        for mailing in active_mailings:
            # Используем метод модели для получения пользователей
            with db.get_connection() as conn:
                cursor = conn.cursor()
                
                tariffs = json.loads(mailing['tariffs'])
                placeholders = ','.join(['?'] * len(tariffs))
                
                cursor.execute(f'''
                    SELECT DISTINCT user_id 
                    FROM payments 
                    WHERE tariff_name IN ({placeholders}) 
                    AND status = 'succeeded'
                    AND datetime(valid_until) > datetime('now')
                ''', tariffs)
                
                users = cursor.fetchall()
            
            await message.answer(
                f"📤 Рассылка #{mailing['id']}\n"
                f"👥 Найдено пользователей: {len(users)}\n"
                f"📅 Период: {mailing['start_date'][:16]} - {mailing['end_date'][:16]}\n"
                f"💰 Тарифы: {', '.join(tariffs)}"
            )
            
            # Тестовая отправка только админу С ФАЙЛАМИ (как в реальной рассылке)
            try:
                # Отправляем текст
                await message.bot.send_message(
                    chat_id=message.from_user.id, 
                    text=f"📧 <b>Тест рассылки #{mailing['id']}</b>\n\n{mailing['message_text']}",
                    parse_mode='HTML'
                )
                
                # Отправляем файлы если есть - ТАК ЖЕ КАК В РЕАЛЬНОЙ РАССЫЛКЕ
                if mailing['file_paths']:
                    files = json.loads(mailing['file_paths'])
                    for file_path in files:
                        if os.path.exists(file_path):
                            try:
                                # Определяем тип файла по расширению
                                file_ext = os.path.splitext(file_path)[1].lower()
                                
                                with open(file_path, 'rb') as file:
                                    file_data = file.read()
                                
                                from aiogram.types import BufferedInputFile
                                input_file = BufferedInputFile(
                                    file_data,
                                    filename=os.path.basename(file_path)
                                )
                                
                                if file_ext in ['.jpg', '.jpeg', '.png', '.gif']:
                                    # Отправляем как фото
                                    await message.bot.send_photo(
                                        chat_id=message.from_user.id,
                                        photo=input_file
                                    )
                                else:
                                    # Отправляем как документ
                                    await message.bot.send_document(
                                        chat_id=message.from_user.id,
                                        document=input_file
                                    )
                                    
                            except Exception as file_error:
                                await message.answer(f"❌ Ошибка отправки файла: {str(file_error)}")
                
                await message.answer(f"✅ Тестовая отправка для рассылки #{mailing['id']} завершена")
                
            except Exception as e:
                await message.answer(f"❌ Ошибка отправки рассылки #{mailing['id']}: {str(e)}")
        
        await message.answer("🎉 Тестовая отправка завершена!")
        
    except Exception as e:
        await message.answer(f"❌ Общая ошибка: {str(e)}")


@mailing_router.message(Command("final_test_mailing"))
async def final_test_mailing(message: Message):
    """Финальная тестовая отправка с исправлениями"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет прав для этой команды.")
        return
    
    await message.answer("🔄 Начинаю финальную тестовую отправку...")
    
    try:
        # Получаем активные рассылки через модель
        mailings = bonus_mailing.get_all_mailings()
        current_time = datetime.now()
        
        active_mailings = []
        for mailing in mailings:
            if not mailing['is_active']:
                continue
            
            start_date = datetime.fromisoformat(mailing['start_date'])
            end_date = datetime.fromisoformat(mailing['end_date'])
            
            if start_date <= current_time <= end_date:
                active_mailings.append(mailing)
        
        if not active_mailings:
            await message.answer("❌ Нет активных рассылок в текущий период времени")
            return
        
        await message.answer(f"📧 Найдено {len(active_mailings)} активных рассылок")
        
        for mailing in active_mailings:
            with db.get_connection() as conn:
                cursor = conn.cursor()
                
                tariffs = json.loads(mailing['tariffs'])
                placeholders = ','.join(['?'] * len(tariffs))
                
                # ИСПРАВЛЕННЫЙ ЗАПРОС
                cursor.execute(f'''
                    SELECT DISTINCT user_id 
                    FROM payments 
                    WHERE tariff_name IN ({placeholders}) 
                    AND status = 'succeeded'
                    AND datetime(valid_until) > datetime('now')
                ''', tariffs)
                
                users = cursor.fetchall()
            
            await message.answer(
                f"📤 Рассылка #{mailing['id']}\n"
                f"👥 Найдено пользователей: {len(users)}\n"
                f"📅 Период: {mailing['start_date'][:16]} - {mailing['end_date'][:16]}\n"
                f"💰 Тарифы: {', '.join(tariffs)}"
            )
            
            # Отправляем тестовое сообщение С ФАЙЛАМИ (как в реальной рассылке)
            try:
                # Текст
                await message.bot.send_message(
                    chat_id=message.from_user.id,
                    text=f"📧 <b>Тест рассылки #{mailing['id']}</b>\n\n{mailing['message_text']}",
                    parse_mode='HTML'
                )
                
                # Файлы - ТАК ЖЕ КАК В РЕАЛЬНОЙ РАССЫЛКЕ
                if mailing['file_paths']:
                    files = json.loads(mailing['file_paths'])
                    for file_path in files:
                        if os.path.exists(file_path):
                            try:
                                # Определяем тип файла по расширению
                                file_ext = os.path.splitext(file_path)[1].lower()
                                
                                with open(file_path, 'rb') as file:
                                    file_data = file.read()
                                
                                from aiogram.types import BufferedInputFile
                                input_file = BufferedInputFile(
                                    file_data,
                                    filename=os.path.basename(file_path)
                                )
                                
                                if file_ext in ['.jpg', '.jpeg', '.png', '.gif']:
                                    # Отправляем как фото
                                    await message.bot.send_photo(
                                        chat_id=message.from_user.id,
                                        photo=input_file
                                    )
                                else:
                                    # Отправляем как документ
                                    await message.bot.send_document(
                                        chat_id=message.from_user.id,
                                        document=input_file
                                    )
                                    
                            except Exception as file_error:
                                await message.answer(f"❌ Ошибка отправки файла: {str(file_error)}")
                
                await message.answer(f"✅ Рассылка #{mailing['id']} отправлена успешно!")
                
            except Exception as e:
                await message.answer(f"❌ Ошибка отправки: {str(e)}")
        
        await message.answer("🎉 Финальная тестовая отправка завершена!")
        
    except Exception as e:
        await message.answer(f"❌ Общая ошибка: {str(e)}")



@mailing_router.message(Command("start_mailing"))
async def start_mailing(message: Message):
    """Запуск реальной рассылки всем пользователям"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет прав для этой команды.")
        return
    
    await message.answer("🚀 Запуск реальной рассылки...")
    
    try:
        # Получаем активные рассылки через модель
        mailings = bonus_mailing.get_all_mailings()
        current_time = datetime.now()
        
        active_mailings = []
        for mailing in mailings:
            if not mailing['is_active']:
                continue
            
            start_date = datetime.fromisoformat(mailing['start_date'])
            end_date = datetime.fromisoformat(mailing['end_date'])
            
            if start_date <= current_time <= end_date:
                active_mailings.append(mailing)
        
        if not active_mailings:
            await message.answer("❌ Нет активных рассылок в текущий период времени")
            return
        
        await message.answer(f"📧 Найдено {len(active_mailings)} активных рассылок")
        
        total_sent = 0
        total_errors = 0
        
        for mailing in active_mailings:
            with db.get_connection() as conn:
                cursor = conn.cursor()
                
                tariffs = json.loads(mailing['tariffs'])
                placeholders = ','.join(['?'] * len(tariffs))
                
                cursor.execute(f'''
                    SELECT DISTINCT user_id 
                    FROM payments 
                    WHERE tariff_name IN ({placeholders}) 
                    AND status = 'succeeded'
                    AND datetime(valid_until) > datetime('now')
                ''', tariffs)
                
                users = cursor.fetchall()
            
            await message.answer(
                f"📤 Рассылка #{mailing['id']}\n"
                f"👥 Пользователей для отправки: {len(users)}\n"
                f"📅 Период: {mailing['start_date'][:16]} - {mailing['end_date'][:16]}\n"
                f"💰 Тарифы: {', '.join(tariffs)}"
            )
            
            mailing_sent = 0
            mailing_errors = 0
            
            # Отправляем каждому пользователю
            for user in users:
                user_id = user[0]
                
                try:
                    # Сначала отправляем текст отдельно
                    await message.bot.send_message(
                        chat_id=user_id,
                        text=mailing['message_text'],
                        parse_mode='HTML'
                    )
                    
                    # Затем отправляем файлы если есть с поддержкой изображений
                    if mailing['file_paths']:
                        files = json.loads(mailing['file_paths'])
                        for file_path in files:
                            if os.path.exists(file_path):
                                try:
                                    # Определяем тип файла по расширению
                                    file_ext = os.path.splitext(file_path)[1].lower()
                                    
                                    with open(file_path, 'rb') as file:
                                        file_data = file.read()
                                    
                                    from aiogram.types import BufferedInputFile
                                    input_file = BufferedInputFile(
                                        file_data,
                                        filename=os.path.basename(file_path)
                                    )
                                    
                                    if file_ext in ['.jpg', '.jpeg', '.png', '.gif']:
                                        # Отправляем как фото
                                        await message.bot.send_photo(
                                            chat_id=user_id,
                                            photo=input_file
                                        )
                                    else:
                                        # Отправляем как документ
                                        await message.bot.send_document(
                                            chat_id=user_id,
                                            document=input_file
                                        )
                                        
                                except Exception as file_error:
                                    print(f"Ошибка отправки файла пользователю {user_id}: {str(file_error)}")
                    
                    mailing_sent += 1
                    total_sent += 1
                    
                    # Небольшая задержка чтобы не спамить
                    await asyncio.sleep(0.1)
                    
                except Exception as e:
                    mailing_errors += 1
                    total_errors += 1
                    print(f"Ошибка отправки пользователю {user_id}: {str(e)}")
            
            await message.answer(
                f"📊 Результаты рассылки #{mailing['id']}:\n"
                f"✅ Успешно отправлено: {mailing_sent}\n"
                f"❌ Ошибок: {mailing_errors}"
            )
        
        # Финальная статистика
        await message.answer(
            f"🎉 <b>Рассылка завершена!</b>\n\n"
            f"📊 <b>Общая статистика:</b>\n"
            f"✅ Успешно отправлено: {total_sent}\n"
            f"❌ Ошибок: {total_errors}\n"
            f"📧 Обработано рассылок: {len(active_mailings)}",
            parse_mode='HTML'
        )
    except Exception as e:
        await message.answer(f"❌ Общая ошибка: {str(e)}")




@mailing_router.message(Command("test_mailing_with_files"))
async def test_mailing_with_files(message: Message):
    """Тестовая отправка рассылки с файлами - исправленная версия"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет прав для этой команды.")
        return
    
    await message.answer("🔄 Тестирую отправку с файлами...")
    
    try:
        # Получаем все рассылки
        mailings = bonus_mailing.get_all_mailings()
        current_time = datetime.now()
        
        # Фильтруем активные рассылки
        active_mailings = []
        for mailing in mailings:
            if not mailing['is_active']:
                continue
            
            start_date = datetime.fromisoformat(mailing['start_date'])
            end_date = datetime.fromisoformat(mailing['end_date'])
            
            if start_date <= current_time <= end_date:
                active_mailings.append(mailing)
        
        if not active_mailings:
            await message.answer("❌ Нет активных рассылок для тестирования")
            return
        
        # Тестируем каждую активную рассылку
        for mailing in active_mailings:
            mailing_id = mailing['id']
            await message.answer(f"📧 Тестирую рассылку #{mailing_id}")
            
            try:
                # 1. Отправляем основной текст рассылки
                await message.answer("📤 Отправляю текст рассылки...")
                await message.bot.send_message(
                    chat_id=message.from_user.id,
                    text=f"📧 Тест рассылки #{mailing_id}\n\n{mailing['message_text']}",
                    parse_mode='HTML'
                )
                
                # 2. Отправляем файлы с поддержкой изображений - ИСПРАВЛЕННАЯ ЧАСТЬ
                if mailing['file_paths']:
                    files = json.loads(mailing['file_paths'])
                    await message.answer(f"📎 Отправляю {len(files)} файлов...")
                    
                    for i, file_path in enumerate(files, 1):
                        if not os.path.exists(file_path):
                            await message.answer(f"❌ Файл не найден: {file_path}")
                            continue
                        
                        try:
                            await message.answer(f"📤 Отправляю файл {i}: {os.path.basename(file_path)}")
                            
                            # Используем FSInputFile вместо BufferedInputFile для тестовой отправки
                            from aiogram.types import FSInputFile
                            
                            # Определяем тип файла по расширению
                            file_ext = os.path.splitext(file_path)[1].lower()
                            
                            if file_ext in ['.jpg', '.jpeg', '.png', '.gif']:
                                # Отправляем как фото
                                input_file = FSInputFile(file_path)
                                await message.bot.send_photo(
                                    chat_id=message.from_user.id,
                                    photo=input_file,
                                    caption=f"Файл {i}: {os.path.basename(file_path)}"
                                )
                            else:
                                # Отправляем как документ
                                input_file = FSInputFile(file_path)
                                await message.bot.send_document(
                                    chat_id=message.from_user.id,
                                    document=input_file,
                                    caption=f"Файл {i}: {os.path.basename(file_path)}"
                                )
                            
                            await message.answer(f"✅ Файл {i} успешно отправлен")
                            
                        except Exception as file_error:
                            await message.answer(f"❌ Ошибка отправки файла {i}: {str(file_error)}")
                            
                            # Пробуем альтернативный способ
                            try:
                                await message.answer("🔄 Пробую альтернативный способ отправки...")
                                # Просто передаем путь как строку
                                if file_ext in ['.jpg', '.jpeg', '.png', '.gif']:
                                    await message.bot.send_photo(
                                        chat_id=message.from_user.id,
                                        photo=file_path,
                                        caption=f"Альтернативный способ: {os.path.basename(file_path)}"
                                    )
                                else:
                                    await message.bot.send_document(
                                        chat_id=message.from_user.id,
                                        document=file_path,
                                        caption=f"Альтернативный способ: {os.path.basename(file_path)}"
                                    )
                                await message.answer("✅ Альтернативный способ сработал")
                            except Exception as alt_error:
                                await message.answer(f"❌ Альтернативный способ тоже не сработал: {str(alt_error)}")
                else:
                    await message.answer("ℹ️ В этой рассылке нет прикрепленных файлов")
                
                await message.answer(f"✅ Тестирование рассылки #{mailing_id} завершено\n")
                
            except Exception as mailing_error:
                await message.answer(f"❌ Ошибка тестирования рассылки #{mailing_id}: {str(mailing_error)}")
        
        await message.answer("🎉 Тестирование всех рассылок завершено!")
        
    except Exception as e:
        await message.answer(f"❌ Общая ошибка тестирования: {str(e)}")



@mailing_router.message(Command("start_real_mailing"))
async def start_real_mailing(message: Message):
    """Запуск реальной рассылки по оплаченным тарифам"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет прав для этой команды.")
        return
    
    await message.answer("🔄 Запускаю реальную рассылку по оплаченным тарифам...")
    
    try:
        # Получаем активные рассылки
        mailings = bonus_mailing.get_all_mailings()
        current_time = datetime.now()
        
        active_mailings = []
        for mailing in mailings:
            if not mailing['is_active']:
                continue
            
            start_date = datetime.fromisoformat(mailing['start_date'])
            end_date = datetime.fromisoformat(mailing['end_date'])
            
            if start_date <= current_time <= end_date:
                active_mailings.append(mailing)
        
        if not active_mailings:
            await message.answer("❌ Нет активных рассылок в текущий период")
            return
        
        total_sent = 0
        total_errors = 0
        total_already_sent = 0
        
        for mailing in active_mailings:
            mailing_id = mailing['id']
            tariffs = json.loads(mailing['tariffs'])
            
            await message.answer(
                f"📧 Рассылка #{mailing_id}\n"
                f"💰 Тарифы: {', '.join(tariffs)}\n"
                f"📅 Период: {mailing['start_date'][:16]} - {mailing['end_date'][:16]}"
            )
            
            # Получаем пользователей, оплативших эти тарифы
            with db.get_connection() as conn:
                cursor = conn.cursor()
                
                placeholders = ','.join(['?'] * len(tariffs))
                cursor.execute(f'''
                    SELECT DISTINCT user_id 
                    FROM payments 
                    WHERE tariff_name IN ({placeholders}) 
                    AND status = 'succeeded'
                    AND datetime(valid_until) > datetime('now')
                ''', tariffs)
                
                users = cursor.fetchall()
            
            if not users:
                await message.answer(f"❌ Нет пользователей с оплаченными тарифами: {', '.join(tariffs)}")
                continue
            
            await message.answer(f"👥 Найдено пользователей: {len(users)}")
            
            mailing_sent = 0
            mailing_errors = 0
            mailing_already_sent = 0
            
            # Отправляем каждому пользователю
            for i, user in enumerate(users, 1):
                user_id = user[0]
                
                # Проверяем, не отправляли ли уже эту рассылку пользователю
                if bonus_mailing.is_mailing_sent_to_user(mailing_id, user_id):
                    mailing_already_sent += 1
                    total_already_sent += 1
                    continue
                
                try:
                    # Отправляем текст сообщения
                    await message.bot.send_message(
                        chat_id=user_id,
                        text=mailing['message_text'],
                        parse_mode='HTML'
                    )
                    
                    # Отправляем файлы с поддержкой изображений
                    if mailing['file_paths']:
                        files = json.loads(mailing['file_paths'])
                        for file_path in files:
                            if os.path.exists(file_path):
                                try:
                                    # Определяем тип файла по расширению
                                    file_ext = os.path.splitext(file_path)[1].lower()
                                    
                                    with open(file_path, 'rb') as file:
                                        file_data = file.read()
                                    
                                    from aiogram.types import BufferedInputFile
                                    input_file = BufferedInputFile(
                                        file_data,
                                        filename=os.path.basename(file_path)
                                    )
                                    
                                    if file_ext in ['.jpg', '.jpeg', '.png', '.gif']:
                                        # Отправляем как фото
                                        await message.bot.send_photo(
                                            chat_id=user_id,
                                            photo=input_file
                                        )
                                    else:
                                        # Отправляем как документ
                                        await message.bot.send_document(
                                            chat_id=user_id,
                                            document=input_file
                                        )
                                        
                                except Exception as file_error:
                                    logger.error(f"Ошибка отправки файла пользователю {user_id}: {file_error}")
                                    bonus_mailing.log_mailing_sent(
                                        mailing_id, user_id, 'error', 
                                        f"File error: {str(file_error)}"
                                    )
                                    mailing_errors += 1
                                    total_errors += 1
                    
                    # Логируем успешную отправку
                    bonus_mailing.log_mailing_sent(mailing_id, user_id, 'sent')
                    mailing_sent += 1
                    total_sent += 1
                    
                    # Прогресс каждые 10 пользователей
                    if i % 10 == 0:
                        await message.answer(f"📊 Прогресс: {i}/{len(users)} отправлено")
                    
                    # Небольшая задержка чтобы не спамить
                    await asyncio.sleep(0.1)
                    
                except Exception as e:
                    # Логируем ошибку
                    bonus_mailing.log_mailing_sent(mailing_id, user_id, 'error', str(e))
                    mailing_errors += 1
                    total_errors += 1
                    logger.error(f"Ошибка отправки пользователю {user_id}: {e}")
            
            await message.answer(
                f"📊 Результаты рассылки #{mailing_id}:\n"
                f"✅ Успешно отправлено: {mailing_sent}\n"
                f"🔄 Уже было отправлено: {mailing_already_sent}\n"
                f"❌ Ошибок: {mailing_errors}"
            )
        
        # Финальная статистика
        await message.answer(
            f"🎉 <b>Рассылка завершена!</b>\n\n"
            f"📊 <b>Общая статистика:</b>\n"
            f"✅ Успешно отправлено: {total_sent}\n"
            f"🔄 Уже было отправлено: {total_already_sent}\n"
            f"❌ Ошибок: {total_errors}\n"
            f"📧 Обработано рассылок: {len(active_mailings)}",
            parse_mode='HTML'
        )
        
    except Exception as e:
        await message.answer(f"❌ Общая ошибка рассылки: {str(e)}")




@mailing_router.message(Command("mailing_stats_detailed"))
async def mailing_stats_detailed(message: Message):
    """Детальная статистика по отправкам рассылок"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет прав для этой команды.")
        return
    
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            # Статистика по рассылкам
            cursor.execute('''
                SELECT 
                    bm.id,
                    bm.message_text,
                    COUNT(ml.id) as total_sent,
                    SUM(CASE WHEN ml.status = 'sent' THEN 1 ELSE 0 END) as success_sent,
                    SUM(CASE WHEN ml.status = 'error' THEN 1 ELSE 0 END) as error_sent
                FROM bonus_mailings bm
                LEFT JOIN mailing_logs ml ON bm.id = ml.mailing_id
                GROUP BY bm.id
                ORDER BY bm.created_at DESC
            ''')
            
            stats = cursor.fetchall()
            
            if not stats:
                await message.answer("📊 Нет данных по рассылкам")
                return
            
            text = "📊 <b>Детальная статистика рассылок</b>\n\n"
            
            for stat in stats:
                mailing_id, message_text, total, success, errors = stat
                preview = message_text[:50] + "..." if len(message_text) > 50 else message_text
                
                text += (
                    f"📧 <b>Рассылка #{mailing_id}</b>\n"
                    f"📝 {preview}\n"
                    f"✅ Успешно: {success or 0}\n"
                    f"❌ Ошибок: {errors or 0}\n"
                    f"📤 Всего отправок: {total or 0}\n"
                    f"────────────────────\n\n"
                )
            
            await message.answer(text, parse_mode='HTML')
            
    except Exception as e:
        await message.answer(f"❌ Ошибка получения статистики: {str(e)}")


@mailing_router.message(Command("check_mailing_users"))
async def check_mailing_users(message: Message):
    """Проверка пользователей для активных рассылок"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет прав для этой команды.")
        return
    
    try:
        # Получаем активные рассылки
        mailings = bonus_mailing.get_all_mailings()
        current_time = datetime.now()
        
        active_mailings = []
        for mailing in mailings:
            if not mailing['is_active']:
                continue
            
            start_date = datetime.fromisoformat(mailing['start_date'])
            end_date = datetime.fromisoformat(mailing['end_date'])
            
            if start_date <= current_time <= end_date:
                active_mailings.append(mailing)
        
        if not active_mailings:
            await message.answer("❌ Нет активных рассылок в текущий период")
            return
        
        text = "🔍 <b>Проверка пользователей для активных рассылок</b>\n\n"
        
        for mailing in active_mailings:
            mailing_id = mailing['id']
            tariffs = json.loads(mailing['tariffs'])
            
            with db.get_connection() as conn:
                cursor = conn.cursor()
                
                placeholders = ','.join(['?'] * len(tariffs))
                cursor.execute(f'''
                    SELECT DISTINCT user_id 
                    FROM payments 
                    WHERE tariff_name IN ({placeholders}) 
                    AND status = 'succeeded'
                    AND datetime(valid_until) > datetime('now')
                ''', tariffs)
                
                users = cursor.fetchall()
            
            text += (
                f"📧 <b>Рассылка #{mailing_id}</b>\n"
                f"💰 Тарифы: {', '.join(tariffs)}\n"
                f"👥 Пользователей: {len(users)}\n"
                f"📅 Период: {mailing['start_date'][:16]} - {mailing['end_date'][:16]}\n\n"
            )
            
            if users:
                text += "<b>Пользователи:</b>\n"
                for user in users[:5]:  # Показываем первых 5
                    text += f"• ID: {user[0]}\n"
                if len(users) > 5:
                    text += f"• ... и еще {len(users) - 5}\n"
            else:
                text += "❌ <b>Нет подходящих пользователей!</b>\n"
            
            text += "\n" + "─" * 30 + "\n\n"
        
        await message.answer(text, parse_mode='HTML')
        
    except Exception as e:
        await message.answer(f"❌ Ошибка проверки: {str(e)}")


# Вспомогательные команды
@mailing_router.message(Command("create_test_mailing"))
async def create_test_mailing(message: Message):
    """Создает тестовую рассылку"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет прав для этой команды.")
        return
    
    try:
        # Создаем тестовую рассылку на ближайшие 2 часа
        from datetime import datetime, timedelta
        start_date = datetime.now()
        end_date = start_date + timedelta(hours=2)
        
        mailing_id = bonus_mailing.create_mailing(
            message_text="🎉 <b>Тестовая рассылка</b>\n\nЭто тестовое сообщение для проверки работы системы рассылок!",
            file_paths=[],  # Без файлов
            tariffs=["1 месяц", "6 месяцев"],
            start_date=start_date,
            end_date=end_date
        )
        
        await message.answer(
            f"✅ Тестовая рассылка создана!\n"
            f"ID: {mailing_id}\n"
            f"Период: {start_date.strftime('%H:%M')} - {end_date.strftime('%H:%M')}\n\n"
            f"Теперь используй команду /test_mailing для отправки"
        )

    except Exception as e:
        await message.answer(f"❌ Ошибка создания тестовой рассылки: {str(e)}")

@mailing_router.message(Command("cleanup_mailings"))
async def cleanup_mailings(message: Message):
    """Очистка старых рассылок и файлов"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет прав для этой команды.")
        return
    
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            # Находим рассылки, которые закончились более 30 дней назад
            cursor.execute('''
                SELECT id, file_paths 
                FROM bonus_mailings 
                WHERE datetime(end_date) < datetime('now', '-30 days')
            ''')
            old_mailings = cursor.fetchall()
            
            deleted_count = 0
            file_count = 0
            
            for mailing in old_mailings:
                mailing_id = mailing[0]
                file_paths = json.loads(mailing[1]) if mailing[1] else []
                
                # Удаляем файлы
                for file_path in file_paths:
                    try:
                        if os.path.exists(file_path):
                            os.remove(file_path)
                            file_count += 1
                    except Exception as e:
                        print(f"Ошибка удаления файла {file_path}: {e}")
                
                # Удаляем рассылку из БД
                cursor.execute('DELETE FROM bonus_mailings WHERE id = ?', (mailing_id,))
                deleted_count += 1
            
            conn.commit()
        
        await message.answer(
            f"🧹 <b>Очистка завершена</b>\n\n"
            f"🗑️ Удалено рассылок: {deleted_count}\n"
            f"📎 Удалено файлов: {file_count}"
        )
        
    except Exception as e:
        await message.answer(f"❌ Ошибка очистки: {str(e)}")

@mailing_router.message(Command("mailing_help"))
async def mailing_help(message: Message):
    """Справка по командам рассылок"""
    help_text = """
🎁 <b>Команды управления бонусными рассылками</b>

<b>Основные команды:</b>
/bonus_mailing - Главное меню рассылок
/mailing_stats - Статистика по рассылкам
/send_mailings - Ручная отправка активных рассылок
/start_mailing - Запуск реальной рассылки

<b>Тестирование:</b>
/test_mailing - Тестовая отправка активных рассылок
/final_test_mailing - Финальная тестовая отправка
/test_mailing_with_files - Тест с файлами
/create_test_mailing - Создать тестовую рассылку

<b>Администрирование:</b>
/cleanup_mailings - Очистка старых рассылок
/mailing_help - Эта справка

<b>Процесс создания:</b>
1. Используйте /bonus_mailing
2. Выберите "Запланировать бонус"
3. Отправьте сообщение в HTML формате
4. Прикрепите файлы (необязательно) - PDF или изображения
5. Выберите тарифы
6. Укажите даты начала и окончания

<b>Управление:</b>
• В планере бонусов можно редактировать все параметры
• Можно включать/выключать рассылки
• Изменять даты, тарифы и файлы
• Удалять ненужные рассылки
"""
    await message.answer(help_text)


# Диагностические команды
@mailing_router.message(Command("check_users"))
async def check_users(message: Message):
    """Проверка почему пользователи не находятся"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет прав для этой команды.")
        return
    
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            # Проверяем рассылку #1
            cursor.execute('SELECT tariffs FROM bonus_mailings WHERE id = 1')
            mailing_result = cursor.fetchone()
            
            if not mailing_result:
                await message.answer("❌ Рассылка #1 не найдена")
                return
            
            tariffs = json.loads(mailing_result[0])
            
            # Все активные пользователи
            cursor.execute('''
                SELECT user_id, tariff_name, valid_until, status
                FROM payments 
                WHERE datetime(valid_until) > datetime('now')
                ORDER BY valid_until DESC
            ''')
            all_active = cursor.fetchall()
            
            # Пользователи подходящие под тарифы
            placeholders = ','.join(['?'] * len(tariffs))
            cursor.execute(f'''
                SELECT user_id, tariff_name, valid_until, status
                FROM payments 
                WHERE tariff_name IN ({placeholders}) 
                AND datetime(valid_until) > datetime('now')
                ORDER BY valid_until DESC
            ''', tariffs)
            matching = cursor.fetchall()
            
            # Проверяем конкретный тариф "1 месяц"
            cursor.execute('''
                SELECT user_id, tariff_name, valid_until, status
                FROM payments 
                WHERE tariff_name = '1 месяц'
                AND datetime(valid_until) > datetime('now')
                ORDER BY valid_until DESC
            ''')
            month_tariff = cursor.fetchall()
        
        text = (
            f"🔍 <b>Проверка пользователей</b>\n\n"
            f"💰 Тарифы рассылки: {', '.join(tariffs)}\n\n"
            f"👥 Всего активных пользователей: {len(all_active)}\n"
            f"✅ Подходящих под тарифы: {len(matching)}\n"
            f"📅 С тарифом '1 месяц': {len(month_tariff)}\n\n"
        )
        
        if all_active:
            text += "<b>Все активные пользователи:</b>\n"
            for user in all_active[:5]:
                text += f"• ID: {user[0]}, Тариф: {user[1]}, До: {user[2][:16]}, Статус: {user[3]}\n"
        
        if matching:
            text += f"\n<b>Подходящие пользователи:</b>\n"
            for user in matching:
                text += f"• ID: {user[0]}, Тариф: {user[1]}, До: {user[2][:16]}, Статус: {user[3]}\n"
        else:
            text += "\n❌ <b>Нет подходящих пользователей!</b>\n"
            text += "Возможные причины:\n"
            text += "1. Нет пользователей с активными подписками\n"
            text += "2. Неправильные названия тарифов\n"
            text += "3. Проблемы с форматом дат\n"
        
        await message.answer(text)
        
    except Exception as e:
        await message.answer(f"❌ Ошибка проверки: {str(e)}")

@mailing_router.message(Command("check_payments_structure"))
async def check_payments_structure(message: Message):
    """Проверка структуры таблицы payments"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет прав для этой команды.")
        return
    
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            # Получаем структуру таблицы
            cursor.execute("PRAGMA table_info(payments)")
            columns = cursor.fetchall()
            
            # Получаем примеры данных
            cursor.execute('''
                SELECT tariff_name, status, valid_until 
                FROM payments 
                LIMIT 5
            ''')
            examples = cursor.fetchall()
            
            # Получаем уникальные тарифы
            cursor.execute('SELECT DISTINCT tariff_name FROM payments')
            unique_tariffs = cursor.fetchall()
        
        text = "<b>Структура таблицы payments:</b>\n"
        for col in columns:
            text += f"• {col[1]} ({col[2]})\n"
        
        text += f"\n<b>Уникальные тарифы ({len(unique_tariffs)}):</b>\n"
        for tariff in unique_tariffs:
            text += f"• '{tariff[0]}'\n"
        
        text += "\n<b>Примеры данных:</b>\n"
        for example in examples:
            text += f"• Тариф: '{example[0]}', Статус: '{example[1]}', До: {example[2]}\n"
        
        await message.answer(text)
        
    except Exception as e:
        await message.answer(f"❌ Ошибка проверки структуры: {str(e)}")

async def auto_send_mailings(bot):
    """Автоматическая отправка рассылок по расписанию"""
    try:
        mailings = bonus_mailing.get_all_mailings()
        current_time = datetime.now()
        
        for mailing in mailings:
            if not mailing['is_active']:
                continue
            
            start_date = datetime.fromisoformat(mailing['start_date'])
            end_date = datetime.fromisoformat(mailing['end_date'])
            
            if start_date <= current_time <= end_date:
                # Проверяем не отправлялась ли уже сегодня
                last_sent_key = f"mailing_last_sent_{mailing['id']}"
                last_sent = bonus_mailing.get_setting(last_sent_key)
                
                if last_sent and last_sent == current_time.strftime('%Y-%m-%d'):
                    continue  # Уже отправляли сегодня
                
                # Получаем пользователей
                with db.get_connection() as conn:
                    cursor = conn.cursor()
                    
                    tariffs = json.loads(mailing['tariffs'])
                    placeholders = ','.join(['?'] * len(tariffs))
                    
                    cursor.execute(f'''
                        SELECT DISTINCT user_id 
                        FROM payments 
                        WHERE tariff_name IN ({placeholders}) 
                        AND status = 'succeeded'
                        AND datetime(valid_until) > datetime('now')
                    ''', tariffs)
                    
                    users = cursor.fetchall()
                
                # Отправляем пользователям
                sent_count = 0
                for user in users:
                    try:
                        user_id = user[0]
                        
                        # Сначала отправляем текст
                        await bot.send_message(
                            chat_id=user_id,
                            text=mailing['message_text'],
                            parse_mode='HTML'
                        )
                        
                        # Затем отправляем файлы если есть с поддержкой изображений
                        if mailing['file_paths']:
                            files = json.loads(mailing['file_paths'])
                            for file_path in files:
                                if os.path.exists(file_path):
                                    try:
                                        # Определяем тип файла по расширению
                                        file_ext = os.path.splitext(file_path)[1].lower()
                                        
                                        with open(file_path, 'rb') as file:
                                            file_data = file.read()
                                        
                                        from aiogram.types import BufferedInputFile
                                        input_file = BufferedInputFile(
                                            file_data,
                                            filename=os.path.basename(file_path)
                                        )
                                        
                                        if file_ext in ['.jpg', '.jpeg', '.png', '.gif']:
                                            # Отправляем как фото
                                            await bot.send_photo(
                                                chat_id=user_id,
                                                photo=input_file
                                            )
                                        else:
                                            # Отправляем как документ
                                            await bot.send_document(
                                                chat_id=user_id,
                                                document=input_file
                                            )
                                            
                                    except Exception as file_error:
                                        print(f"Ошибка отправки файла пользователю {user_id}: {str(file_error)}")
                        
                        sent_count += 1
                        await asyncio.sleep(0.1)
                        
                    except Exception as e:
                        print(f"Ошибка отправки пользователю {user_id}: {str(e)}")
                
                # Сохраняем дату отправки
                bonus_mailing.update_setting(last_sent_key, current_time.strftime('%Y-%m-%d'))
                
                print(f"✅ Автоматическая рассылка #{mailing['id']} отправлена {sent_count} пользователям")
                
    except Exception as e:
        print(f"❌ Ошибка автоматической рассылки: {str(e)}")




# Обработка ошибок
@mailing_router.errors()
async def mailing_errors_handler(event, exception):
    """Обработчик ошибок для рассылок"""
    if hasattr(event, 'message') and event.message:
        await event.message.answer("❌ Произошла ошибка при обработке запроса. Попробуйте позже.")
    
    print(f"Ошибка в модуле рассылок: {exception}")
    return True


# Функция для проверки и создания необходимых директорий
def init_mailing_system():
    """Инициализация системы рассылок"""
    try:
        # Создаем директорию для файлов если не существует
        if not os.path.exists(MailingConfig.FILES_DIR):
            os.makedirs(MailingConfig.FILES_DIR)
            print(f"✅ Создана директория для файлов: {MailingConfig.FILES_DIR}")
        
        # Создаем таблицы если не существуют
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            # Таблица рассылок
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS bonus_mailings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    message_text TEXT NOT NULL,
                    file_paths TEXT,
                    tariffs TEXT NOT NULL,
                    start_date DATETIME NOT NULL,
                    end_date DATETIME NOT NULL,
                    is_active BOOLEAN DEFAULT 1,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Таблица логов отправок
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS mailing_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    mailing_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    sent_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (mailing_id) REFERENCES bonus_mailings (id)
                )
            ''')
            
            conn.commit()
        
        print("✅ Система рассылок инициализирована")
        
    except Exception as e:
        print(f"❌ Ошибка инициализации системы рассылок: {e}")

@mailing_router.message(Command("test_single_file"))
async def test_single_file(message: Message):
    """Тест отправки одного файла"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет прав для этой команды.")
        return
    
    # Получаем первый файл из первой активной рассылки
    try:
        mailings = bonus_mailing.get_all_mailings()
        current_time = datetime.now()
        
        test_file_path = None
        
        for mailing in mailings:
            if not mailing['is_active']:
                continue
            
            start_date = datetime.fromisoformat(mailing['start_date'])
            end_date = datetime.fromisoformat(mailing['end_date'])
            
            if start_date <= current_time <= end_date and mailing['file_paths']:
                files = json.loads(mailing['file_paths'])
                if files and os.path.exists(files[0]):
                    test_file_path = files[0]
                    break
        
        if not test_file_path:
            await message.answer("❌ Не найден подходящий файл для теста")
            return
        
        await message.answer(f"📤 Тестирую отправку файла: {os.path.basename(test_file_path)}")
        
        # Способ 1: Прямой путь (самый простой)
        await message.answer("🔄 Способ 1: Прямой путь...")
        try:
            # Определяем тип файла по расширению
            file_ext = os.path.splitext(test_file_path)[1].lower()
            
            if file_ext in ['.jpg', '.jpeg', '.png', '.gif']:
                await message.bot.send_photo(
                    chat_id=message.from_user.id,
                    photo=test_file_path
                )
            else:
                await message.bot.send_document(
                    chat_id=message.from_user.id,
                    document=test_file_path
                )
            await message.answer("✅ Способ 1: Успешно")
            return
        except Exception as e:
            await message.answer(f"❌ Способ 1 не сработал: {str(e)}")
        
        # Способ 2: Бинарное чтение с явным закрытием файла
        await message.answer("🔄 Способ 2: Бинарное чтение...")
        try:
            with open(test_file_path, 'rb') as file:
                file_data = file.read()  # Читаем все данные в память
            
            # Используем BufferedInputFile
            from aiogram.types import BufferedInputFile
            input_file = BufferedInputFile(file_data, filename=os.path.basename(test_file_path))
            
            # Определяем тип файла по расширению
            file_ext = os.path.splitext(test_file_path)[1].lower()
            
            if file_ext in ['.jpg', '.jpeg', '.png', '.gif']:
                await message.bot.send_photo(
                    chat_id=message.from_user.id,
                    photo=input_file
                )
            else:
                await message.bot.send_document(
                    chat_id=message.from_user.id,
                    document=input_file
                )
            await message.answer("✅ Способ 2: Успешно")
            
        except Exception as e2:
            await message.answer(f"❌ Способ 2 не сработал: {str(e2)}")
            
    except Exception as e:
        await message.answer(f"❌ Общая ошибка: {str(e)}")



@mailing_router.message(Command("test_mailing_direct"))
async def test_mailing_direct(message: Message):
    """Прямая отправка файлов по путям"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет прав для этой команды.")
        return
    
    await message.answer("🔄 Прямой тест отправки файлов...")
    
    try:
        mailings = bonus_mailing.get_all_mailings()
        current_time = datetime.now()
        
        for mailing in mailings:
            if not mailing['is_active']:
                continue
            
            start_date = datetime.fromisoformat(mailing['start_date'])
            end_date = datetime.fromisoformat(mailing['end_date'])
            
            if start_date <= current_time <= end_date:
                await message.answer(f"📧 Рассылка #{mailing['id']}")
                
                # Текст
                await message.answer("📤 Текст рассылки:")
                await message.bot.send_message(
                    chat_id=message.from_user.id,
                    text=mailing['message_text'],
                    parse_mode='HTML'
                )
                
                # Файлы - САМЫЙ ПРОСТОЙ СПОСОБ
                if mailing['file_paths']:
                    files = json.loads(mailing['file_paths'])
                    for file_path in files:
                        if os.path.exists(file_path):
                            await message.answer(f"📤 Отправляю: {os.path.basename(file_path)}")
                            
                            # Просто передаем путь как строку
                            await message.bot.send_document(
                                chat_id=message.from_user.id,
                                document=file_path  # Просто строка с путем!
                            )
                
                break  # Только первую
        
        await message.answer("✅ Прямой тест завершен")
        
    except Exception as e:
        await message.answer(f"❌ Ошибка: {str(e)}")



# Вызываем инициализацию при импорте модуля
init_mailing_system()

# Экспортируем роутер
__all__ = ['mailing_router', 'auto_send_mailings']
