from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest
import logging

from handlers.students.config import ANSWER_ADD_STUDENT, PARENTS_PHONE_NUMBER, STUDENT_MENU, STUDENT_PHONE_NUMBER
from handlers.students.keyboards_student import get_cancel_keyboard_add_students, get_students_menu_keyboard
from handlers.students.states import AddStudentStates
from keyboards.keyboard_phone import get_phone_keyboard


from database import db

router = Router()
logger = logging.getLogger(__name__)

# Обработчик ввода имени ученика
@router.message(AddStudentStates.waiting_for_name)
async def process_student_name(message: types.Message, state: FSMContext):
    if not message.text or len(message.text.strip()) < 2:
        await message.answer("Пожалуйста, введите корректное ФИО ученика (минимум 2 символа):")
        return
    
    await state.update_data(full_name=message.text.strip())
    await state.set_state(AddStudentStates.waiting_for_phone)
    
    await message.answer(
        STUDENT_PHONE_NUMBER,
        reply_markup=get_phone_keyboard()
    )

# Обработчик ввода телефона ученика
@router.message(AddStudentStates.waiting_for_phone)
async def process_student_phone(message: types.Message, state: FSMContext):
    phone = message.text.strip() if message.text else "-"
    
    await state.update_data(phone=phone)
    await state.set_state(AddStudentStates.waiting_for_parent_phone)
    
    await message.answer(
        PARENTS_PHONE_NUMBER,
        reply_markup=get_cancel_keyboard_add_students()
    )

# Обработчик ввода телефона родителя и сохранения ученика
@router.message(AddStudentStates.waiting_for_parent_phone)
async def process_parent_phone_and_save(message: types.Message, state: FSMContext):
    parent_phone = message.text.strip() if message.text else "-"
    
    data = await state.get_data()
    tutor_id = db.get_tutor_id_by_telegram_id(message.from_user.id)
    
    if not tutor_id:
        await message.answer("❌ Ошибка: не найден ID репетитора. Пожалуйста, зарегистрируйтесь заново.")
        await state.clear()
        return
    
    student_id = db.add_student(
        full_name=data['full_name'],
        phone=data['phone'],
        parent_phone=parent_phone,
        status="active",
        tutor_id=tutor_id
    )
    
    if student_id:
        await message.answer(
        ANSWER_ADD_STUDENT.format(
        full_name=data['full_name'],
        phone=data['phone'],
        parent_phone=parent_phone
        ),
            parse_mode="HTML"
        )
        
        await message.answer(
            "👥 <b>Учет учеников</b>\n\n"
            "Выберите действие:",
            reply_markup=get_students_menu_keyboard(),
            parse_mode="HTML"
        )
    else:
        await message.answer(
            "❌ <b>Ошибка при добавлении ученика!</b>\n\n"
            "Пожалуйста, попробуйте позже или обратитесь к администратору.",
            parse_mode="HTML"
        )
    
    await state.clear()

    # Обработчик отмены добавления ученика
@router.callback_query(F.data == "cancel_operation")
async def cancel_add_student(callback_query: types.CallbackQuery, state: FSMContext):
    current_state = await state.get_state()
    
    # Проверяем, находимся ли мы в состоянии добавления ученика
    if current_state and current_state.startswith("AddStudentStates"):
        await callback_query.answer()
        await state.clear()
        
        try:
            await callback_query.message.edit_text(
                STUDENT_MENU,
                reply_markup=get_students_menu_keyboard(),
                parse_mode="HTML"
            )
        except TelegramBadRequest:
            await callback_query.message.answer(
                STUDENT_MENU,
                reply_markup=get_students_menu_keyboard(),
                parse_mode="HTML"
            )
    else:
        await callback_query.answer("Операция не активна")