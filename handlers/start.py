# handlers/start.py
from aiogram import Router, types, F
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from keyboards.registration import get_registration_keyboard
from keyboards.main_menu import get_main_menu_keyboard
from keyboards.students import get_students_menu_keyboard, get_cancel_keyboard
from database import db

router = Router()

# Функция для клавиатуры приглашений
def get_invite_keyboard(student_id):
    """Создает клавиатуру для меню приглашений"""
    keyboard = [
        [InlineKeyboardButton(text="👤 Пригласить ученика", callback_data=f"invite_student_{student_id}")],
        [InlineKeyboardButton(text="👨‍👩‍👧‍👦 Пригласить родителя", callback_data=f"invite_parent_{student_id}")],
        [InlineKeyboardButton(text="◀️ Назад к ученику", callback_data=f"back_to_student_{student_id}")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

# Функция для клавиатуры списка учеников
def get_students_list_keyboard(students, page=0, page_size=5):
    """Создает клавиатуру для списка учеников с пагинацией"""
    keyboard = []
    
    # Добавляем кнопки для учеников на текущей странице
    start_idx = page * page_size
    end_idx = start_idx + page_size
    current_page_students = students[start_idx:end_idx]
    
    for student in current_page_students:
        status_emoji = "✅" if student['status'].lower() == 'active' else "⏸️"
        keyboard.append([InlineKeyboardButton(
            text=f"{status_emoji} {student['full_name']}",
            callback_data=f"student_{student['id']}"
        )])
    
    # Добавляем кнопки навигации, если нужно
    navigation_buttons = []
    if page > 0:
        navigation_buttons.append(InlineKeyboardButton(
            text="⬅️ Назад",
            callback_data=f"students_page_{page-1}"
        ))
    if end_idx < len(students):
        navigation_buttons.append(InlineKeyboardButton(
            text="➡️ Вперед",
            callback_data=f"students_page_{page+1}"
        ))
    
    if navigation_buttons:
        keyboard.append(navigation_buttons)
    
    # Кнопка возврата
    keyboard.append([InlineKeyboardButton(
        text="◀️ Назад к меню учеников",
        callback_data="back_to_students_menu"
    )])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

@router.message(Command("start"))
async def cmd_start(message: types.Message):
    # Проверяем, зарегистрирован ли пользователь
    existing_tutor = db.get_tutor_by_telegram_id(message.from_user.id)
    
    if existing_tutor:
        # Если пользователь уже зарегистрирован, показываем приветственное сообщение с главным меню
        welcome_text = f"""
<b>Добро пожаловать назад, {existing_tutor[2]}!</b>

Рады снова видеть вас в ежедневнике репетитора.

Ваши данные:
📝 ФИО: {existing_tutor[2]}
📞 Телефон: {existing_tutor[3]}

Выберите нужный раздел:
"""
        await message.answer(
            welcome_text,
            reply_markup=get_main_menu_keyboard(),
            parse_mode="HTML"
        )
    else:
        # Если пользователь не зарегистрирован, показываем стандартное приветствие
        welcome_text = """
<b>Ежедневник репетитора</b>

Привет! Этот бот для репетиторов

🔲 Зарегистрироваться в боте
✅ Написать сообщение...
"""
        
        await message.answer(
            welcome_text,
            reply_markup=get_registration_keyboard(),
            parse_mode="HTML"
        )

# Обработчик глубоких ссылок
@router.message(CommandStart(deep_link=True))
async def handle_deep_link(message: types.Message):
    # Извлекаем аргументы из deep link
    parts = message.text.split()
    
    if len(parts) < 2:
        # Если нет аргументов, выполняем стандартный старт
        await cmd_start(message)
        return
    
    args = parts[1]  # Вторая часть - это аргументы
    
    # Обрабатываем пригласительные ссылки
    if args.startswith('student_') or args.startswith('parent_'):
        try:
            invite_type, token = args.split('_', 1)
        except ValueError:
            await message.answer("❌ Неверная ссылка приглашения.")
            return
        
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

# Обработчик для кнопки "Учет учеников"
@router.callback_query(F.data == "students")
async def students_menu(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.answer()
    await state.clear()
    
    await callback_query.message.edit_text(
        "👥 <b>Учет учеников</b>\n\n"
        "Здесь вы можете управлять вашими учениками: добавлять новых, "
        "просматривать и редактировать информацию о существующих.",
        reply_markup=get_students_menu_keyboard(),
        parse_mode="HTML"
    )

# Обработчик для кнопки "Назад в главное меню" из раздела учеников
@router.callback_query(F.data == "back_to_main")
async def back_to_main_menu(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.answer()
    await state.clear()
    
    # Получаем данные репетитора для приветственного сообщения
    existing_tutor = db.get_tutor_by_telegram_id(callback_query.from_user.id)
    
    if existing_tutor:
        welcome_text = f"""
<b>Добро пожаловать назад, {existing_tutor[2]}!</b>

Рады снова видеть вас в ежедневнике репетитора.

Ваши данные:
📝 ФИО: {existing_tutor[2]}
📞 Телефон: {existing_tutor[3]}

Выберите нужный раздел:
"""
        try:
            await callback_query.message.edit_text(
                welcome_text,
                reply_markup=get_main_menu_keyboard(),
                parse_mode="HTML"
            )
        except:
            await callback_query.message.answer(
                welcome_text,
                reply_markup=get_main_menu_keyboard(),
                parse_mode="HTML"
            )

# Обработчик для кнопки "Назад к меню учеников"
@router.callback_query(F.data == "back_to_students_menu")
async def back_to_students_menu(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.answer()
    await state.clear()
    
    await callback_query.message.edit_text(
        "👥 <b>Учет учеников</b>\n\n"
        "Здесь вы можете управлять вашими учениками: добавлять новых, "
        "просматривать и редактировать информацию о существующих.",
        reply_markup=get_students_menu_keyboard(),
        parse_mode="HTML"
    )

# Обработчик отмены операций
@router.callback_query(F.data == "cancel_operation")
async def cancel_operation(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.answer()
    await state.clear()
    
    await callback_query.message.edit_text(
        "👥 <b>Учет учеников</b>\n\n"
        "Здесь вы можете управлять вашими учениками: добавлять новых, "
        "просматривать и редактировать информацию о существующих.",
        reply_markup=get_students_menu_keyboard(),
        parse_mode="HTML"
    )

# Обработчик для кнопки приглашения
@router.callback_query(lambda c: c.data.startswith("invite_") and len(c.data.split("_")) == 2)
async def invite_menu(callback_query: types.CallbackQuery):
    await callback_query.answer()
    
    try:
        student_id = int(callback_query.data.split("_")[1])
    except ValueError:
        return
    
    await callback_query.message.edit_text(
        f"👤 <b>Приглашение для ученика</b>\n\n"
        "Выберите, кого вы хотите пригласить:",
        parse_mode="HTML",
        reply_markup=get_invite_keyboard(student_id)
    )

# Обработчики для приглашения ученика
@router.callback_query(lambda c: c.data.startswith("invite_student_") and len(c.data.split("_")) == 3)
async def invite_student(callback_query: types.CallbackQuery):
    await callback_query.answer()
    
    try:
        student_id = int(callback_query.data.split("_")[2])
    except ValueError:
        return
    
    student = db.get_student_by_id(student_id)
    if not student:
        return
    
    # Генерируем и СОХРАНЯЕМ токен
    token = db.generate_invite_token()
    success = db.update_student_token(student_id, token, 'student')
    
    if not success:
        await callback_query.message.edit_text("❌ Ошибка при создании приглашения!")
        return
    
    # Создаем ссылку для приглашения
    bot_username = (await callback_query.bot.get_me()).username
    invite_link = f"https://t.me/{bot_username}?start=student_{token}"
    
    try:
        await callback_query.message.edit_text(
            f"👤 <b>Приглашение для ученика</b>\n\n"
            f"Ученик: {student['full_name']}\n\n"
            f"Отправьте эту ссылку ученику:\n"
            f"<code>{invite_link}</code>\n\n"
            f"Ученик сможет привязать свой Telegram аккаунт к вашей базе.",
            parse_mode="HTML",
            reply_markup=get_invite_keyboard(student_id)
        )
    except Exception:
        await callback_query.message.answer(
            f"👤 <b>Приглашение для ученика</b>\n\n"
            f"Ученик: {student['full_name']}\n\n"
            f"Отправьте эту ссылку ученику:\n"
            f"<code>{invite_link}</code>\n\n"
            f"Ученик сможет привязать свой Telegram аккаунт к вашей базе.",
            parse_mode="HTML",
            reply_markup=get_invite_keyboard(student_id)
        )

# Обработчики для приглашения родителя
@router.callback_query(lambda c: c.data.startswith("invite_parent_") and len(c.data.split("_")) == 3)
async def invite_parent(callback_query: types.CallbackQuery):
    await callback_query.answer()
    
    try:
        student_id = int(callback_query.data.split("_")[2])
    except ValueError:
        return
    
    student = db.get_student_by_id(student_id)
    if not student:
        return
    
    # Генерируем и СОХРАНЯЕМ токен
    token = db.generate_invite_token()
    success = db.update_student_token(student_id, token, 'parent')
    
    if not success:
        await callback_query.message.edit_text("❌ Ошибка при создании приглашения!")
        return
    
    # Создаем ссылку для приглашения
    bot_username = (await callback_query.bot.get_me()).username
    invite_link = f"https://t.me/{bot_username}?start=parent_{token}"
    
    try:
        await callback_query.message.edit_text(
            f"👨‍👩‍👧‍👦 <b>Приглашение для родителя</b>\n\n"
            f"Ученик: {student['full_name']}\n\n"
            f"Отправьте эту ссылку родителю:\n"
            f"<code>{invite_link}</code>\n\n"
            f"Родитель сможет привязать свой Telegram аккаунт к вашей базе.",
            parse_mode="HTML",
            reply_markup=get_invite_keyboard(student_id)
        )
    except Exception:
        await callback_query.message.answer(
            f"👨‍👩‍👧‍👦 <b>Приглашение для родителя</b>\n\n"
            f"Ученик: {student['full_name']}\n\n"
            f"Отправьте эту ссылку родителю:\n"
            f"<code>{invite_link}</code>\n\n"
            f"Родитель сможет привязать свой Telegram аккаунт к вашей базе.",
            parse_mode="HTML",
            reply_markup=get_invite_keyboard(student_id)
        )

# Обработчик возврата к ученику
@router.callback_query(lambda c: c.data.startswith("back_to_student_") and len(c.data.split("_")) == 4)
async def back_to_student_from_invite(callback_query: types.CallbackQuery):
    await callback_query.answer()
    
    try:
        student_id = int(callback_query.data.split("_")[3])
    except ValueError:
        return
    
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
        f"<b>Дата добавления:</b> {student.get('created_at', 'не указана')}"
    )
    
    # Создаем клавиатуру для управления учеником
    keyboard = [
        [InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"edit_student_{student_id}")],
        [InlineKeyboardButton(text="📤 Пригласить", callback_data=f"invite_{student_id}")],
        [InlineKeyboardButton(text="◀️ Назад к списку", callback_data="students_list")]
    ]
    
    await callback_query.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
        parse_mode="HTML"
    )

# Обработчик списка учеников
@router.callback_query(F.data == "students_list")
async def process_students_list(callback_query: types.CallbackQuery):
    await callback_query.answer()
    
    # Получаем ID текущего репетитора
    tutor_id = db.get_tutor_id_by_telegram_id(callback_query.from_user.id)
    
    if not tutor_id:
        await callback_query.message.edit_text("❌ Ошибка: не найден ID репетитора.")
        return
    
    # Получаем список учеников
    students = db.get_students_by_tutor(tutor_id)
    
    if not students:
        await callback_query.message.edit_text(
            "📝 <b>Список учеников пуст</b>\n\n"
            "У вас пока нет добавленных учеников.",
            reply_markup=get_students_menu_keyboard(),
            parse_mode="HTML"
        )
        return
    
    # Формируем текст сообщения
    active_count = sum(1 for s in students if s['status'].lower() == 'active')
    text = (
        f"👥 <b>Список ваших учеников</b>\n\n"
        f"Всего учеников: {len(students)}\n"
        f"Активных: {active_count}\n\n"
        f"Выберите ученика для просмотра:"
    )
    
    # Показываем первую страницу списка
    await callback_query.message.edit_text(
        text,
        reply_markup=get_students_list_keyboard(students, page=0),
        parse_mode="HTML"
    )

# Обработчик пагинации списка учеников
@router.callback_query(F.data.startswith("students_page_"))
async def students_list_page(callback_query: types.CallbackQuery):
    await callback_query.answer()
    
    # Получаем номер страницы из callback_data
    page = int(callback_query.data.split("_")[2])
    
    # Получаем ID текущего репетитора
    tutor_id = db.get_tutor_id_by_telegram_id(callback_query.from_user.id)
    
    if not tutor_id:
        await callback_query.message.edit_text("❌ Ошибка: не найден ID репетитора.")
        return
    
    # Получаем список учеников
    students = db.get_students_by_tutor(tutor_id)
    
    # Формируем текст сообщения
    active_count = sum(1 for s in students if s['status'].lower() == 'active')
    text = (
        f"👥 <b>Список ваших учеников</b>\n\n"
        f"Всего учеников: {len(students)}\n"
        f"Активных: {active_count}\n\n"
        f"Страница {page + 1}"
    )
    
    # Обновляем сообщение с новой страницей
    await callback_query.message.edit_text(
        text,
        reply_markup=get_students_list_keyboard(students, page=page),
        parse_mode="HTML"
    )

# Обработчик просмотра ученика
@router.callback_query(F.data.startswith("student_"))
async def view_student_detail(callback_query: types.CallbackQuery):
    await callback_query.answer()
    
    # Получаем ID ученика из callback_data
    student_id = int(callback_query.data.split("_")[1])
    
    # Получаем информацию об ученике
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
        f"<b>Дата добавления:</b> {student.get('created_at', 'не указана')}"
    )
    
    # Создаем клавиатуру для управления учеником
    keyboard = [
        [InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"edit_student_{student_id}")],
        [InlineKeyboardButton(text="📤 Пригласить", callback_data=f"invite_{student_id}")],
        [InlineKeyboardButton(text="◀️ Назад к списку", callback_data="students_list")]
    ]
    
    await callback_query.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
        parse_mode="HTML"
    )

# Обработчик редактирования ученика
@router.callback_query(F.data.startswith("edit_student_"))
async def edit_student(callback_query: types.CallbackQuery):
    await callback_query.answer()
    
    student_id = int(callback_query.data.split("_")[2])
    await callback_query.message.answer(
        f"✏️ Редактирование ученика ID: {student_id}\n\n"
        "Функция редактирования находится в разработке."
    )

# Временные обработчики для остальных кнопок
@router.callback_query(F.data.in_(["schedule", "groups", "payments", "settings"]))
async def process_other_menus(callback_query: types.CallbackQuery):
    await callback_query.answer()
    
    menu_responses = {
        "schedule": "📅 Раздел 'Расписание занятий' находится в разработке.",
        "groups": "👨‍👩‍👧‍👦 Раздел 'Управление группами' находится в разработке.",
        "payments": "💰 Раздел 'Оплаты' находится в разработке.",
        "settings": "⚙️ Раздел 'Настройки' находится в разработке."
    }
    
    await callback_query.message.answer(menu_responses[callback_query.data])