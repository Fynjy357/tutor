# handlers/debt/payment_debts.py
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

def get_payment_debts_keyboard():
    """Клавиатура для раздела задолженностей по оплате"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="⬅️ Назад к статистике", 
            callback_data="statistics_menu"
        )
    )
    return builder.as_markup()

def get_students_with_payment_debts_keyboard(tutor_id):
    """Клавиатура со списком студентов с задолженностями"""
    db = Database()
    builder = InlineKeyboardBuilder()
    
    try:
        print(f"🔍 DEBUG: Получение студентов с задолженностями для tutor_id={tutor_id}")
        
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
            SELECT DISTINCT s.id, s.full_name 
            FROM students s
            JOIN lessons l ON s.id = l.student_id
            LEFT JOIN lesson_reports lr ON l.id = lr.lesson_id
            WHERE l.tutor_id = ? 
            AND lr.lesson_held = 1  -- Только проведенные занятия
            AND (lr.lesson_paid = 0 OR lr.lesson_paid IS NULL)
            AND l.status != 'cancelled'
            ORDER BY s.full_name
            ''', (tutor_id,))
            
            students = cursor.fetchall()
            print(f"🔍 DEBUG: Найдено студентов с задолженностями: {len(students)}")
            
            for student_id, student_name in students:
                builder.row(
                    InlineKeyboardButton(
                        text=f"👤 {student_name}",
                        callback_data=f"new_payment_debt_student_{student_id}"
                    )
                )
    except Exception as e:
        print(f"❌ ERROR в get_students_with_payment_debts_keyboard: {e}")
        print(f"🔍 TRACEBACK: {traceback.format_exc()}")
    
    builder.row(
        InlineKeyboardButton(
            text="⬅️ Назад", 
            callback_data="statistics_menu"
        )
    )
    
    return builder.as_markup()

def get_student_payment_debts_keyboard(student_id, tutor_id):
    """Клавиатура с датами задолженностей конкретного студента"""
    db = Database()
    builder = InlineKeyboardBuilder()
    
    try:
        print(f"🔍 DEBUG: Получение занятий с задолженностями для student_id={student_id}, tutor_id={tutor_id}")
        
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
            SELECT l.id, l.lesson_date, lr.lesson_paid
            FROM lessons l
            LEFT JOIN lesson_reports lr ON l.id = lr.lesson_id
            WHERE l.student_id = ? 
            AND l.tutor_id = ?
            AND lr.lesson_held = 1  -- Только проведенные занятия
            AND (lr.lesson_paid = 0 OR lr.lesson_paid IS NULL)
            AND l.status != 'cancelled'
            ORDER BY l.lesson_date DESC
            ''', (student_id, tutor_id))
            
            lessons = cursor.fetchall()
            print(f"🔍 DEBUG: Найдено занятий с задолженностями: {len(lessons)}")
            
            for lesson_id, lesson_date, lesson_paid in lessons:
                date_str = datetime.strptime(lesson_date, '%Y-%m-%d %H:%M:%S').strftime('%d.%m.%Y')
                builder.row(
                    InlineKeyboardButton(
                        text=f"📅 {date_str} - ❌ Не оплачено",
                        callback_data=f"new_mark_paid_{lesson_id}"
                    )
                )
    except Exception as e:
        print(f"❌ ERROR в get_student_payment_debts_keyboard: {e}")
        print(f"🔍 TRACEBACK: {traceback.format_exc()}")
    
    builder.row(
        InlineKeyboardButton(
            text="⬅️ К списку учеников", 
            callback_data="new_payment_debts_menu"
        )
    )
    
    return builder.as_markup()


@router.callback_query(F.data == "new_payment_debts_menu")
async def show_new_payment_debts_menu(callback: types.CallbackQuery):
    """Показать меню задолженностей по оплате"""
    db = Database()
    
    try:
        print(f"🔍 DEBUG: Запуск show_new_payment_debts_menu для пользователя {callback.from_user.id}")
        
        # Получаем tutor_id
        tutor_id = get_tutor_id(callback.from_user.id)
        if not tutor_id:
            print(f"❌ ERROR: Репетитор с telegram_id={callback.from_user.id} не найден")
            await callback.message.edit_text(
                text="❌ Репетитор не найден в системе",
                reply_markup=get_payment_debts_keyboard()
            )
            return
        
        with db.get_connection() as conn:
            cursor = conn.cursor()
            print(f"🔍 DEBUG: Выполнение SQL запроса для получения задолженностей для tutor_id={tutor_id}")
            
            cursor.execute('''
            SELECT s.full_name, l.lesson_date
            FROM students s
            JOIN lessons l ON s.id = l.student_id
            LEFT JOIN lesson_reports lr ON l.id = lr.lesson_id
            WHERE l.tutor_id = ? 
            AND lr.lesson_held = 1  -- Только проведенные занятия
            AND (lr.lesson_paid = 0 OR lr.lesson_paid IS NULL)
            AND l.status != 'cancelled'
            ORDER BY l.lesson_date DESC
            ''', (tutor_id,))
            
            debts = cursor.fetchall()
            print(f"🔍 DEBUG: Найдено записей с задолженностями: {len(debts)}")
            
            if not debts:
                text = "💰 <b>Задолженности по оплате</b>\n\n📭 Все занятия оплачены!"
                print("🔍 DEBUG: Нет задолженностей - показываем сообщение 'Все занятия оплачены'")
            else:
                text = "💰 <b>Задолженности по оплате</b>\n\n"
                for student_name, lesson_date in debts:
                    date_str = datetime.strptime(lesson_date, '%Y-%m-%d %H:%M:%S').strftime('%d.%m.%Y')
                    text += f"👤 {student_name} - {date_str} - ❌ Не оплачено\n"
                print(f"🔍 DEBUG: Сформирован текст с {len(debts)} задолженностями")
            
            print(f"🔍 DEBUG: Создание клавиатуры для меню")
            keyboard = get_students_with_payment_debts_keyboard(tutor_id)
            
            await callback.message.edit_text(
                text=text,
                reply_markup=keyboard,
                parse_mode="HTML"
            )
            print("🔍 DEBUG: Сообщение успешно отправлено")
            
    except Exception as e:
        print(f"❌ ERROR в show_new_payment_debts_menu: {e}")
        print(f"🔍 TRACEBACK: {traceback.format_exc()}")
        await callback.message.edit_text(
            text="❌ Ошибка при загрузке задолженностей",
            reply_markup=get_payment_debts_keyboard()
        )

@router.callback_query(F.data.startswith("new_payment_debt_student_"))
async def show_student_payment_debts(callback: types.CallbackQuery):
    """Показать задолженности конкретного студента"""
    student_id = int(callback.data.split("_")[-1])
    db = Database()
    
    try:
        print(f"🔍 DEBUG: Запуск show_student_payment_debts для student_id={student_id}, пользователя {callback.from_user.id}")
        
        # Получаем tutor_id
        tutor_id = get_tutor_id(callback.from_user.id)
        if not tutor_id:
            print(f"❌ ERROR: Репетитор с telegram_id={callback.from_user.id} не найден")
            await callback.message.edit_text(
                text="❌ Репетитор не найден в системе",
                reply_markup=get_payment_debts_keyboard()
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
                    reply_markup=get_payment_debts_keyboard()
                )
                return
                
            student_name = student_data[0]
            print(f"🔍 DEBUG: Найден студент: {student_name}")
            
            # Получаем занятия с задолженностями
            print(f"🔍 DEBUG: Поиск занятий с задолженностями для студента")
            cursor.execute('''
            SELECT l.id, l.lesson_date, lr.lesson_paid
            FROM lessons l
            LEFT JOIN lesson_reports lr ON l.id = lr.lesson_id
            WHERE l.student_id = ? 
            AND l.tutor_id = ?
            AND lr.lesson_held = 1  -- Только проведенные занятия
            AND (lr.lesson_paid = 0 OR lr.lesson_paid IS NULL)
            AND l.status != 'cancelled'
            ORDER BY l.lesson_date DESC
            ''', (student_id, tutor_id))
            
            lessons = cursor.fetchall()
            print(f"🔍 DEBUG: Найдено занятий с задолженностями: {len(lessons)}")
            
            text = f"💰 <b>Задолженности по оплате</b>\n\n👤 <b>{student_name}</b>\n\n"
            
            if not lessons:
                text += "✅ Все занятия оплачены!"
                print("🔍 DEBUG: У студента нет задолженностей")
            else:
                total_debt = 0
                for lesson_id, lesson_date, lesson_paid in lessons:
                    date_str = datetime.strptime(lesson_date, '%Y-%m-%d %H:%M:%S').strftime('%d.%m.%Y')
                    text += f"📅 {date_str} - ❌ Не оплачено\n"
                    total_debt += 1
                
                text += f"\n📊 Всего неоплаченных занятий: {total_debt}"
                print(f"🔍 DEBUG: У студента {total_debt} неоплаченных занятий")
            
            print(f"🔍 DEBUG: Создание клавиатуры для студента")
            keyboard = get_student_payment_debts_keyboard(student_id, tutor_id)
            
            await callback.message.edit_text(
                text=text,
                reply_markup=keyboard,
                parse_mode="HTML"
            )
            print("🔍 DEBUG: Сообщение с задолженностями студента успешно отправлено")
            
    except Exception as e:
        print(f"❌ ERROR в show_student_payment_debts: {e}")
        print(f"🔍 TRACEBACK: {traceback.format_exc()}")
        await callback.message.edit_text(
            text="❌ Ошибка при загрузке данных студента",
            reply_markup=get_payment_debts_keyboard()
        )


@router.callback_query(F.data.startswith("new_mark_paid_"))
async def mark_lesson_as_paid(callback: types.CallbackQuery):
    """Отметить занятие как оплаченное"""
    lesson_id = int(callback.data.split("_")[-1])
    db = Database()
    
    try:
        print(f"🔍 DEBUG: Отметка занятия {lesson_id} как оплаченного")
        
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
                UPDATE lesson_reports SET lesson_paid = 1 WHERE lesson_id = ?
                ''', (lesson_id,))
                print(f"🔍 DEBUG: Обновлена запись lesson_reports для занятия {lesson_id}")
            else:
                # Создаем новую запись
                cursor.execute('''
                INSERT INTO lesson_reports (lesson_id, student_id, lesson_paid)
                VALUES (?, ?, 1)
                ''', (lesson_id, student_id))
                print(f"🔍 DEBUG: Создана новая запись lesson_reports для занятия {lesson_id}")
            
            conn.commit()
            
            # Возвращаемся к списку студентов
            await show_new_payment_debts_menu(callback)
            await callback.answer("✅ Занятие отмечено как оплаченное")
            
    except Exception as e:
        print(f"❌ ERROR в mark_lesson_as_paid: {e}")
        print(f"🔍 TRACEBACK: {traceback.format_exc()}")
        await callback.answer("❌ Ошибка при обновлении статуса оплаты")
