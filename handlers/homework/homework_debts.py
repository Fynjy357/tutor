# handlers/homework/homework_debts.py
from aiogram import Router, types, F
from database import Database
from datetime import datetime
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton
import traceback

router = Router()

def get_tutor_id(telegram_id: int) -> int:
    """Получить tutor_id по telegram_id"""
    db = Database()
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT id FROM tutors WHERE telegram_id = ?', (telegram_id,))
        result = cursor.fetchone()
        return result[0] if result else None

def get_homework_debts_keyboard():
    """Клавиатура для раздела долгов по домашним работам"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="⬅️ Назад к статистике", 
            callback_data="statistics_menu"
        )
    )
    return builder.as_markup()

def get_students_with_homework_debts_keyboard(tutor_id):
    """Клавиатура со списком студентов с долгами по домашним работам"""
    db = Database()
    builder = InlineKeyboardBuilder()
    
    try:
        print(f"🔍 DEBUG: Получение студентов с долгами по ДЗ для tutor_id={tutor_id}")
        
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
            SELECT DISTINCT s.id, s.full_name 
            FROM students s
            JOIN lessons l ON s.id = l.student_id
            JOIN lesson_reports lr ON l.id = lr.lesson_id
            WHERE l.tutor_id = ? 
            AND lr.lesson_held = 1  -- Только проведенные занятия
            AND (lr.homework_done = 0 OR lr.homework_done IS NULL)
            AND l.status != 'cancelled'
            ORDER BY s.full_name
            ''', (tutor_id,))
            
            students = cursor.fetchall()
            print(f"🔍 DEBUG: Найдено студентов с долгами по ДЗ: {len(students)}")
            
            for student_id, student_name in students:
                builder.row(
                    InlineKeyboardButton(
                        text=f"👤 {student_name}",
                        callback_data=f"new_homework_debt_student_{student_id}"
                    )
                )
    except Exception as e:
        print(f"❌ ERROR в get_students_with_homework_debts_keyboard: {e}")
        print(f"🔍 TRACEBACK: {traceback.format_exc()}")
    
    builder.row(
        InlineKeyboardButton(
            text="⬅️ Назад", 
            callback_data="statistics_menu"
        )
    )
    
    return builder.as_markup()

def get_student_homework_debts_keyboard(student_id, tutor_id):
    """Клавиатура с датами долгов по домашним работам конкретного студента"""
    db = Database()
    builder = InlineKeyboardBuilder()
    
    try:
        print(f"🔍 DEBUG: Получение занятий с долгами по ДЗ для student_id={student_id}, tutor_id={tutor_id}")
        
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
            SELECT l.id, l.lesson_date, lr.student_performance
            FROM lessons l
            JOIN lesson_reports lr ON l.id = lr.lesson_id
            WHERE l.student_id = ? 
            AND l.tutor_id = ?
            AND lr.lesson_held = 1  -- Только проведенные занятия
            AND (lr.homework_done = 0 OR lr.homework_done IS NULL)
            AND l.status != 'cancelled'
            ORDER BY l.lesson_date DESC
            ''', (student_id, tutor_id))
            
            lessons = cursor.fetchall()
            print(f"🔍 DEBUG: Найдено занятий с долгами по ДЗ: {len(lessons)}")
            
            for lesson_id, lesson_date, comment in lessons:
                date_str = datetime.strptime(lesson_date, '%Y-%m-%d %H:%M:%S').strftime('%d.%m.%Y')
                builder.row(
                    InlineKeyboardButton(
                        text=f"📅 {date_str}",
                        callback_data=f"new_mark_homework_done_{lesson_id}"
                    )
                )
    except Exception as e:
        print(f"❌ ERROR в get_student_homework_debts_keyboard: {e}")
        print(f"🔍 TRACEBACK: {traceback.format_exc()}")
    
    builder.row(
        InlineKeyboardButton(
            text="⬅️ К списку учеников", 
            callback_data="new_homework_debts_menu"
        )
    )
    
    return builder.as_markup()

@router.callback_query(F.data == "new_homework_debts_menu")
async def show_new_homework_debts_menu(callback: types.CallbackQuery):
    """Показать меню долгов по домашним работам"""
    db = Database()
    
    try:
        print(f"🔍 DEBUG: Запуск show_new_homework_debts_menu для пользователя {callback.from_user.id}")
        
        # Получаем tutor_id
        tutor_id = get_tutor_id(callback.from_user.id)
        if not tutor_id:
            print(f"❌ ERROR: Репетитор с telegram_id={callback.from_user.id} не найден")
            await callback.message.edit_text(
                text="❌ Репетитор не найден в системе",
                reply_markup=get_homework_debts_keyboard()
            )
            return
        
        with db.get_connection() as conn:
            cursor = conn.cursor()
            print(f"🔍 DEBUG: Выполнение SQL запроса для получения долгов по ДЗ для tutor_id={tutor_id}")
            
            cursor.execute('''
            SELECT s.full_name, l.lesson_date, lr.student_performance
            FROM students s
            JOIN lessons l ON s.id = l.student_id
            JOIN lesson_reports lr ON l.id = lr.lesson_id
            WHERE l.tutor_id = ? 
            AND lr.lesson_held = 1  -- Только проведенные занятия
            AND (lr.homework_done = 0 OR lr.homework_done IS NULL)
            AND l.status != 'cancelled'
            ORDER BY l.lesson_date DESC
            ''', (tutor_id,))
            
            debts = cursor.fetchall()
            print(f"🔍 DEBUG: Найдено записей с долгами по ДЗ: {len(debts)}")
            
            if not debts:
                text = "📚 <b>Долги по домашним работам</b>\n\n📭 Все домашние работы выполнены!"
                print("🔍 DEBUG: Нет долгов по ДЗ - показываем сообщение 'Все домашние работы выполнены'")
            else:
                text = "📚 <b>Долги по домашним работам</b>\n\n"
                for student_name, lesson_date, comment in debts:
                    date_str = datetime.strptime(lesson_date, '%Y-%m-%d %H:%M:%S').strftime('%d.%m.%Y')
                    comment_text = f" - {comment}" if comment else ""
                    text += f"📅 {date_str} - 👤 {student_name}{comment_text}\n"
                print(f"🔍 DEBUG: Сформирован текст с {len(debts)} долгами по ДЗ")
            
            await callback.message.edit_text(
                text=text,
                reply_markup=get_students_with_homework_debts_keyboard(tutor_id),
                parse_mode="HTML"
            )
            print("🔍 DEBUG: Сообщение успешно отправлено")
            
    except Exception as e:
        print(f"❌ ERROR в show_new_homework_debts_menu: {e}")
        print(f"🔍 TRACEBACK: {traceback.format_exc()}")
        await callback.message.edit_text(
            text="❌ Ошибка при загрузке долгов по домашним работам",
            reply_markup=get_homework_debts_keyboard()
        )

@router.callback_query(F.data.startswith("new_homework_debt_student_"))
async def show_student_homework_debts(callback: types.CallbackQuery):
    """Показать долги по домашним работам конкретного студента"""
    student_id = int(callback.data.split("_")[-1])
    db = Database()
    
    try:
        print(f"🔍 DEBUG: Запуск show_student_homework_debts для student_id={student_id}, пользователя {callback.from_user.id}")
        
        # Получаем tutor_id
        tutor_id = get_tutor_id(callback.from_user.id)
        if not tutor_id:
            print(f"❌ ERROR: Репетитор с telegram_id={callback.from_user.id} не найден")
            await callback.message.edit_text(
                text="❌ Репетитор не найден в системе",
                reply_markup=get_homework_debts_keyboard()
            )
            return
        
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            # Получаем имя студента с проверкой
            print(f"🔍 DEBUG: Поиск студента с id={student_id}")
            cursor.execute('SELECT full_name FROM students WHERE id = ?', (student_id,))
            student_data = cursor.fetchone()
            
            if not student_data:
                print(f"❌ ERROR: Студент с id={student_id} не найден")
                await callback.message.edit_text(
                    text="❌ Студент не найден",
                    reply_markup=get_homework_debts_keyboard()
                )
                return
                
            student_name = student_data[0]
            print(f"🔍 DEBUG: Найден студент: {student_name}")
            
            # Получаем занятия с долгами по ДЗ
            print(f"🔍 DEBUG: Поиск занятий с долгами по ДЗ для студента")
            cursor.execute('''
            SELECT l.lesson_date, lr.student_performance
            FROM lessons l
            JOIN lesson_reports lr ON l.id = lr.lesson_id
            WHERE l.student_id = ? 
            AND l.tutor_id = ?
            AND lr.lesson_held = 1  -- Только проведенные занятия
            AND (lr.homework_done = 0 OR lr.homework_done IS NULL)
            AND l.status != 'cancelled'
            ORDER BY l.lesson_date DESC
            ''', (student_id, tutor_id))
            
            lessons = cursor.fetchall()
            print(f"🔍 DEBUG: Найдено занятий с долгами по ДЗ: {len(lessons)}")
            
            text = f"📚 <b>Долги по домашним работам</b>\n\n👤 <b>{student_name}</b>\n\n"
            
            if not lessons:
                text += "📭 Все домашние работы выполнены!"
                print("🔍 DEBUG: У студента нет долгов по ДЗ")
            else:
                total_debt = 0
                for lesson_date, comment in lessons:
                    date_str = datetime.strptime(lesson_date, '%Y-%m-%d %H:%M:%S').strftime('%d.%m.%Y')
                    comment_text = f" - {comment}" if comment else ""
                    text += f"📅 {date_str}{comment_text}\n"
                    total_debt += 1
                
                text += f"\n📊 Всего невыполненных домашних работ: {total_debt}"
                print(f"🔍 DEBUG: У студента {total_debt} невыполненных домашних работ")
            
            await callback.message.edit_text(
                text=text,
                reply_markup=get_student_homework_debts_keyboard(student_id, tutor_id),
                parse_mode="HTML"
            )
            print("🔍 DEBUG: Сообщение с долгами по ДЗ студента успешно отправлено")
            
    except Exception as e:
        print(f"❌ ERROR в show_student_homework_debts: {e}")
        print(f"🔍 TRACEBACK: {traceback.format_exc()}")
        await callback.message.edit_text(
            text="❌ Ошибка при загрузке данных студента",
            reply_markup=get_homework_debts_keyboard()
        )

@router.callback_query(F.data.startswith("new_mark_homework_done_"))
async def mark_homework_as_done(callback: types.CallbackQuery):
    """Отметить домашнюю работу как выполненную"""
    lesson_id = int(callback.data.split("_")[-1])
    db = Database()
    
    try:
        print(f"🔍 DEBUG: Отметка домашней работы для занятия {lesson_id} как выполненной")
        
        # Получаем tutor_id
        tutor_id = get_tutor_id(callback.from_user.id)
        if not tutor_id:
            print(f"❌ ERROR: Репетитор с telegram_id={callback.from_user.id} не найден")
            await callback.answer("❌ Репетитор не найден в системе")
            return
        
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            # Получаем данные занятия
            cursor.execute('''
            SELECT l.student_id, s.full_name, l.lesson_date 
            FROM lessons l 
            JOIN students s ON l.student_id = s.id 
            WHERE l.id = ? AND l.tutor_id = ?
            ''', (lesson_id, tutor_id))
            
            lesson_data = cursor.fetchone()
            
            if not lesson_data:
                print(f"❌ ERROR: Занятие {lesson_id} не найдено")
                await callback.answer("❌ Занятие не найдено")
                return
            
            student_id, student_name, lesson_date = lesson_data
            
            # Проверяем существование записи в lesson_reports
            cursor.execute('SELECT id FROM lesson_reports WHERE lesson_id = ?', (lesson_id,))
            report_exists = cursor.fetchone()
            
            if report_exists:
                # Обновляем существующую запись
                cursor.execute('''
                UPDATE lesson_reports SET homework_done = 1 WHERE lesson_id = ?
                ''', (lesson_id,))
                print(f"🔍 DEBUG: Обновлена запись lesson_reports для занятия {lesson_id}")
            else:
                # Создаем новую запись
                cursor.execute('''
                INSERT INTO lesson_reports (lesson_id, student_id, homework_done)
                VALUES (?, ?, 1)
                ''', (lesson_id, student_id))
                print(f"🔍 DEBUG: Создана новая запись lesson_reports для занятия {lesson_id}")
            
            conn.commit()
            
            # Возвращаемся к списку студентов
            await show_new_homework_debts_menu(callback)
            await callback.answer("✅ Домашняя работа отмечена как выполненная")
            
    except Exception as e:
        print(f"❌ ERROR в mark_homework_as_done: {e}")
        print(f"🔍 TRACEBACK: {traceback.format_exc()}")
        await callback.answer("❌ Ошибка при обновлении статуса домашней работы")
