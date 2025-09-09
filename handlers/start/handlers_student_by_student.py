from aiogram import types, Router, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database import db
from datetime import datetime, timedelta

from handlers.start.keyboards_start import get_student_welcome_keyboard

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

@student_router.callback_query(F.data == "stud_view_unpaid")
async def handle_student_unpaid_lessons(callback_query: types.CallbackQuery):
    """Обработчик кнопки 'Посмотреть неоплаченные занятия' для ученика"""
    try:
        # Получаем данные ученика из базы
        student = db.get_student_by_telegram_id(callback_query.from_user.id)
        
        if student:
            # Получаем реальные неоплаченные занятия
            unpaid_lessons = db.get_student_unpaid_lessons(student['id'])
            
            if unpaid_lessons:
                response_text = "💰 <b>Ваши задолженности:</b>\n\n"
                total_debt = 0
                lesson_count = 0
                
                for lesson in unpaid_lessons:
                    try:
                        # Парсим дату занятия
                        lesson_date = datetime.strptime(lesson['lesson_date'], '%Y-%m-%d %H:%M:%S').strftime('%d.%m.%Y')
                        response_text += f"• {lesson_date} - {lesson['price']} руб. ({lesson['duration']} мин.)\n"
                        total_debt += lesson['price']
                        lesson_count += 1
                    except (ValueError, KeyError) as e:
                        print(f"Ошибка обработки занятия {lesson}: {e}")
                        continue
                
                response_text += f"\n<b>Всего неоплачено:</b> {lesson_count} занятий\n"
                response_text += f"<b>Общая сумма задолженности:</b> {total_debt} руб.\n\n"
                response_text += "💳 Для оплаты свяжитесь с репетитором."
            else:
                response_text = "✅ <b>Все занятия оплачены!</b>\n\nУ вас нет задолженностей по оплате занятий."
        else:
            response_text = "❌ Не удалось найти данные ученика"
        
        await callback_query.message.edit_text(
            response_text,
            parse_mode="HTML",
            reply_markup=get_back_to_student_menu_keyboard()
        )
        
    except Exception as e:
        await callback_query.message.answer("❌ Произошла ошибка при получении данных о задолженностях")
        print(f"Ошибка в handle_student_unpaid_lessons: {e}")
    
    await callback_query.answer()

@student_router.callback_query(F.data == "stud_view_homeworks")
async def handle_student_homeworks(callback_query: types.CallbackQuery):
    """Обработчик кнопки 'Посмотреть домашние работы' для ученика"""
    try:
        # Получаем данные ученика из базы
        student = db.get_student_by_telegram_id(callback_query.from_user.id)
        
        if student:
            # Получаем невыполненные домашние работы
            undone_homeworks = db.get_student_undone_homeworks(student['id'])
            
            if undone_homeworks:
                response_text = "📚 <b>Невыполненные домашние работы:</b>\n\n"
                homework_count = 0
                
                for homework in undone_homeworks:
                    try:
                        # Парсим дату занятия
                        lesson_date = datetime.strptime(homework['lesson_date'], '%Y-%m-%d %H:%M:%S').strftime('%d.%m.%Y')
                        response_text += f"• {lesson_date} - {homework['tutor_name']}\n"
                        
                        # Добавляем комментарий о выполнении, если есть
                        if homework['student_performance']:
                            response_text += f"  Комментарий: {homework['student_performance']}\n\n"
                        else:
                            response_text += "\n"
                        
                        homework_count += 1
                    except (ValueError, KeyError) as e:
                        print(f"Ошибка обработки домашней работы {homework}: {e}")
                        continue
                
                response_text += f"\n<b>Всего невыполнено:</b> {homework_count} домашних работ\n\n"
                response_text += "📝 Пожалуйста, выполните домашние задания."
            else:
                response_text = "✅ <b>Все домашние работы выполнены!</b>\n\nУ вас нет невыполненных домашних заданий."
        else:
            response_text = "❌ Не удалось найти данные ученика"
        
        await callback_query.message.edit_text(
            response_text,
            parse_mode="HTML",
            reply_markup=get_back_to_student_menu_keyboard()
        )
        
    except Exception as e:
        await callback_query.message.answer("❌ Произошла ошибка при получении данных о домашних работах")
        print(f"Ошибка в handle_student_homeworks: {e}")
    
    await callback_query.answer()

@student_router.callback_query(F.data == "stud_view_upcoming")
async def handle_student_upcoming_lessons(callback_query: types.CallbackQuery):
    """Обработчик кнопки 'Предстоящие занятия' для ученика"""
    try:
        # Получаем данные ученика из базы
        student = db.get_student_by_telegram_id(callback_query.from_user.id)
        
        if student:
            # Получаем предстоящие занятия на месяц вперед
            upcoming_lessons = db.get_student_upcoming_lessons(student['id'], 30)
            
            if upcoming_lessons:
                response_text = "📅 <b>Ваши предстоящие занятия:</b>\n\n"
                lesson_count = 0
                
                for lesson in upcoming_lessons:
                    try:
                        # Парсим дату и время занятия
                        lesson_datetime = datetime.strptime(lesson['lesson_date'], '%Y-%m-%d %H:%M:%S')
                        lesson_date = lesson_datetime.strftime('%d.%m.%Y')
                        lesson_time = lesson_datetime.strftime('%H:%M')
                        
                        response_text += f"• {lesson_date} в {lesson_time} - {lesson['duration']} мин.\n"
                        if lesson['price']:
                            response_text += f"  Стоимость: {lesson['price']} руб.\n"
                        response_text += "\n"
                        
                        lesson_count += 1
                    except (ValueError, KeyError) as e:
                        print(f"Ошибка обработки занятия {lesson}: {e}")
                        continue
                
                response_text += f"\n<b>Всего запланировано:</b> {lesson_count} занятий\n\n"
                response_text += "⏰ Не забудьте подготовиться к занятиям!"
            else:
                response_text = "📅 <b>Предстоящие занятия</b>\n\n"
                response_text += "На ближайший месяц у вас нет запланированных занятий.\n\n"
                response_text += "📞 Свяжитесь с репетитором для планирования занятий."
        else:
            response_text = "❌ Не удалось найти данные ученика"
        
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
    """Обработчик кнопки 'Назад в меню' для ученика"""
    try:
        # Получаем данные ученика из базы
        student = db.get_student_by_telegram_id(callback_query.from_user.id)
        
        if student:
            # Получаем информацию о репетиторе
            tutor = db.get_tutor_by_id(student['tutor_id'])
            
            if tutor:
                welcome_text = f"""
<b>Добрый день, {student['full_name']}!</b>

Вы прикреплены к репетитору <b>{tutor[2]}</b>.

Здесь вы можете посмотреть свои домашние работы, задолженности и предстоящие занятия.
"""
            else:
                welcome_text = f"Добрый день, {student['full_name']}! Вы прикреплены к репетитору."
        else:
            welcome_text = "Добро пожаловать!"
        
        await callback_query.message.edit_text(
            welcome_text,
            parse_mode="HTML",
            reply_markup=get_student_welcome_keyboard()
        )
        
    except Exception as e:
        await callback_query.message.answer("❌ Произошла ошибка при возврате в меню")
        print(f"Ошибка в handle_back_to_student_menu: {e}")
    
    await callback_query.answer()