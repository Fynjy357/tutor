import logging
import sqlite3
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from .states import GroupLessonStates

logger = logging.getLogger(__name__)

class GroupLessonHandler:
    def __init__(self, db, parent_reports):
        self.db = db
        self.parent_reports = parent_reports

    async def start_group_report(self, callback: CallbackQuery, state: FSMContext):
        """Начинает заполнение отчета для группового занятия"""
        lesson_id = int(callback.data.split(':')[1])
        
        logger.info(f"🔍 Поиск группового занятия ID: {lesson_id}")
        
        with self.db.get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('''
            SELECT l.*, g.name as group_name FROM lessons l 
            LEFT JOIN groups g ON l.group_id = g.id WHERE l.id = ?
            ''', (lesson_id,))
            lesson = cursor.fetchone()
            
            if lesson:
                lesson = dict(lesson)
                logger.info(f"📋 Найдено занятие: {lesson}")
        
        if not lesson or not lesson.get('group_id'):
            await callback.message.edit_text("❌ Групповое занятие не найдено")
            return
        
        with self.db.get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('''
            SELECT l.id as lesson_id, s.id as student_id, s.full_name 
            FROM lessons l JOIN students s ON l.student_id = s.id
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
            group_student_lessons=student_lessons,
            report_lesson_id=lesson_id
        )
        
        keyboard = InlineKeyboardBuilder()
        keyboard.button(text="✅ Да", callback_data="group_held_yes")
        keyboard.button(text="❌ Нет", callback_data="group_held_no")
        
        await callback.message.edit_text(
            f"📝 Отчет по групповому занятию '{lesson.get('group_name', 'Группа')}'\n\n"
            f"👥 Учеников: {len(student_lessons)}\n\nЗанятие состоялось?",
            reply_markup=keyboard.as_markup()
        )
        
        await state.set_state(GroupLessonStates.LESSON_HELD)

    async def handle_lesson_held(self, callback: CallbackQuery, state: FSMContext):
        """Обрабатывает ответ о проведении группового занятия"""
        lesson_held = callback.data == "group_held_yes"
        data = await state.get_data()
        student_lessons = data['group_student_lessons']
        
        if not lesson_held:
            # Если занятие не состоялось, завершаем отчет
            for student_lesson in student_lessons:
                self.db.save_lesson_report(
                    student_lesson['lesson_id'],
                    student_lesson['student_id'], 
                    lesson_held=False
                )
            
            await callback.message.edit_text("✅ Отчет сохранен: Занятие не состоялось")
            await state.clear()
            return
        
        # Если занятие состоялось, начинаем опрос по каждому ученику
        if not student_lessons:
            await callback.message.edit_text("❌ В группе нет учеников")
            await state.clear()
            return
        
        await state.update_data(current_student_index=0)
        await self._show_student_attendance(callback, state, student_lessons[0], 0)

    async def handle_student_attendance(self, callback: CallbackQuery, state: FSMContext):
        """Обрабатывает ответ о присутствии ученика"""
        data_parts = callback.data.split(':')
        attended = data_parts[0] == "attend_yes"
        student_id = int(data_parts[1])
        lesson_id = int(data_parts[2])
        
        # Сохраняем статус присутствия
        self.db.save_lesson_report(lesson_id, student_id, lesson_held=attended)
        
        # ВСЕГДА переходим к вопросу об оплате, независимо от присутствия
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
            f"👤 {student_lesson['full_name']}\n\n💳 Занятие оплачено?",
            reply_markup=keyboard.as_markup()
        )
        
        await state.set_state(GroupLessonStates.STUDENT_PAID)

    async def handle_student_paid(self, callback: CallbackQuery, state: FSMContext):
        """Обрабатывает ответ об оплате для ученика"""
        data_parts = callback.data.split(':')
        paid = data_parts[0] == "paid_yes"
        student_id = int(data_parts[1])
        lesson_id = int(data_parts[2])
        
        # Сохраняем статус оплаты
        self.db.save_lesson_report(lesson_id, student_id, lesson_paid=paid)
        
        # ВСЕГДА переходим к вопросу о домашней работе, независимо от присутствия
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
            f"👤 {student_lesson['full_name']}\n\n📚 Домашнее задание выполнено?",
            reply_markup=keyboard.as_markup()
        )
        
        await state.set_state(GroupLessonStates.STUDENT_HOMEWORK)

    async def handle_student_homework(self, callback: CallbackQuery, state: FSMContext):
        """Обрабатывает ответ о домашней работе"""
        data_parts = callback.data.split(':')
        homework_done = data_parts[0] == "homework_yes"
        student_id = int(data_parts[1])
        lesson_id = int(data_parts[2])
        
        # Сохраняем статус домашней работы
        self.db.save_lesson_report(lesson_id, student_id, homework_done=homework_done)
        
        await state.update_data(current_student_id=student_id, current_lesson_id=lesson_id)
        
        state_data = await state.get_data()
        student_lessons = state_data['group_student_lessons']
        student_lesson = next((s for s in student_lessons if s['student_id'] == student_id), None)
        
        if not student_lesson:
            await callback.message.edit_text("❌ Ошибка: ученик не найден")
            await state.clear()
            return
        
        # ВСЕГДА спрашиваем об успехах ученика, независимо от присутствия
        attended = state_data.get('lesson_held', True)
        
        if attended:
            await callback.message.edit_text(
                f"👤 {student_lesson['full_name']}\n\n💬 Этот ответ получит ученик. Вы можете добавить здесь комментарий для ученика или описать домашнюю работу. /n Можно поставить -"
            )
        else:
            await callback.message.edit_text(
                f"👤 {student_lesson['full_name']}\n\n💬 Этот ответ получит ученик. Опишите ситуацию с занятием (почему не состоялось, долги по домашней работе и т.д.):/n Можно поставить -"
            )
        
        await state.set_state(GroupLessonStates.STUDENT_PERFORMANCE)

    async def handle_student_performance(self, message: Message, state: FSMContext):
        """Обрабатывает описание работы ученика и переходит к заметке для родителей ЭТОГО ученика"""
        performance_text = message.text
        state_data = await state.get_data()
        student_id = state_data['current_student_id']
        lesson_id = state_data['current_lesson_id']
        
        # Сохраняем успехи для текущего ученика
        self.db.save_lesson_report(lesson_id, student_id, student_performance=performance_text)
        
        # ВСЕГДА спрашиваем заметку для родителей, независимо от присутствия
        student_lessons = state_data['group_student_lessons']
        student_lesson = next((s for s in student_lessons if s['student_id'] == student_id), None)
        
        if not student_lesson:
            await message.answer("❌ Ошибка: ученик не найден")
            await state.clear()
            return
        
        attended = state_data.get('lesson_held', True)
        
        if attended:
            await message.answer(
                f"👤 {student_lesson['full_name']}\n\n"
                f"Заметка для родителей этого ученика:\n"
                f"Напишите комментарий, который увидят родители {student_lesson['full_name']}:"
            )
        else:
            await message.answer(
                f"👤 {student_lesson['full_name']}\n\n"
                f"Заметка для родителей этого ученика:\n"
                f"Напишите комментарий для родителей (о причинах отсутствия, дальнейших планах и т.д.):"
            )
        
        await state.set_state(GroupLessonStates.PARENT_PERFORMANCE)

    async def _show_student_attendance(self, update, state: FSMContext, student_lesson, index):
        """Показывает вопрос о присутствии ученика"""
        keyboard = InlineKeyboardBuilder()
        keyboard.button(text="✅ Был", callback_data=f"attend_yes:{student_lesson['student_id']}:{student_lesson['lesson_id']}")
        keyboard.button(text="❌ Не был", callback_data=f"attend_no:{student_lesson['student_id']}:{student_lesson['lesson_id']}")
        
        if isinstance(update, Message):
            await update.answer(
                f"👤 Ученик {index + 1}: {student_lesson['full_name']}\n\nПрисутствовал на занятии?",
                reply_markup=keyboard.as_markup()
            )
        else:
            await update.message.edit_text(
                f"👤 Ученик {index + 1}: {student_lesson['full_name']}\n\nПрисутствовал на занятии?",
                reply_markup=keyboard.as_markup()
            )
        
        await state.set_state(GroupLessonStates.STUDENT_ATTENDANCE)

    async def _next_group_student(self, update, state: FSMContext):
        """Переходит к следующему ученику"""
        state_data = await state.get_data()
        student_lessons = state_data['group_student_lessons']
        current_index = state_data['current_student_index'] + 1
        
        await state.update_data(current_student_index=current_index)
        
        if current_index >= len(student_lessons):
            await self._finish_group_report(update, state, student_lessons)
            return
        
        await self._show_student_attendance(update, state, student_lessons[current_index], current_index)

    async def _finish_group_report(self, update, state: FSMContext, student_lessons):
        """Завершает отчет по группе"""
        state_data = await state.get_data()
        
        with self.db.get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('SELECT g.name FROM groups g WHERE g.id = ?', (state_data['report_group_id'],))
            group_info = cursor.fetchone()
        
        group_name = group_info['name'] if group_info else 'Группа'
        message_text = f"✅ Отчет по групповому занятию '{group_name}' завершен!\n\nОтчеты сохранены для всех {len(student_lessons)} учеников"
        
        if isinstance(update, Message):
            await update.answer(message_text)
        else:
            await update.message.edit_text(message_text)

        # Отправляем отчеты родителям
        for student_lesson in student_lessons:
            try:
                await self.parent_reports.send_report_to_parent(
                    bot=update.bot,
                    lesson_id=student_lesson['lesson_id'],
                    student_id=student_lesson['student_id']
                )
            except Exception as e:
                logger.error(f"❌ Ошибка при отправке отчета для ученика {student_lesson['student_id']}: {e}")
        
        await state.clear()

    async def handle_parent_performance(self, message: Message, state: FSMContext):
        """Обрабатывает заметку для родителей КОНКРЕТНОГО ученика"""
        parent_performance = message.text
        state_data = await state.get_data()
        student_id = state_data['current_student_id']
        lesson_id = state_data['current_lesson_id']
        
        # Сохраняем parent_performance для КОНКРЕТНОГО ученика
        self.db.save_lesson_report(lesson_id, student_id, parent_performance=parent_performance)
        
        # Теперь переходим к следующему ученику
        student_lessons = state_data['group_student_lessons']
        current_index = state_data['current_student_index'] + 1
        
        await state.update_data(current_student_index=current_index)
        
        if current_index < len(student_lessons):
            # Следующий ученик
            await self._show_student_attendance(message, state, student_lessons[current_index], current_index)
        else:
            # Все ученики обработаны - завершаем
            await self._finish_group_report(message, state, student_lessons)
