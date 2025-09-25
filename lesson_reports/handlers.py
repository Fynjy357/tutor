import logging
import sqlite3
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from datetime import datetime
import asyncio
from handlers.start.welcome import show_main_menu
from parent_report.handlers import ParentReportHandlers

logger = logging.getLogger(__name__)

# Состояния для индивидуальных занятий
class IndividualLessonStates(StatesGroup):
    LESSON_HELD = State()
    LESSON_PAID = State()
    HOMEWORK_DONE = State()
    PERFORMANCE = State()

# Состояния для групповых занятий
class GroupLessonStates(StatesGroup):
    LESSON_HELD = State()
    STUDENT_ATTENDANCE = State()
    STUDENT_PAID = State()
    STUDENT_HOMEWORK = State()
    STUDENT_PERFORMANCE = State()

class LessonReportHandlers:
    def __init__(self, db):
        self.db = db
        self.router = Router()
        self.parent_reports = ParentReportHandlers(db)
        self.setup_handlers()

    def setup_handlers(self):
        """Настройка обработчиков"""
        # Индивидуальные занятия
        self.router.callback_query(F.data.startswith("individual_report:"))(
            self.start_individual_report
        )
        self.router.callback_query(F.data.in_(["held_yes", "held_no"]))(
            self.handle_individual_lesson_held
        )
        self.router.callback_query(F.data.in_(["paid_yes", "paid_no"]))(
            self.handle_individual_lesson_paid
        )
        self.router.callback_query(F.data.in_(["homework_yes", "homework_no"]))(
            self.handle_individual_homework_done
        )
        self.router.message(IndividualLessonStates.PERFORMANCE)(
            self.handle_individual_performance
        )

        # Групповые занятия
        self.router.callback_query(F.data.startswith("group_report:"))(
            self.start_group_report
        )
        self.router.callback_query(F.data.in_(["group_held_yes", "group_held_no"]))(
            self.handle_group_lesson_held
        )
        self.router.callback_query(F.data.startswith("attend_"))(
            self.handle_group_student_attendance
        )
        self.router.callback_query(F.data.startswith("paid_"))(
            self.handle_group_student_paid
        )
        self.router.callback_query(F.data.startswith("homework_"))(
            self.handle_group_student_homework
        )
        self.router.message(GroupLessonStates.STUDENT_PERFORMANCE)(
            self.handle_group_student_performance
        )

        # Команда отмены
        self.router.message(Command("cancel"))(
            self.cancel_report
        )

    async def notify_tutor_about_lesson_end(self, bot):
        """Уведомляет репетитора об окончании занятия"""
        logger.info("🚀 Запуск планировщика уведомлений о завершении занятий")
        while True:
            try:
                logger.info("🔍 Проверка завершенных занятий...")
                now = datetime.now()
                now_str = now.strftime('%Y-%m-%d %H:%M:%S')
                
                with self.db.get_connection() as conn:
                    conn.row_factory = sqlite3.Row
                    cursor = conn.cursor()
                    
                    # Получаем ID первого занятия в группе для callback_data
                    cursor.execute('''
                    SELECT l.group_id, l.lesson_date, l.duration, 
                        t.telegram_id as tutor_telegram_id,
                        g.name as group_name,
                        COUNT(l.id) as student_count,
                        GROUP_CONCAT(s.full_name) as student_names,
                        MIN(l.id) as first_lesson_id  -- Берем первый ID для callback
                    FROM lessons l
                    JOIN tutors t ON l.tutor_id = t.id
                    LEFT JOIN groups g ON l.group_id = g.id
                    LEFT JOIN students s ON l.student_id = s.id
                    WHERE l.status = 'planned'
                    AND datetime(l.lesson_date, '+' || l.duration || ' minutes') 
                    BETWEEN datetime(?) AND datetime(?, '+5 minutes')
                    GROUP BY l.group_id, l.lesson_date, l.duration, t.telegram_id, g.name
                    ''', (now_str, now_str))
                    
                    lessons = cursor.fetchall()
                    logger.info(f"Найдено завершенных занятий (группировано): {len(lessons)}")
                    
                    for lesson in lessons:
                        lesson_dict = dict(lesson)
                        tutor_id = lesson_dict['tutor_telegram_id']
                        group_id = lesson_dict['group_id']
                        start_time = lesson_dict['lesson_date']
                        duration = lesson_dict['duration']
                        first_lesson_id = lesson_dict['first_lesson_id']
                        
                        if group_id:  # Групповое занятие
                            logger.info(f"👥 Групповое занятие: группа={lesson_dict['group_name']}, "
                                    f"ID={first_lesson_id}, учеников={lesson_dict['student_count']}")
                            
                            message = f"🎓 Групповое занятие '{lesson_dict['group_name']}' завершено!\n"
                            message += f"📅 Время: {start_time}\n"
                            message += f"⏱ Длительность: {duration} мин\n"
                            message += f"👥 Учеников: {lesson_dict['student_count']}\n\n"
                            message += "Заполните отчет по занятию:"
                            
                            keyboard = InlineKeyboardBuilder()
                            keyboard.button(
                                text="📝 Заполнить отчет", 
                                callback_data=f"group_report:{first_lesson_id}"
                            )
                            
                        else:  # Индивидуальное занятие
                            logger.info(f"👤 Индивидуальное занятие: ученик={lesson_dict['student_names']}")
                            
                            message = f"🎓 Занятие с {lesson_dict['student_names']} завершено!\n"
                            message += f"📅 Время: {start_time}\n"
                            message += f"⏱ Длительность: {duration} мин\n\n"
                            message += "Заполните отчет по занятию:"
                            
                            keyboard = InlineKeyboardBuilder()
                            keyboard.button(
                                text="📝 Заполнить отчет", 
                                callback_data=f"individual_report:{first_lesson_id}"
                            )
                        
                        reply_markup = keyboard.as_markup()
                        
                        try:
                            await bot.send_message(
                                chat_id=tutor_id,
                                text=message,
                                reply_markup=reply_markup
                            )
                            
                            # Обновляем статус ВСЕХ занятий этой группы
                            if group_id:
                                cursor.execute('''
                                UPDATE lessons 
                                SET status = 'completed' 
                                WHERE group_id = ? AND lesson_date = ? AND status = 'planned'
                                ''', (group_id, start_time))
                            else:
                                student_name = lesson_dict['student_names']
                                cursor.execute('''
                                UPDATE lessons 
                                SET status = 'completed' 
                                WHERE student_id IN (
                                    SELECT id FROM students WHERE full_name = ?
                                ) AND lesson_date = ? AND status = 'planned'
                                ''', (student_name, start_time))
                            
                            conn.commit()
                            
                            logger.info(f"✅ Уведомление отправлено репетитору {tutor_id}")
                            
                        except Exception as e:
                            logger.error(f"❌ Ошибка отправки уведомления: {e}")
                
                await asyncio.sleep(60)
                
            except Exception as e:
                logger.error(f"❌ Ошибка в фоновой задаче: {e}")
                await asyncio.sleep(60)
                

    async def start_individual_report(self, callback: CallbackQuery, state: FSMContext):
        """Начинает заполнение отчета для индивидуального занятия"""
        lesson_id = int(callback.data.split(':')[1])
        lesson = self.db.get_lesson_by_id(lesson_id)
        
        if not lesson:
            await callback.message.edit_text("❌ Занятие не найдено")
            return
        
        await state.update_data(
            report_lesson_id=lesson_id,
            report_student_id=lesson['student_id'],
            report_type='individual'
        )
        
        keyboard = InlineKeyboardBuilder()
        keyboard.button(text="✅ Да", callback_data="held_yes")
        keyboard.button(text="❌ Нет", callback_data="held_no")
        
        await callback.message.edit_text(
            f"📝 Отчет по занятию с {lesson['student_name']}\n\n"
            "1. Занятие состоялось?",
            reply_markup=keyboard.as_markup()
        )
        
        await state.set_state(IndividualLessonStates.LESSON_HELD)

    async def handle_individual_lesson_held(self, callback: CallbackQuery, state: FSMContext):
        """Обрабатывает ответ о проведении занятия"""
        lesson_held = callback.data == "held_yes"
        data = await state.get_data()
        lesson_id = data['report_lesson_id']
        student_id = data['report_student_id']
        
        self.db.save_lesson_report(lesson_id, student_id, lesson_held=lesson_held)
        
        if not lesson_held:
            await callback.message.edit_text(
                "✅ Отчет сохранен: Занятие не состоялось"
            )
            await state.clear()
            return
        
        keyboard = InlineKeyboardBuilder()
        keyboard.button(text="✅ Да", callback_data="paid_yes")
        keyboard.button(text="❌ Нет", callback_data="paid_no")
        
        await callback.message.edit_text(
            "2. Занятие оплачено?",
            reply_markup=keyboard.as_markup()
        )
        
        await state.set_state(IndividualLessonStates.LESSON_PAID)

    async def handle_individual_lesson_paid(self, callback: CallbackQuery, state: FSMContext):
        """Обрабатывает ответ об оплате"""
        lesson_paid = callback.data == "paid_yes"
        data = await state.get_data()
        lesson_id = data['report_lesson_id']
        student_id = data['report_student_id']
        
        self.db.save_lesson_report(lesson_id, student_id, lesson_paid=lesson_paid)
        
        keyboard = InlineKeyboardBuilder()
        keyboard.button(text="✅ Да", callback_data="homework_yes")
        keyboard.button(text="❌ Нет", callback_data="homework_no")
        
        await callback.message.edit_text(
            "3. Домашняя работа выполнена?",
            reply_markup=keyboard.as_markup()
        )
        
        await state.set_state(IndividualLessonStates.HOMEWORK_DONE)

    async def handle_individual_homework_done(self, callback: CallbackQuery, state: FSMContext):
        """Обрабатывает ответ о домашней работе"""
        homework_done = callback.data == "homework_yes"
        data = await state.get_data()
        lesson_id = data['report_lesson_id']
        student_id = data['report_student_id']
        
        self.db.save_lesson_report(lesson_id, student_id, homework_done=homework_done)
        
        await callback.message.edit_text(
            "4. Как ученик работал на занятии?\n\n"
            "Опишите работу ученика:"
        )
        
        await state.set_state(IndividualLessonStates.PERFORMANCE)

    async def handle_individual_performance(self, message: Message, state: FSMContext):
        """Обрабатывает описание работы ученика и возвращает в главное меню"""
        performance = message.text
        data = await state.get_data()
        lesson_id = data['report_lesson_id']
        student_id = data['report_student_id']
        
        self.db.save_lesson_report(lesson_id, student_id, student_performance=performance)
        
        lesson = self.db.get_lesson_by_id(lesson_id)
        
        await message.answer(
            f"✅ Отчет по занятию с {lesson['student_name']} сохранен!\n\n"
            f"📝 Ваш комментарий: {performance}"
        )
        await self.parent_reports.send_report_to_parent(message.bot, lesson_id, student_id)
        
        # Очищаем состояние
        await state.clear()
        
        # ЗАМЕНА: Используем универсальную функцию для возврата в главное меню
        await show_main_menu(
            chat_id=message.from_user.id,
            message=message
        )


    async def start_group_report(self, callback: CallbackQuery, state: FSMContext):
        """Начинает заполнение отчета для группового занятия"""
        lesson_id = int(callback.data.split(':')[1])
        
        logger.info(f"🔍 Поиск группового занятия ID: {lesson_id}")
        
        # Получаем информацию о занятии
        with self.db.get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('''
            SELECT l.*, g.name as group_name 
            FROM lessons l 
            LEFT JOIN groups g ON l.group_id = g.id 
            WHERE l.id = ?
            ''', (lesson_id,))
            lesson = cursor.fetchone()
            
            if lesson:
                lesson = dict(lesson)
                logger.info(f"📋 Найдено занятие: {lesson}")
        
        if not lesson or not lesson.get('group_id'):
            await callback.message.edit_text("❌ Групповое занятие не найдено")
            return
        
        # Получаем ВСЕ уроки этой группы на эту дату с их ID
        with self.db.get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('''
            SELECT l.id as lesson_id, s.id as student_id, s.full_name 
            FROM lessons l
            JOIN students s ON l.student_id = s.id
            WHERE l.group_id = ? AND l.lesson_date = ?
            ''', (lesson['group_id'], lesson['lesson_date']))
            student_lessons = [dict(row) for row in cursor.fetchall()]
        
        logger.info(f"👥 Уроков в группе: {len(student_lessons)}")
        
        if not student_lessons:
            await callback.message.edit_text("❌ В группе нет учеников")
            return
        
        await state.update_data(
            report_group_id=lesson['group_id'],
            report_lesson_date=lesson['lesson_date'],
            report_type='group',
            current_student_index=0,
            group_student_lessons=student_lessons  # Теперь храним список уроков с их ID
        )
        
        keyboard = InlineKeyboardBuilder()
        keyboard.button(text="✅ Да", callback_data="group_held_yes")
        keyboard.button(text="❌ Нет", callback_data="group_held_no")
        
        await callback.message.edit_text(
            f"📝 Отчет по групповому занятию '{lesson.get('group_name', 'Группа')}'\n\n"
            f"👥 Учеников: {len(student_lessons)}\n\n"
            "1. Занятие состоялось?",
            reply_markup=keyboard.as_markup()
        )
        
        await state.set_state(GroupLessonStates.LESSON_HELD)

    async def handle_group_lesson_held(self, callback: CallbackQuery, state: FSMContext):
        """Обрабатывает ответ о проведении группового занятия"""
        lesson_held = callback.data == "group_held_yes"
        data = await state.get_data()
        student_lessons = data['group_student_lessons']
        
        if not lesson_held:
            # Для всех уроков группы сохраняем, что занятие не состоялось
            for student_lesson in student_lessons:
                self.db.save_lesson_report(
                    student_lesson['lesson_id'],  # Используем индивидуальный lesson_id
                    student_lesson['student_id'], 
                    lesson_held=False
                )
            
            await callback.message.edit_text(
                "✅ Отчет сохранен: Занятие не состоялось"
            )
            await state.clear()
            return
        
        if not student_lessons:
            await callback.message.edit_text("❌ В группе нет учеников")
            await state.clear()
            return
        
        await state.update_data(current_student_index=0)
        student_lesson = student_lessons[0]
        
        keyboard = InlineKeyboardBuilder()
        keyboard.button(text="✅ Был", callback_data=f"attend_yes:{student_lesson['student_id']}:{student_lesson['lesson_id']}")
        keyboard.button(text="❌ Не был", callback_data=f"attend_no:{student_lesson['student_id']}:{student_lesson['lesson_id']}")
        
        await callback.message.edit_text(
            f"👤 Ученик 1: {student_lesson['full_name']}\n\n"
            "2. Был на занятии?",
            reply_markup=keyboard.as_markup()
        )
        
        await state.set_state(GroupLessonStates.STUDENT_ATTENDANCE)

    async def handle_group_student_attendance(self, callback: CallbackQuery, state: FSMContext):
        """Обрабатывает ответ о присутствии ученика"""
        data_parts = callback.data.split(':')
        attended = data_parts[0] == "attend_yes"
        student_id = int(data_parts[1])
        lesson_id = int(data_parts[2])  # Получаем индивидуальный lesson_id
        
        self.db.save_lesson_report(lesson_id, student_id, lesson_held=attended)
        
        if not attended:
            await self.next_group_student(callback, state)
            return
        
        state_data = await state.get_data()
        student_lessons = state_data['group_student_lessons']
        student_lesson = next((s for s in student_lessons if s['student_id'] == student_id), None)
        
        if not student_lesson:
            await callback.message.edit_text("❌ Ошибка: ученик не найден")
            await state.clear()
            return
        
        keyboard = InlineKeyboardBuilder()
        keyboard.button(text="✅ Оплачено", callback_data=f"paid_yes:{student_id}:{lesson_id}")
        keyboard.button(text="❌ Не оплачено", callback_data=f"paid_no:{student_id}:{lesson_id}")
        
        await callback.message.edit_text(
            f"👤 {student_lesson['full_name']}\n\n"
            "3. Занятие оплачено?",
            reply_markup=keyboard.as_markup()
        )
        
        await state.set_state(GroupLessonStates.STUDENT_PAID)

    async def handle_group_student_paid(self, callback: CallbackQuery, state: FSMContext):
        """Обрабатывает ответ об оплате для ученика"""
        data_parts = callback.data.split(':')
        paid = data_parts[0] == "paid_yes"
        student_id = int(data_parts[1])
        lesson_id = int(data_parts[2])  # Получаем индивидуальный lesson_id
        
        self.db.save_lesson_report(lesson_id, student_id, lesson_paid=paid)
        
        state_data = await state.get_data()
        student_lessons = state_data['group_student_lessons']
        student_lesson = next((s for s in student_lessons if s['student_id'] == student_id), None)
        
        if not student_lesson:
            await callback.message.edit_text("❌ Ошибка: ученик не найден")
            await state.clear()
            return
        
        keyboard = InlineKeyboardBuilder()
        keyboard.button(text="✅ Выполнена", callback_data=f"homework_yes:{student_id}:{lesson_id}")
        keyboard.button(text="❌ Не выполнена", callback_data=f"homework_no:{student_id}:{lesson_id}")
        
        await callback.message.edit_text(
            f"👤 {student_lesson['full_name']}\n\n"
            "4. Домашняя работа выполнена?",
            reply_markup=keyboard.as_markup()
        )
        
        await state.set_state(GroupLessonStates.STUDENT_HOMEWORK)

    async def handle_group_student_homework(self, callback: CallbackQuery, state: FSMContext):
        """Обрабатывает ответ о домашней работе"""
        data_parts = callback.data.split(':')
        homework_done = data_parts[0] == "homework_yes"
        student_id = int(data_parts[1])
        lesson_id = int(data_parts[2])  # Получаем индивидуальный lesson_id
        
        self.db.save_lesson_report(lesson_id, student_id, homework_done=homework_done)
        
        await state.update_data(
            current_student_id=student_id,
            current_lesson_id=lesson_id  # Сохраняем lesson_id для использования в performance
        )
        
        state_data = await state.get_data()
        student_lessons = state_data['group_student_lessons']
        student_lesson = next((s for s in student_lessons if s['student_id'] == student_id), None)
        
        if not student_lesson:
            await callback.message.edit_text("❌ Ошибка: ученик не найден")
            await state.clear()
            return
        
        await callback.message.edit_text(
            f"👤 {student_lesson['full_name']}\n\n"
            "5. Как ученик работал на занятии?\n\n"
            "Опишите работу ученика:"
        )
        
        await state.set_state(GroupLessonStates.STUDENT_PERFORMANCE)

    async def handle_group_student_performance(self, message: Message, state: FSMContext):
        """Обрабатывает описание работы ученика"""
        performance = message.text
        state_data = await state.get_data()
        student_id = state_data['current_student_id']
        lesson_id = state_data['current_lesson_id']  # Используем сохраненный lesson_id
        
        self.db.save_lesson_report(lesson_id, student_id, student_performance=performance)
        
        await self.next_group_student(message, state)

    async def next_group_student(self, update, state: FSMContext):
        """Переходит к следующему ученику"""
        state_data = await state.get_data()
        student_lessons = state_data['group_student_lessons']
        current_index = state_data['current_student_index']
        
        current_index += 1
        await state.update_data(current_student_index=current_index)
        
        if current_index >= len(student_lessons):
            # Получаем информацию о группе для завершающего сообщения
            with self.db.get_connection() as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute('''
                SELECT g.name FROM groups g WHERE g.id = ?
                ''', (state_data['report_group_id'],))
                group_info = cursor.fetchone()
            
            group_name = group_info['name'] if group_info else 'Группа'
            
            if isinstance(update, Message):
                await update.answer(
                    f"✅ Отчет по групповому занятию '{group_name}' завершен!\n\n"
                    f"Отчеты сохранены для всех {len(student_lessons)} учеников"
                )
            else:
                await update.message.edit_text(
                    f"✅ Отчет по групповому занятию '{group_name}' завершен!\n\n"
                    f"Отчеты сохранены для всех {len(student_lessons)} учеников"
                )

            # Отправляем отчеты всем родителям по одному
            for student_lesson in student_lessons:
                try:
                    await self.parent_reports.send_report_to_parent(
                        update.bot, student_lesson['lesson_id'], student_lesson['student_id']
                    )
                except Exception as e:
                    logger.error(f"❌ Ошибка при отправке отчета для ученика {student_lesson['student_id']}: {e}")
            
            await state.clear()
            return
        
        student_lesson = student_lessons[current_index]
        
        keyboard = InlineKeyboardBuilder()
        keyboard.button(text="✅ Был", callback_data=f"attend_yes:{student_lesson['student_id']}:{student_lesson['lesson_id']}")
        keyboard.button(text="❌ Не был", callback_data=f"attend_no:{student_lesson['student_id']}:{student_lesson['lesson_id']}")
        
        if isinstance(update, Message):
            await update.answer(
                f"👤 Ученик {current_index + 1}: {student_lesson['full_name']}\n\n"
                "2. Был на занятии?",
                reply_markup=keyboard.as_markup()
            )
        else:
            await update.message.edit_text(
                f"👤 Ученик {current_index + 1}: {student_lesson['full_name']}\n\n"
                "2. Был на занятии?",
                reply_markup=keyboard.as_markup()
            )
        
        await state.set_state(GroupLessonStates.STUDENT_ATTENDANCE)


    async def cancel_report(self, message: Message, state: FSMContext):
        """Отменяет заполнение отчета"""
        await message.answer("❌ Заполнение отчета отменено")
        
        # Очищаем данные отчета
        current_data = await state.get_data()
        
        if 'report_lesson_id' in current_data:
            await state.update_data(report_lesson_id=None)
        if 'report_student_id' in current_data:
            await state.update_data(report_student_id=None)
        if 'report_group_id' in current_data:
            await state.update_data(report_group_id=None)
        if 'report_type' in current_data:
            await state.update_data(report_type=None)
        if 'group_students' in current_data:
            await state.update_data(group_students=None)
        if 'current_student_index' in current_data:
            await state.update_data(current_student_index=None)
        if 'current_student_id' in current_data:
            await state.update_data(current_student_id=None)
        
        await state.clear()

    def get_handlers(self):
        """Возвращает обработчики для отчетов"""
        return [self.router]