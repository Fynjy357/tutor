import logging
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder

from .states import IndividualLessonStates

logger = logging.getLogger(__name__)

class IndividualLessonHandler:
    def __init__(self, db, parent_reports):
        self.db = db
        self.parent_reports = parent_reports

    async def start_individual_report(self, callback: CallbackQuery, state: FSMContext):
        """Начинает заполнение отчета по индивидуальному занятию"""
        lesson_id = int(callback.data.split(":")[1])
        
        # Получаем данные о занятии
        lesson_data = self.db.get_lesson_by_id(lesson_id)
        if not lesson_data:
            await callback.message.answer("❌ Занятие не найдено")
            return
        
        await state.update_data(
            report_lesson_id=lesson_id,
            report_student_id=lesson_data['student_id'],
            report_type='individual'
        )
        
        # Спрашиваем, состоялось ли занятие
        keyboard = InlineKeyboardBuilder()
        keyboard.button(text="✅ Да", callback_data="held_yes")
        keyboard.button(text="❌ Нет", callback_data="held_no")
        
        await callback.message.answer(
            f"🎓 Занятие с {lesson_data['student_name']}\n"
            f"📅 {lesson_data['lesson_date']}\n\n"
            "Присутствовал ли ученик на занятии?",
            reply_markup=keyboard.as_markup()
        )
        await state.set_state(IndividualLessonStates.LESSON_HELD)

    async def handle_lesson_held(self, callback: CallbackQuery, state: FSMContext):
        """Обрабатывает ответ о проведении занятия"""
        lesson_held = callback.data == "held_yes"
        await state.update_data(lesson_held=lesson_held)
        
        # ВСЕГДА спрашиваем об оплате
        keyboard = InlineKeyboardBuilder()
        keyboard.button(text="✅ Оплачено", callback_data="paid_yes")
        keyboard.button(text="❌ Не оплачено", callback_data="paid_no")
        
        await callback.message.answer("💳 Занятие оплачено?", reply_markup=keyboard.as_markup())
        await state.set_state(IndividualLessonStates.LESSON_PAID)

    async def handle_lesson_paid(self, callback: CallbackQuery, state: FSMContext):
        """Обрабатывает ответ об оплате"""
        await state.update_data(lesson_paid=callback.data == "paid_yes")
        
        # ВСЕГДА спрашиваем о домашнем задании
        keyboard = InlineKeyboardBuilder()
        keyboard.button(text="✅ Сделано", callback_data="homework_yes")
        keyboard.button(text="❌ Не сделано", callback_data="homework_no")
        
        await callback.message.answer("📚 Домашнее задание выполнено?", reply_markup=keyboard.as_markup())
        await state.set_state(IndividualLessonStates.HOMEWORK_DONE)

    async def handle_homework_done(self, callback: CallbackQuery, state: FSMContext):
        """Обрабатывает ответ о домашнем задании"""
        await state.update_data(homework_done=callback.data == "homework_yes")
        
        # ВСЕГДА спрашиваем об успехах ученика
        data = await state.get_data()
        lesson_held = data.get('lesson_held', True)
        
        if lesson_held:
            await callback.message.answer("💬 Этот ответ получит ученик. Вы можете добавить здесь комментарий для ученика или описать домашнюю работу. /n Можно поставить -")
        else:
            await callback.message.answer("💬 Этот ответ получит ученик. Опишите ситуацию с занятием (почему не состоялось, долги по домашней работе и т.д.):/n Можно поставить -")
        
        await state.set_state(IndividualLessonStates.STUDENT_PERFORMANCE)

    async def handle_performance(self, message: Message, state: FSMContext):
        """Обрабатывает описание успехов ученика"""
        student_performance = message.text
        await state.update_data(student_performance=student_performance)
        
        # ВСЕГДА спрашиваем заметку для родителей
        data = await state.get_data()
        lesson_held = data.get('lesson_held', True)
        
        if lesson_held:
            await message.answer(
                "👨‍👩‍👧‍👦 Заметка для родителей:\n"
                "Напишите комментарий для родителей ученика "
                "(о прогрессе, рекомендациях, важных моментах):\n"
                "Можно указать -\n"
            )
        else:
            await message.answer(
                "👨‍👩‍👧‍👦 **Заметка для родителей:**\n"
                "Напишите комментарий для родителей ученика "
                "(о причинах отмены, дальнейших планах, рекомендациях):\n"
                "Можно указать -\n"
            )
        
        await state.set_state(IndividualLessonStates.PARENT_PERFORMANCE)

    async def handle_parent_performance(self, message: Message, state: FSMContext, bot):
        """Обрабатывает заметку для родителей и завершает отчет"""
        parent_performance = message.text
        data = await state.get_data()
        
        # Сохраняем полный отчет со ВСЕМИ данными
        success = self.db.save_lesson_report(
            lesson_id=data['report_lesson_id'],
            student_id=data['report_student_id'],
            lesson_held=data.get('lesson_held', True),
            lesson_paid=data.get('lesson_paid'),
            homework_done=data.get('homework_done'),
            student_performance=data.get('student_performance'),
            parent_performance=parent_performance
        )
        
        if success:
            # Отправляем отчет родителям
            await self.parent_reports.send_report_to_parent(
                bot=bot,
                lesson_id=data['report_lesson_id'],
                student_id=data['report_student_id']
            )
            
            await message.answer("✅ Отчет успешно сохранен и отправлен родителям!")
        else:
            await message.answer("❌ Ошибка сохранения отчета")
        
        await state.clear()
