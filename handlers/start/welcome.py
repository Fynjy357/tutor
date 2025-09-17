from aiogram import types
from database import db
from handlers.schedule.schedule_utils import get_today_schedule_text
from handlers.start.keyboards_start import get_student_welcome_keyboard, get_parent_welcome_keyboard, get_registration_keyboard
from keyboards.main_menu import get_main_menu_keyboard
from handlers.start.config import WELCOME_BACK_TEXT, REGISTRATION_TEXT

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
    tutor_name = tutor[2] if tutor else "Пользователь"
    tutor_id = tutor[0]  # ID репетитора
    
    # Получаем расписание на сегодня
    schedule_text = await get_today_schedule_text(tutor_id)

    # Проверяем активную подпику
    has_active_subscription = db.check_tutor_subscription(tutor_id)
    subscription_icon = "💎 " if has_active_subscription else ""
    
    # Формируем полный текст приветствия
    formatted_text = WELCOME_BACK_TEXT.format(
        tutor_name=tutor_name,
        schedule_text=schedule_text
    )
    welcome_text = f"{subscription_icon}{formatted_text}"
    
    await message.answer(
        welcome_text,
        reply_markup=get_main_menu_keyboard(),
        parse_mode="HTML"
    )

async def show_registration_message(message: types.Message):
    """Приветствие для нового пользователя"""
    await message.answer(
        REGISTRATION_TEXT,
        reply_markup=get_registration_keyboard(),
        parse_mode="HTML"
    )