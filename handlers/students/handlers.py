# handlers/students/handlers.py
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest
import logging

from .states import AddStudentStates
from .keyboards import get_invite_keyboard, get_student_detail_keyboard
from .utils import format_student_info, get_students_stats
from keyboards.students import get_students_menu_keyboard, get_cancel_keyboard, get_students_list_keyboard
from keyboards.registration import get_phone_keyboard
from database import db

router = Router()
logger = logging.getLogger(__name__)

# Обработчик начала добавления ученика
@router.callback_query(F.data == "add_student")
async def add_student_start(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.answer()
    await state.set_state(AddStudentStates.waiting_for_name)
    
    try:
        await callback_query.message.edit_text(
            "👤 <b>Добавление нового ученика</b>\n\n"
            "Введите ФИО ученика:",
            reply_markup=get_cancel_keyboard(),
            parse_mode="HTML"
        )
    except TelegramBadRequest:
        await callback_query.message.answer(
            "👤 <b>Добавление нового ученика</b>\n\n"
            "Введите ФИО ученика:",
            reply_markup=get_cancel_keyboard(),
            parse_mode="HTML"
        )

# Обработчик ввода имени ученика
@router.message(AddStudentStates.waiting_for_name)
async def process_student_name(message: types.Message, state: FSMContext):
    if not message.text or len(message.text.strip()) < 2:
        await message.answer("Пожалуйста, введите корректное ФИО ученика (минимум 2 символа):")
        return
    
    await state.update_data(full_name=message.text.strip())
    await state.set_state(AddStudentStates.waiting_for_phone)
    
    await message.answer(
        "📞 Введите номер телефона ученика (или '-' если нет телефона):",
        reply_markup=get_phone_keyboard()
    )

# Обработчик ввода телефона ученика
@router.message(AddStudentStates.waiting_for_phone)
async def process_student_phone(message: types.Message, state: FSMContext):
    phone = message.text.strip() if message.text else "-"
    
    await state.update_data(phone=phone)
    await state.set_state(AddStudentStates.waiting_for_parent_phone)
    
    await message.answer(
        "👨‍👩‍👧‍👦 Введите номер телефона родителя (или '-' если не требуется):",
        reply_markup=get_cancel_keyboard()
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
            f"✅ <b>Ученик успешно добавлен!</b>\n\n"
            f"👤 ФИО: {data['full_name']}\n"
            f"📞 Телефон: {data['phone']}\n"
            f"👨‍👩‍👧‍👦 Телефон родителя: {parent_phone}\n\n"
            f"Теперь вы можете отправить приглашение ученику и родителю.",
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
@router.callback_query(AddStudentStates, F.data == "cancel_operation")
async def cancel_add_student(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.answer()
    await state.clear()
    
    try:
        await callback_query.message.edit_text(
            "👥 <b>Учет учеников</b>\n\n"
            "Здесь вы можете управлять вашими учениками: добавлять новых, "
            "просматривать и редактировать информацию о существующих.",
            reply_markup=get_students_menu_keyboard(),
            parse_mode="HTML"
        )
    except TelegramBadRequest:
        await callback_query.message.answer(
            "👥 <b>Учет учеников</b>\n\n"
            "Здесь вы можете управлять вашими учениками: добавлять новых, "
            "просматривать и редактировать информацию о существующих.",
            reply_markup=get_students_menu_keyboard(),
            parse_mode="HTML"
        )

# Обработчик для кнопки приглашения
@router.callback_query(F.data.startswith("invite_"))
async def invite_menu(callback_query: types.CallbackQuery):
    await callback_query.answer()
    
    student_id = int(callback_query.data.split("_")[1])
    student = db.get_student_by_id(student_id)
    
    if not student:
        await callback_query.message.edit_text("❌ Ученик не найден!")
        return
    
    await callback_query.message.edit_text(
        f"👤 <b>Приглашение для {student['full_name']}</b>\n\n"
        "Выберите, кого вы хотите пригласить:",
        parse_mode="HTML",
        reply_markup=get_invite_keyboard(student_id)
    )

# Обработчик возврата к ученику из меню приглашения
@router.callback_query(F.data.startswith("back_to_student_"))
async def back_to_student_from_invite(callback_query: types.CallbackQuery):
    await callback_query.answer()
    
    student_id = int(callback_query.data.split("_")[3])
    student = db.get_student_by_id(student_id)
    
    if not student:
        await callback_query.message.edit_text("❌ Ученик не найден!")
        return
    
    text = format_student_info(student)
    
    try:
        await callback_query.message.edit_text(
            text,
            reply_markup=get_student_detail_keyboard(student_id),
            parse_mode="HTML"
        )
    except TelegramBadRequest:
        await callback_query.message.answer(
            text,
            reply_markup=get_student_detail_keyboard(student_id),
            parse_mode="HTML"
        )

# Обработчик возврата к списку учеников
@router.callback_query(F.data == "back_to_students_list")
async def back_to_students_list(callback_query: types.CallbackQuery):
    await callback_query.answer()
    
    tutor_id = db.get_tutor_id_by_telegram_id(callback_query.from_user.id)
    
    if not tutor_id:
        await callback_query.message.edit_text("❌ Ошибка: не найден ID репетитора.")
        return
    
    students = db.get_students_by_tutor(tutor_id)
    
    if not students:
        await callback_query.message.edit_text(
            "📝 <b>Список учеников пуст</b>\n\n"
            "У вас пока нет добавленных учеников.",
            reply_markup=get_students_menu_keyboard(),
            parse_mode="HTML"
        )
        return
    
    text = "👥 <b>Список ваших учеников</b>\n\n" + get_students_stats(students)
    
    try:
        await callback_query.message.edit_text(
            text,
            reply_markup=get_students_list_keyboard(students, page=0),
            parse_mode="HTML"
        )
    except TelegramBadRequest:
        await callback_query.message.answer(
            text,
            reply_markup=get_students_list_keyboard(students, page=0),
            parse_mode="HTML"
        )

# Обработчик переключения страниц списка учеников
@router.callback_query(F.data.startswith("students_page_"))
async def students_list_page(callback_query: types.CallbackQuery):
    await callback_query.answer()
    
    page = int(callback_query.data.split("_")[2])
    tutor_id = db.get_tutor_id_by_telegram_id(callback_query.from_user.id)
    
    if not tutor_id:
        await callback_query.message.edit_text("❌ Ошибка: не найден ID репетитора.")
        return
    
    students = db.get_students_by_tutor(tutor_id)
    text = "👥 <b>Список ваших учеников</b>\n\n" + get_students_stats(students)
    
    await callback_query.message.edit_text(
        text,
        reply_markup=get_students_list_keyboard(students, page=page),
        parse_mode="HTML"
    )