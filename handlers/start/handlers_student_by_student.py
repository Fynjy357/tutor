from aiogram import types, Router, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database import db

from datetime import datetime

from handlers.start.keyboards_start import get_student_welcome_keyboard
from handlers.start.welcome import show_student_welcome  # Импортируем функцию из welcome.py

# Создаем роутер для учеников
student_router = Router()

def get_back_to_student_menu_keyboard() -> InlineKeyboardMarkup:
    """Создает клавиатуру с кнопкой 'Назад' для ученика"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="⬅️ Назад в меню", 
                    callback_data="stud_back_menu"
                )
            ]
        ]
    )
    return keyboard

@student_router.callback_query(F.data == "stud_settings")
async def handle_student_settings(callback_query: types.CallbackQuery):
    """Обработчик кнопки 'Настройки' для ученика"""
    try:
        # Получаем настройки студента
        main_student = db.get_main_student_by_telegram_id(callback_query.from_user.id)
        
        if not main_student:
            await callback_query.message.edit_text(
                "❌ Не удалось найти данные ученика",
                parse_mode="HTML",
                reply_markup=get_back_to_student_menu_keyboard()
            )
            await callback_query.answer()
            return
        
        # Создаем клавиатуру настроек
        settings_keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="🔔 Уведомления: Вкл/Выкл" if main_student.get('notification_enabled', True) else "🔕 Уведомления: Вкл/Выкл",
                        callback_data="stud_toggle_notifications"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="🕐 Изменить время уведомлений",
                        callback_data="stud_change_notification_time"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="👤 Редактировать профиль",
                        callback_data="stud_edit_profile"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="⬅️ Назад в меню",
                        callback_data="stud_back_menu"
                    )
                ]
            ]
        )
        
        settings_text = f"""
⚙️ <b>Настройки профиля</b>

👤 <b>Имя:</b> {main_student['full_name']}
⏰ <b>Уведомления:</b> {'✅ Включены' if main_student.get('notification_enabled', True) else '❌ Выключены'}
🕐 <b>Время уведомлений:</b> {main_student.get('notification_time', '09:00')}

Здесь вы можете настроить параметры вашего профиля и уведомлений.
        """
        
        await callback_query.message.edit_text(
            settings_text,
            parse_mode="HTML",
            reply_markup=settings_keyboard
        )
        
    except Exception as e:
        print(f"❌ Ошибка в handle_student_settings: {e}")
        await callback_query.message.answer("❌ Произошла ошибка при отображении настроек")
    
    await callback_query.answer()

@student_router.callback_query(F.data == "stud_view_homeworks")
async def handle_student_homeworks(callback_query: types.CallbackQuery):
    """Обработчик кнопки 'Посмотреть домашние работы' для ученика"""
    try:
        # Получаем основного студента
        main_student = db.get_main_student_by_telegram_id(callback_query.from_user.id)
        
        if not main_student:
            await callback_query.message.edit_text(
                "❌ Не удалось найти данные ученика",
                parse_mode="HTML",
                reply_markup=get_back_to_student_menu_keyboard()
            )
            await callback_query.answer()
            return
        
        # Получаем все записи студента у разных репетиторов
        all_student_records = db.get_all_students_for_main_student(main_student['id'])

        if not all_student_records:
            await callback_query.message.edit_text(
                "📚 <b>Домашние задания</b>\n\nУ вас нет активных записей у репетиторов.",
                parse_mode="HTML",
                reply_markup=get_back_to_student_menu_keyboard()
            )
            await callback_query.answer()
            return
        
        # Собираем невыполненные домашние задания
        response_text = "📚 <b>Невыполненные домашние задания:</b>\n\n"
        total_undone = 0
        has_undone_homeworks = False
        
        # Группируем по репетиторам
        for student_record in all_student_records:
            tutor_name = student_record.get('tutor_name', 'Неизвестный репетитор')
            student_id_in_tutor = student_record['id']
            
            # Получаем невыполненные домашние (используем исправленную функцию)
            undone_homeworks = db.get_student_undone_homeworks_from_reports(student_id_in_tutor)
            
            if undone_homeworks:
                has_undone_homeworks = True
                response_text += f"👨‍🏫 <b>{tutor_name}:</b>\n"
                
                for homework in undone_homeworks:
                    try:
                        lesson_date = datetime.strptime(homework['lesson_date'], '%Y-%m-%d %H:%M:%S').strftime('%d.%m.%Y')
                        response_text += f"   • {lesson_date}"
                        
                        # Добавляем информацию о производительности ученика, если есть
                        if homework.get('student_performance'):
                            # Обрезаем длинный текст для лучшего отображения
                            performance_text = homework['student_performance']
                            if len(performance_text) > 100:
                                performance_text = performance_text[:97] + "..."
                            response_text += f"\n     💬 <i>{performance_text}</i>"
                        
                        response_text += "\n"
                        total_undone += 1
                        
                    except Exception:
                        continue
                
                response_text += "\n"
        
        if not has_undone_homeworks:
            response_text = "✅ <b>Все домашние задания выполнены!</b>\n\n"
            response_text += "У вас нет невыполненных домашних работ."
        else:
            response_text += f"\n📊 <b>Всего невыполнено:</b> {total_undone} домашних заданий\n\n"
            response_text += "📝 Пожалуйста, выполните домашние задания вовремя!"
        
        await callback_query.message.edit_text(
            response_text,
            parse_mode="HTML",
            reply_markup=get_back_to_student_menu_keyboard()
        )
        
    except Exception as e:
        print(f"❌ Ошибка в handle_student_homeworks: {e}")
        await callback_query.message.answer("❌ Произошла ошибка при получении данных о домашних работах")
    
    await callback_query.answer()


@student_router.callback_query(F.data == "stud_view_upcoming")
async def handle_student_upcoming_lessons(callback_query: types.CallbackQuery):
    """Обработчик кнопки 'Предстоящие занятия' для ученика"""
    try:
        # Получаем основного студента
        main_student = db.get_main_student_by_telegram_id(callback_query.from_user.id)
        
        if not main_student:
            await callback_query.message.edit_text(
                "❌ Не удалось найти данные ученика",
                parse_mode="HTML",
                reply_markup=get_back_to_student_menu_keyboard()
            )
            await callback_query.answer()
            return
        
        # Получаем все записи студента
        all_student_records = db.get_all_students_for_main_student(main_student['id'])
        
        if not all_student_records:
            await callback_query.message.edit_text(
                "📅 <b>Предстоящие занятия</b>\n\nУ вас нет активных записей у репетиторов.",
                parse_mode="HTML",
                reply_markup=get_back_to_student_menu_keyboard()
            )
            await callback_query.answer()
            return
        
        # Собираем предстоящие занятия
        response_text = "📅 <b>Ваши предстоящие занятия:</b>\n\n"
        total_lessons = 0
        has_upcoming_lessons = False
        
        # Группируем по репетиторам
        for student_record in all_student_records:
            tutor_name = student_record.get('tutor_name', 'Неизвестный репетитор')
            student_id_in_tutor = student_record['id']
            
            # Получаем предстоящие занятия
            upcoming_lessons = db.get_student_upcoming_lessons(student_id_in_tutor, 30)
            
            if upcoming_lessons:
                has_upcoming_lessons = True
                tutor_lessons = 0
                
                response_text += f"👨‍🏫 <b>{tutor_name}:</b>\n"
                
                for lesson in upcoming_lessons:
                    try:
                        lesson_datetime = datetime.strptime(lesson['lesson_date'], '%Y-%m-%d %H:%M:%S')
                        lesson_date = lesson_datetime.strftime('%d.%m.%Y')
                        lesson_time = lesson_datetime.strftime('%H:%M')
                        
                        response_text += f"   • {lesson_date} в {lesson_time} - {lesson['duration']} мин."
                        if lesson.get('price'):
                            response_text += f" ({lesson['price']} руб.)"
                        response_text += "\n"
                        
                        tutor_lessons += 1
                        
                    except Exception:
                        continue
                
                response_text += f"   <b>Запланировано:</b> {tutor_lessons} занятий\n\n"
                total_lessons += tutor_lessons
        
        if not has_upcoming_lessons:
            response_text = "📅 <b>Предстоящие занятия</b>\n\n"
            response_text += "На ближайший месяц у вас нет запланированных занятий.\n\n"
            response_text += "📞 Свяжитесь с репетиторами для планирования занятий."
        else:
            response_text += f"📊 <b>Всего запланировано:</b> {total_lessons} занятий\n\n"
            response_text += "⏰ Не забудьте подготовиться к занятиям!"
        
        await callback_query.message.edit_text(
            response_text,
            parse_mode="HTML",
            reply_markup=get_back_to_student_menu_keyboard()
        )
        
    except Exception as e:
        await callback_query.message.answer("❌ Произошла ошибка при получении данных о предстоящих занятиях")
        print(f"Ошибка в handle_student_upcoming_lessons: {e}")
    
    await callback_query.answer()

@student_router.callback_query(F.data == "stud_back_menu")
async def handle_back_to_student_menu(callback_query: types.CallbackQuery):
    """Обработчик кнопки 'Назад в меню' для ученика - возвращает в начальное меню из welcome.py"""
    try:
        # Получаем основного студента
        main_student = db.get_main_student_by_telegram_id(callback_query.from_user.id)
        
        if main_student:
            # Используем функцию из welcome.py для показа начального меню
            await show_student_welcome(callback_query.message, main_student)
        else:
            await callback_query.message.edit_text(
                "❌ Не удалось найти данные ученика",
                parse_mode="HTML"
            )
        
    except Exception as e:
        await callback_query.message.answer("❌ Произошла ошибка при возврате в меню")
        print(f"Ошибка в handle_back_to_student_menu: {e}")
    
    await callback_query.answer()

@student_router.callback_query(F.data == "stud_view_unpaid")
async def handle_student_unpaid_lessons(callback_query: types.CallbackQuery):
    """Обработчик кнопки 'Неоплаченные занятия' для ученика"""
    try:
        # Получаем основного студента
        main_student = db.get_main_student_by_telegram_id(callback_query.from_user.id)
        
        if not main_student:
            await callback_query.message.edit_text(
                "❌ Не удалось найти данные ученика",
                parse_mode="HTML",
                reply_markup=get_back_to_student_menu_keyboard()
            )
            await callback_query.answer()
            return
        
        # Получаем все записи студента у разных репетиторов
        all_student_records = db.get_all_students_for_main_student(main_student['id'])
        
        if not all_student_records:
            await callback_query.message.edit_text(
                "💰 <b>Неоплаченные занятия</b>\n\nУ вас нет активных записей у репетиторов.",
                parse_mode="HTML",
                reply_markup=get_back_to_student_menu_keyboard()
            )
            await callback_query.answer()
            return
        
        # Собираем неоплаченные занятия по репетиторам
        response_text = "💰 <b>Неоплаченные занятия:</b>\n\n"
        total_unpaid = 0
        total_amount = 0.0
        has_unpaid_lessons = False
        
        # Группируем по репетиторам
        for student_record in all_student_records:
            tutor_name = student_record.get('tutor_name', 'Неизвестный репетитор')
            student_id_in_tutor = student_record['id']
            
            # Получаем неоплаченные занятия
            unpaid_lessons = db.get_unpaid_lessons_for_student(student_id_in_tutor)
            
            if unpaid_lessons:
                has_unpaid_lessons = True
                tutor_unpaid = 0
                tutor_amount = 0.0
                
                response_text += f"👨‍🏫 <b>{tutor_name}:</b>\n"
                
                for lesson in unpaid_lessons:
                    try:
                        # Форматируем дату занятия
                        lesson_date = datetime.strptime(lesson['lesson_date'], '%Y-%m-%d %H:%M:%S').strftime('%d.%m.%Y')
                        
                        response_text += f"   • {lesson_date} - {lesson['duration']} мин."
                        if lesson.get('price'):
                            response_text += f" ({lesson['price']} руб.)"
                        response_text += "\n"
                        
                        tutor_unpaid += 1
                        if lesson.get('price'):
                            tutor_amount += float(lesson['price'])
                        
                    except Exception:
                        continue
                
                response_text += f"   <b>Неоплачено:</b> {tutor_unpaid} занятий"
                if tutor_amount > 0:
                    response_text += f" на сумму {tutor_amount} руб."
                response_text += "\n\n"
                
                total_unpaid += tutor_unpaid
                total_amount += tutor_amount
        
        if not has_unpaid_lessons:
            response_text = "✅ <b>Все занятия оплачены!</b>\n\n"
            response_text += "У вас нет неоплаченных занятий у всех репетиторов."
        else:
            response_text += f"📊 <b>Всего неоплачено:</b> {total_unpaid} занятий"
            if total_amount > 0:
                response_text += f" на общую сумму {total_amount} руб."
            response_text += "\n\n"
            response_text += "💳 Пожалуйста, оплатите занятия вовремя!"
        
        await callback_query.message.edit_text(
            response_text,
            parse_mode="HTML",
            reply_markup=get_back_to_student_menu_keyboard()
        )
        
    except Exception as e:
        print(f"❌ Ошибка в handle_student_unpaid_lessons: {e}")
        await callback_query.message.answer("❌ Произошла ошибка при получении данных о неоплаченных занятиях")
    
    await callback_query.answer()