import logging
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

logger = logging.getLogger(__name__)

class ReportUtils:
    @staticmethod
    async def cancel_report(message: Message, state: FSMContext):
        """Отменяет заполнение отчета"""
        await message.answer("❌ Заполнение отчета отменено")
        
        # Очищаем данные отчета
        current_data = await state.get_data()
        report_fields = [
            'report_lesson_id', 'report_student_id', 'report_group_id',
            'report_type', 'group_students', 'current_student_index',
            'current_student_id', 'group_student_lessons'
        ]
        
        for field in report_fields:
            if field in current_data:
                await state.update_data({field: None})
        
        await state.clear()

    @staticmethod
    def validate_lesson_data(lesson_data):
        """Проверяет корректность данных занятия"""
        required_fields = ['lesson_id', 'student_id', 'tutor_id']
        for field in required_fields:
            if not lesson_data.get(field):
                logger.error(f"❌ Отсутствует обязательное поле: {field}")
                return False
        return True
