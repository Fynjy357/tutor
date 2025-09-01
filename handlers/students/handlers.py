# handlers/students/handlers.py
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import logging

from handlers.students.states import AddStudentStates
from keyboards.students import get_students_list_keyboard, get_students_menu_keyboard, get_cancel_keyboard
from keyboards.registration import get_phone_keyboard
from database import db

router = Router()
logger = logging.getLogger(__name__)

def get_invite_keyboard(student_id):
    """Создает клавиатуру для меню приглашений"""
    keyboard = [
        [InlineKeyboardButton(text="👤 Пригласить ученика", callback_data=f"invite_student_{student_id}")],
        [InlineKeyboardButton(text="👨‍👩‍👧‍👦 Пригласить родителя", callback_data=f"invite_parent_{student_id}")],
        [InlineKeyboardButton(text="◀️ Назад к ученику", callback_data=f"back_to_student_{student_id}")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_student_detail_keyboard(student_id):
    """Создает клавиатуру для детальной информации об ученике"""
    keyboard = [
        [InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"edit_student_{student_id}")],
        [InlineKeyboardButton(text="📤 Пригласить", callback_data=f"invite_{student_id}")],
        [InlineKeyboardButton(text="◀️ Назад к списку", callback_data="back_to_students_list")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

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
        # Если сообщение уже удалено, отправляем новое
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
    
    # Получаем все данные из состояния
    data = await state.get_data()
    
    # Получаем ID текущего репетитора
    tutor_id = db.get_tutor_id_by_telegram_id(message.from_user.id)
    
    if not tutor_id:
        await message.answer("❌ Ошибка: не найден ID репетитора. Пожалуйста, зарегистрируйтесь заново.")
        await state.clear()
        return
    
    # Сохраняем ученика в базу со статусом "active" по умолчанию
    student_id = db.add_student(
        full_name=data['full_name'],
        phone=data['phone'],
        parent_phone=parent_phone,
        status="active",  # Статус по умолчанию
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
        
        # Показываем меню учеников
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
    
    # Формируем текст сообщения
    status_text = student['status']
    if student.get('delete_after'):
        status_text = f"{status_text} (будет удален {student['delete_after']})"
    
    student_tg = f"@{student['student_username']}" if student.get('student_username') else "не привязан"
    parent_tg = f"@{student['parent_username']}" if student.get('parent_username') else "не привязан"
    
    text = (
        f"👤 <b>Информация об ученике</b>\n\n"
        f"<b>ФИО:</b> {student['full_name']}\n"
        f"<b>Телефон:</b> {student['phone'] if student['phone'] != '-' else 'не указан'}\n"
        f"<b>Телефон родителя:</b> {student['parent_phone'] if student['parent_phone'] != '-' else 'не указан'}\n"
        f"<b>Статус:</b> {status_text}\n"
        f"<b>ТГ ученика:</b> {student_tg}\n"
        f"<b>ТГ родителя:</b> {parent_tg}\n"
        f"<b>Дата добавления:</b> {student['created_at']}"
    )
    
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
    
    # Получаем ID текущего репетитора
    tutor_id = db.get_tutor_id_by_telegram_id(callback_query.from_user.id)
    
    if not tutor_id:
        await callback_query.message.edit_text("❌ Ошибка: не найден ID репетитора.")
        return
    
    # Получаем список учеников
    students = db.get_students_by_tutor(tutor_id)
    
    if not students:
        await callback_query.message.edit_text(
            "📝 <b>Список учеников пуст</b>\n\n"
            "У вас пока нет добавленных учеников.",
            reply_markup=get_students_menu_keyboard(),
            parse_mode="HTML"
        )
        return
    
    # Формируем текст сообщения
    text = "👥 <b>Список ваших учеников</b>\n\n"
    
    # Добавляем информацию о количестве
    active_count = sum(1 for s in students if s['status'].lower() == 'active')
    text += f"Всего учеников: {len(students)}\n"
    text += f"Активных: {active_count}\n\n"
    
    # Показываем первую страницу списка
    from keyboards.students import get_students_list_keyboard
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
@router.callback_query(F.data.startswith("students_page_"))
async def students_list_page(callback_query: types.CallbackQuery):
    await callback_query.answer()
    
    # Получаем номер страницы из callback_data
    page = int(callback_query.data.split("_")[2])
    
    # Получаем ID текущего репетитора
    tutor_id = db.get_tutor_id_by_telegram_id(callback_query.from_user.id)
    
    if not tutor_id:
        await callback_query.message.edit_text("❌ Ошибка: не найден ID репетитора.")
        return
    
    # Получаем список учеников
    students = db.get_students_by_tutor(tutor_id)
    
    # Формируем текст сообщения
    text = "👥 <b>Список ваших учеников</b>\n\n"
    
    # Добавляем информацию о количестве
    active_count = sum(1 for s in students if s['status'].lower() == 'active')
    text += f"Всего учеников: {len(students)}\n"
    text += f"Активных: {active_count}\n\n"
    
    # Обновляем сообщение с новой страницей
    await callback_query.message.edit_text(
        text,
        reply_markup=get_students_list_keyboard(students, page=page),
        parse_mode="HTML"
    )
