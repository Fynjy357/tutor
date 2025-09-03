# handlers/students/main.py
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest
from handlers.students.keyboards_student import get_students_menu_keyboard

router = Router()

@router.callback_query(F.data == "students")
async def handle_students_button(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.answer()
    
    # Очищаем состояние если было активно
    current_state = await state.get_state()
    if current_state:
        await state.clear()
    
    text = (
        "👥 <b>Учет учеников</b>\n\n"
        "Здесь вы можете управлять вашими учениками: добавлять новых, "
        "просматривать и редактировать информацию о существующих."
    )
    
    try:
        await callback_query.message.edit_text(
            text,
            reply_markup=get_students_menu_keyboard(),
            parse_mode="HTML"
        )
    except TelegramBadRequest:
        await callback_query.message.answer(
            text,
            reply_markup=get_students_menu_keyboard(),
            parse_mode="HTML"
        )