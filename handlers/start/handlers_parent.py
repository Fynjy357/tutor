from aiogram import types, Router, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database import db
from datetime import datetime
import logging

from handlers.start.keyboards_start import get_parent_welcome_keyboard
from handlers.start.welcome import show_parent_welcome  # Импортируем функцию из welcome.py

# Создаем роутер
parent_router = Router()
logger = logging.getLogger(__name__)

def get_back_to_parent_menu_keyboard() -> InlineKeyboardMarkup:
    """Создает клавиатуру с кнопкой 'Назад'"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="⬅️ Назад в меню", 
                    callback_data="back_to_parent_menu"
                )
            ]
        ]
    )
    return keyboard

@parent_router.callback_query(F.data == "parent_tutors")
async def handle_parent_tutors(callback_query: types.CallbackQuery):
    """Обработчик кнопки 'Репетиторы вашего ребенка'"""
    try:
        # Получаем репетиторов родителя
        tutors = db.get_tutors_for_parent(callback_query.from_user.id)
        
        if tutors:
            # Убираем дубликаты
            unique_tutors = {tutor['id']: tutor for tutor in tutors}.values()
            
            tutor_list = "\n".join([f"• {tutor['full_name']} - {tutor['phone']}" 
                                  for tutor in unique_tutors])
            
            await callback_query.message.edit_text(
                f"👨‍🏫 <b>Репетиторы ваших детей:</b>\n\n"
                f"{tutor_list}\n\n"
                f"Всего репетиторов: {len(unique_tutors)}",
                parse_mode="HTML",
                reply_markup=get_back_to_parent_menu_keyboard()
            )
        else:
            await callback_query.message.edit_text(
                "👨‍🏫 <b>Репетиторы ваших детей пока не назначены.</b>\n\n"
                "Как только репетиторы будут назначены и появятся занятия, "
                "вы сможете увидеть их здесь.",
                parse_mode="HTML",
                reply_markup=get_back_to_parent_menu_keyboard()
            )
            
    except Exception as e:
        logger.error(f"❌ Ошибка в handle_parent_tutors: {e}")
        await callback_query.message.answer("❌ Произошла ошибка при получении данных о репетиторах")
    
    await callback_query.answer()

@parent_router.callback_query(F.data == "parent_unpaid_lessons")
async def handle_parent_debts(callback_query: types.CallbackQuery):
    """Обработчик кнопки 'Посмотреть задолженности' - ИСПРАВЛЕННАЯ ВЕРСИЯ"""
    try:
        # Получаем неоплаченные занятия родителя
        unpaid_lessons = db.get_parent_unpaid_lessons(callback_query.from_user.id)
        
        # Дополнительная фильтрация на случай, если SQL запрос возвращает лишние записи
        filtered_unpaid = []
        for lesson in unpaid_lessons:
            # Проверяем, что занятие действительно не оплачено
            if lesson.get('lesson_paid') == 0 or lesson.get('lesson_paid') is None:
                filtered_unpaid.append(lesson)
        
        if filtered_unpaid:
            response_text = "💰 <b>Неоплаченные занятия:</b>\n\n"
            total_debt = 0
            
            # Группируем по ученикам
            students_debts = {}
            for lesson in filtered_unpaid:
                student_name = lesson.get('student_name', 'Неизвестный ученик')
                if student_name not in students_debts:
                    students_debts[student_name] = []
                students_debts[student_name].append(lesson)
                total_debt += lesson['price']
            
            for student_name, lessons in students_debts.items():
                student_total = sum(lesson['price'] for lesson in lessons)
                response_text += f"👤 <b>{student_name}:</b>\n"
                response_text += f"   Неоплачено занятий: {len(lessons)}\n"
                response_text += f"   Сумма: {student_total} руб.\n\n"
            
            response_text += f"💵 <b>Общая задолженность:</b> {total_debt} руб.\n\n"
            response_text += "💳 Для оплаты свяжитесь с репетитором."
        else:
            response_text = "✅ <b>Все занятия оплачены!</b>\n\nУ ваших детей нет задолженностей."
        
        # Добавим отладочную информацию
        logger.info(f"Родитель {callback_query.from_user.id}: найдено {len(unpaid_lessons)} занятий, после фильтрации {len(filtered_unpaid)}")
        
        await callback_query.message.edit_text(
            response_text,
            parse_mode="HTML",
            reply_markup=get_back_to_parent_menu_keyboard()
        )
        
    except Exception as e:
        logger.error(f"❌ Ошибка в handle_parent_debts: {e}")
        await callback_query.message.answer("❌ Произошла ошибка при получении данных о задолженностях")
    
    await callback_query.answer()

@parent_router.callback_query(F.data == "parent_homeworks")
async def handle_parent_homeworks(callback_query: types.CallbackQuery):
    """Обработчик кнопки 'Посмотреть домашние работы'"""
    try:
        # Получаем домашние задания родителя
        homeworks = db.get_parent_homeworks(callback_query.from_user.id)
        
        if homeworks:
            response_text = "📚 <b>Домашние задания ваших детей:</b>\n\n"
            
            # Группируем по ученикам
            students_homeworks = {}
            for hw in homeworks:
                student_name = hw.get('student_name', 'Неизвестный ученик')
                if student_name not in students_homeworks:
                    students_homeworks[student_name] = []
                students_homeworks[student_name].append(hw)
            
            for student_name, homeworks_list in students_homeworks.items():
                response_text += f"👤 <b>{student_name}:</b>\n"
                
                for hw in homeworks_list:
                    lesson_date = datetime.strptime(hw['lesson_date'], '%Y-%m-%d %H:%M:%S').strftime('%d.%m.%Y')
                    response_text += f"   • {lesson_date}"
                    if hw.get('tutor_name'):
                        response_text += f" - {hw['tutor_name']}"
                    response_text += "\n"
            
            response_text += "\n📝 Пожалуйста, помогите детям выполнить домашние задания."
        else:
            response_text = "📚 <b>Домашние задания отсутствуют</b>\n\nНа данный момент нет активных домашних заданий."
        
        await callback_query.message.edit_text(
            response_text,
            parse_mode="HTML",
            reply_markup=get_back_to_parent_menu_keyboard()
        )
        
    except Exception as e:
        logger.error(f"❌ Ошибка в handle_parent_homeworks: {e}")
        await callback_query.message.answer("❌ Произошла ошибка при получении данных о домашних работах")
    
    await callback_query.answer()

@parent_router.callback_query(F.data == "back_to_parent_menu")
async def handle_back_to_parent_menu(callback_query: types.CallbackQuery):
    """Обработчик кнопки 'Назад в меню' - возвращает в начальное меню из welcome.py"""
    try:
        # Получаем данные родителя
        main_parent = db.get_main_parent_by_telegram_id(callback_query.from_user.id)
        
        if main_parent:
            # Используем функцию из welcome.py для показа начального меню
            await show_parent_welcome(callback_query.message, main_parent)
        else:
            await callback_query.message.edit_text(
                "❌ Не удалось найти данные родителя",
                parse_mode="HTML"
            )
        
    except Exception as e:
        logger.error(f"❌ Ошибка в handle_back_to_parent_menu: {e}")
        await callback_query.message.answer("❌ Произошла ошибка при возврате в меню")
    
    await callback_query.answer()