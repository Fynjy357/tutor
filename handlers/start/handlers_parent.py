from aiogram import types, Router, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database import db
from datetime import datetime

from handlers.start.keyboards_start import get_parent_welcome_keyboard

# Создаем роутер
parent_router = Router()

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

@parent_router.callback_query(F.data == "parent_unpaid_lessons")
async def handle_parent_debts(callback_query: types.CallbackQuery):
    """Обработчик кнопки 'Посмотреть задолженности'"""
    try:
        # Получаем данные родителя из базы
        parent = db.get_parent_by_telegram_id(callback_query.from_user.id)
        
        if parent:
            # Получаем реальные неоплаченные занятия
            unpaid_lessons = db.get_student_unpaid_lessons(parent['id'])
            
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
                        # Если возникла ошибка с форматом даты или отсутствующим полем
                        print(f"Ошибка обработки занятия {lesson}: {e}")
                        continue
                
                response_text += f"\n<b>Всего неоплачено:</b> {lesson_count} занятий\n"
                response_text += f"<b>Общая сумма задолженности:</b> {total_debt} руб.\n\n"
                response_text += "💳 Для оплаты свяжитесь с репетитором."
            else:
                response_text = "✅ <b>Все занятия оплачены!</b>\n\nУ вас нет задолженностей по оплате занятий."
        else:
            response_text = "❌ Не удалось найти данные родителя"
        
        await callback_query.message.edit_text(
            response_text,
            parse_mode="HTML",
            reply_markup=get_back_to_parent_menu_keyboard()
        )
        
    except Exception as e:
        await callback_query.message.answer("❌ Произошла ошибка при получении данных о задолженностях")
        print(f"Ошибка в handle_parent_debts: {e}")
    
    await callback_query.answer()

@parent_router.callback_query(F.data == "back_to_parent_menu")
async def handle_back_to_parent_menu(callback_query: types.CallbackQuery):
    """Обработчик кнопки 'Назад в меню'"""
    try:
        # Получаем данные родителя из базы
        parent = db.get_parent_by_telegram_id(callback_query.from_user.id)
        
        if parent:
            # Получаем информацию о репетиторе
            tutor = db.get_tutor_by_id(parent['tutor_id'])
            
            if tutor:
                welcome_text = f"""
<b>Добрый день!</b>

Ваш ребенок (<b>{parent['full_name']}</b>) прикреплен к репетитору (<b>{tutor[2]}</b>).

Вы будете получать отчеты о прошедших занятиях.
"""
            else:
                welcome_text = f"Добрый день! Ваш ребенок ({parent['full_name']}) прикреплен к репетитору."
        else:
            welcome_text = "Добро пожаловать!"
        
        await callback_query.message.edit_text(
            welcome_text,
            parse_mode="HTML",
            reply_markup=get_parent_welcome_keyboard()
        )
        
    except Exception as e:
        await callback_query.message.answer("❌ Произошла ошибка при возврате в меню")
        print(f"Ошибка в handle_back_to_parent_menu: {e}")
    
    await callback_query.answer()

@parent_router.callback_query(F.data == "parent_homeworks")
async def handle_parent_homeworks(callback_query: types.CallbackQuery):
    """Обработчик кнопки 'Посмотреть невыполненные домашние работы'"""
    try:
        # Получаем данные родителя из базы
        parent = db.get_parent_by_telegram_id(callback_query.from_user.id)
        
        if parent:
            # Получаем невыполненные домашние работы
            undone_homeworks = db.get_student_undone_homeworks(parent['id'])
            
            if undone_homeworks:
                response_text = "📚 <b>Невыполненные домашние работы:</b>\n\n"
                homework_count = 0
                
                for homework in undone_homeworks:
                    try:
                        # Парсим дату занятия
                        lesson_date = datetime.strptime(homework['lesson_date'], '%Y-%m-%d %H:%M:%S').strftime('%d.%m.%Y')
                        response_text += f"• {lesson_date} - {homework['tutor_name']}\n"
                        
                        # Добавляем комментарий о выполнении, если есть (БЕЗ ОГРАНИЧЕНИЯ СИМВОЛОВ)
                        if homework['student_performance']:
                            response_text += f"  Комментарий: {homework['student_performance']}\n\n"
                        else:
                            response_text += "\n"
                        
                        homework_count += 1
                    except (ValueError, KeyError) as e:
                        print(f"Ошибка обработки домашней работы {homework}: {e}")
                        continue
                
                response_text += f"\n<b>Всего невыполнено:</b> {homework_count} домашних работ\n\n"
                response_text += "📝 Пожалуйста, помогите ребенку выполнить домашние задания."
            else:
                response_text = "✅ <b>Все домашние работы выполнены!</b>\n\nУ вашего ребенка нет невыполненных домашних заданий."
        else:
            response_text = "❌ Не удалось найти данные родителя"
        
        await callback_query.message.edit_text(
            response_text,
            parse_mode="HTML",
            reply_markup=get_back_to_parent_menu_keyboard()
        )
        
    except Exception as e:
        await callback_query.message.answer("❌ Произошла ошибка при получении данных о домашних работах")
        print(f"Ошибка в handle_parent_homeworks: {e}")
    
    await callback_query.answer()