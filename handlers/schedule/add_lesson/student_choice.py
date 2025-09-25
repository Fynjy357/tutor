from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database import db
from handlers.schedule.states import AddLessonStates
import logging


router = Router()
logger = logging.getLogger(__name__)

# Обработчик выбора ученика
@router.callback_query(AddLessonStates.choosing_students, F.data.startswith("add_lesson_student_"))
async def process_student_selection(callback_query: types.CallbackQuery, state: FSMContext):
    """Обработка выбора ученика"""
    await callback_query.answer()
    
    student_id = int(callback_query.data.split("_")[3]) # add_lesson_student_{id}
    await state.update_data(student_id=student_id)
    
    # Получаем данные для подтверждения
    data = await state.get_data()
    
    # Формируем текст подтверждения
    confirmation_text = "✅ <b>Подтвердите данные занятия:</b>\n\n"
    
    if data.get('frequency') == 'regular':
        weekdays = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
        confirmation_text += f"📅 День: {weekdays[data.get('weekday')]}\n"
        confirmation_text += f"⏰ Время: {data.get('time')}\n"
        # confirmation_text += "🔄 Тип: Регулярное\n"
    else:
        confirmation_text += f"📅 Дата: {data.get('date')}\n"
        confirmation_text += f"⏰ Время: {data.get('time')}\n"
        # confirmation_text += "📋 Тип: Единоразовое\n"
    
    # Получаем имя студента
    tutor_id = db.get_tutor_id_by_telegram_id(callback_query.from_user.id)
    students = db.get_students_by_tutor(tutor_id)
    student_name = next((s['full_name'] for s in students if s['id'] == data.get('student_id')), "Неизвестный ученик")
    
    confirmation_text += f"👤 Ученик: {student_name}\n"
    confirmation_text += f"📚 Тип занятия: {'Индивидуальное' if data.get('lesson_type') == 'individual' else 'Групповое'}"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Подтвердить", callback_data="confirm_lesson")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_students")]
    ])
    
    await callback_query.message.edit_text(
        confirmation_text,
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await state.set_state(AddLessonStates.confirmation)
