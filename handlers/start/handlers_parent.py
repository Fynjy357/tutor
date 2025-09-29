from aiogram import types, Router, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database import db
from datetime import datetime
import logging
import sqlite3
import asyncio

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

def get_reports_keyboard() -> InlineKeyboardMarkup:
    """Создает клавиатуру для отчетов"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔄 Обновить", 
                    callback_data="parent_reports_refresh"
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ Назад в меню", 
                    callback_data="back_to_parent_menu"
                )
            ]
        ]
    )
    return keyboard

@parent_router.callback_query(F.data == "parent_reports")
async def handle_parent_reports(callback_query: types.CallbackQuery):
    """Обработчик кнопки 'Отчеты по занятиям'"""
    try:
        # Добавляем индикатор загрузки
        await callback_query.answer("🔄 Загружаем отчеты...")
        
        # Получаем последние 25 отчетов для родителя
        reports = get_parent_reports(callback_query.from_user.id)
        
        if not reports:
            await callback_query.message.edit_text(
                "📭 <b>Отчеты по занятиям</b>\n\n"
                "У вас пока нет отчетов по занятиям.\n"
                "Отчеты появятся после того, как преподаватель заполнит их.",
                parse_mode="HTML",
                reply_markup=get_back_to_parent_menu_keyboard()
            )
            return
        
        # Формируем сообщение с отчетами
        message_text = format_reports_message(reports)
        
        await callback_query.message.edit_text(
            message_text,
            parse_mode="HTML",
            reply_markup=get_reports_keyboard()
        )
        
    except Exception as e:
        logger.error(f"❌ Ошибка в handle_parent_reports: {e}")
        await callback_query.message.edit_text(
            "❌ Произошла ошибка при загрузке отчетов",
            reply_markup=get_back_to_parent_menu_keyboard()
        )
    
    await callback_query.answer()

@parent_router.callback_query(F.data == "parent_reports_refresh")
async def handle_parent_reports_refresh(callback_query: types.CallbackQuery):
    """Обработчик обновления списка отчетов"""
    try:
        # Сначала показываем уведомление об обновлении
        await callback_query.answer("🔄 Обновляем отчеты...")
        
        # Добавляем небольшую задержку чтобы избежать ошибки "message not modified"
        await asyncio.sleep(0.5)
        
        # Получаем обновленные отчеты
        reports = get_parent_reports(callback_query.from_user.id)
        
        if not reports:
            await callback_query.message.edit_text(
                "📭 <b>Отчеты по занятиям</b>\n\n"
                "У вас пока нет отчетов по занятиям.\n"
                "Отчеты появятся после того, как преподаватель заполнит их.",
                parse_mode="HTML",
                reply_markup=get_back_to_parent_menu_keyboard()
            )
            return
        
        # Формируем обновленное сообщение с временной меткой
        message_text = format_reports_message(reports)
        message_text += f"\n\n🔄 <i>Обновлено: {datetime.now().strftime('%H:%M:%S')}</i>"
        
        # Обновляем сообщение
        await callback_query.message.edit_text(
            message_text,
            parse_mode="HTML",
            reply_markup=get_reports_keyboard()
        )
        
    except Exception as e:
        logger.error(f"❌ Ошибка в handle_parent_reports_refresh: {e}")
        # Если возникает ошибка "message not modified", просто показываем уведомление
        await callback_query.answer("✅ Отчеты уже актуальны", show_alert=False)

def get_parent_reports(parent_telegram_id: int):
    """Получает последние 25 отчетов для родителя"""
    try:
        with db.get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('''
            SELECT 
                l.id as lesson_id,
                l.lesson_date,
                l.duration,
                s.full_name as student_name,
                t.full_name as tutor_name,
                lr.lesson_held,
                lr.lesson_paid,
                lr.homework_done,
                lr.student_performance,
                lr.parent_performance
            FROM lessons l
            JOIN students s ON l.student_id = s.id
            JOIN tutors t ON l.tutor_id = t.id
            LEFT JOIN lesson_reports lr ON l.id = lr.lesson_id AND lr.student_id = s.id
            WHERE s.parent_telegram_id = ?
            AND lr.lesson_held IS NOT NULL  -- только заполненные отчеты
            ORDER BY l.lesson_date DESC
            LIMIT 25
            ''', (parent_telegram_id,))
            return [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        logger.error(f"❌ Ошибка при получении отчетов из БД: {e}")
        return []

def format_reports_message(reports):
    """Форматирует сообщение с отчетами"""
    message_parts = ["<b>📋 Последние отчеты по занятиям:</b>\n"]
    
    for i, report in enumerate(reports, 1):
        # Форматируем дату
        lesson_date = report['lesson_date']
        if isinstance(lesson_date, str):
            lesson_date = lesson_date.split(' ')[0] if ' ' in lesson_date else lesson_date
        
        # Основная информация
        message_parts.append(
            f"\n<b>{i}. {report['student_name']}</b>\n"
            f"📅 {lesson_date} | ⏱ {report['duration']} мин\n"
            f"- - - - -"
        )
        
        # Статус присутствия
        if report['lesson_held']:
            message_parts.append("✅ Присутствовал")
            
            # Если присутствовал, показываем оплату и домашнюю работу
            payment_status = "✅ Оплачено" if report['lesson_paid'] else "❌ Не оплачено"
            homework_status = "✅ Домашняя работа" if report['homework_done'] else "❌ Домашняя работа"
            
            message_parts.append(payment_status)
            message_parts.append(homework_status)
            
            # Комментарий для преподавателя (если есть)
            if report.get('parent_performance'):
                message_parts.append(f"\n💬 <i>Комментарий: {report['parent_performance']}</i>")
        else:
            # Если отсутствовал, показываем только статус отсутствия и оплаты
            message_parts.append("❌ Отсутствовал")
            payment_status = "✅ Оплачено" if report['lesson_paid'] else "❌ Не оплачено"
            homework_status = "✅ Домашняя работа" if report['homework_done'] else "❌ Домашняя работа"
            message_parts.append(payment_status)
            message_parts.append(homework_status)

            if report.get('parent_performance'):
                message_parts.append(f"\n💬 <i>Комментарий: {report['parent_performance']}</i>")
        
        message_parts.append("- - - - -")
    
    # Убираем последний разделитель
    if message_parts and message_parts[-1] == "- - - - -":
        message_parts.pop()
    
    return "\n".join(message_parts)


# Остальной код без изменений...
@parent_router.callback_query(F.data == "parent_tutors")
async def handle_parent_tutors(callback_query: types.CallbackQuery):
    """Обработчик кнопки 'Репетиторы вашего ребенка'"""
    try:
        # Получаем репетиторы родителя
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
    """Обработчик кнопки 'Посмотреть задолженности' - ИСПРАВЛЕННАЯ ВЕРСИЯ С parent_performance"""
    try:
        # Получаем неоплаченные занятия родителя
        unpaid_lessons = db.get_parent_unpaid_lessons(callback_query.from_user.id)
        
        # ОТЛАДОЧНАЯ ИНФОРМАЦИЯ - посмотрим что приходит
        logger.info(f"🔍 ДАННЫЕ ОТ БАЗЫ: {unpaid_lessons}")
        
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
            
            # ДОПОЛНИТЕЛЬНАЯ ОТЛАДКА - посмотрим структуру данных
            logger.info(f"🔍 ГРУППИРОВКА ПО УЧЕНИКАМ: {students_debts}")
            
            for student_name, lessons in students_debts.items():
                student_total = sum(lesson['price'] for lesson in lessons)
                response_text += f"👤 <b>{student_name}:</b>\n"
                response_text += f"   Неоплачено занятий: {len(lessons)}\n"
                response_text += f"   Сумма: {student_total} руб.\n"
                
                # # Добавляем parent_performance для каждого ученика
                # parent_performance = lessons[0].get('parent_performance')
                
                response_text += "\n"
            
            response_text += f"💵 <b>Общая задолженность:</b> {total_debt} руб.\n\n"
            response_text += "💳 Для оплаты свяжитесь с репетитором."
            
        else:
            response_text = "✅ <b>Все занятия оплачены!</b>\n\nУ ваших детей нет задолженностей."
        
        # Добавим отладочную информацию
        
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
    logger.info(f"🚨 ФУНКЦИЯ handle_parent_homeworks ВЫЗВАНА для пользователя {callback_query.from_user.id}")
    try:
        # Получаем домашние задания родителя
        homeworks = db.get_parent_homeworks(callback_query.from_user.id)
        
        # ОТЛАДОЧНАЯ ИНФОРМАЦИЯ
        logger.info(f"🔍 ДАННЫЕ ОТ БАЗЫ (homeworks): {homeworks}")
        
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
                    
                    # ДОБАВЛЯЕМ ОПИСАНИЕ ДОМАШНЕГО ЗАДАНИЯ
                    if hw.get('homework_description'):
                        response_text += f"\n     📝 <i>Задание: {hw['homework_description']}</i>"
                    
                    # ДОБАВЛЯЕМ КОММЕНТАРИЙ ДЛЯ РОДИТЕЛЯ
                    parent_performance = hw.get('parent_performance')
                    if parent_performance:
                        response_text += f"\n     💬 <i>Комментарий: {parent_performance}</i>"
                    
                    response_text += "\n"
                
                response_text += "\n"
            
            response_text += "📝 Пожалуйста, помогите детям выполнить домашние задания."
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
