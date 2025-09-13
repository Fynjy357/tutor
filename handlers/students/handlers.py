# handlers/students/handlers.py
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest
import logging

from handlers.schedule.schedule_utils import get_today_schedule_text
from handlers.start.config import WELCOME_BACK_TEXT
from handlers.students.config import ADD_STUDENT
from handlers.students.keyboards import get_invite_keyboard
from keyboards.main_menu import get_main_menu_keyboard

from .states import AddStudentStates

from .utils import get_students_stats
from handlers.students.keyboards_student import get_cancel_keyboard_add_students, get_students_menu_keyboard, get_students_pagination_keyboard
from .edit_handlers import router as edit_router
from database import db
from handlers.students.handlers_add_student import router as add_students_router
from handlers.students.handlers_edit_student import router as student_



router = Router()
router.include_router(add_students_router)
router.include_router(student_)
logger = logging.getLogger(__name__)

# Обработчик начала добавления ученика (логика в handlers_add_students)
@router.callback_query(F.data == "add_student")
async def add_student_start(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.answer()
    await state.set_state(AddStudentStates.waiting_for_name)
    
    try:
        await callback_query.message.edit_text(
        ADD_STUDENT,
            reply_markup=get_cancel_keyboard_add_students(),
            parse_mode="HTML"
        )
    except TelegramBadRequest:
        await callback_query.message.answer(
            ADD_STUDENT,
            reply_markup=get_cancel_keyboard_add_students(),
            parse_mode="HTML"
        )

# Обработчик списка учеников
@router.callback_query(F.data == "students_list")
async def students_list(callback_query: types.CallbackQuery):
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
            reply_markup=get_students_pagination_keyboard(students, page=0),
            parse_mode="HTML"
        )
    except TelegramBadRequest:
        await callback_query.message.answer(
            text,
            reply_markup=get_students_pagination_keyboard(students, page=0),
            parse_mode="HTML"
        )


# Обработчик для кнопки назад

@router.callback_query(F.data == "back_to_main_students")
async def back_to_main_menu(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.answer()
    
    # Очищаем состояние если было активно
    current_state = await state.get_state()
    if current_state:
        await state.clear()
    
    # Получаем данные репетитора
    tutor = db.get_tutor_by_telegram_id(callback_query.from_user.id)
    
    if not tutor:
        # Если репетитор не найден, показываем сообщение об ошибке
        try:
            await callback_query.message.edit_text(
                "❌ Ошибка: не найдены данные репетитора",
                parse_mode="HTML"
            )
        except TelegramBadRequest:
            await callback_query.message.answer(
                "❌ Ошибка: не найдены данные репетитора",
                parse_mode="HTML"
            )
        return
    
    # Используем функцию show_welcome_back для показа главного меню
    tutor_id = tutor[0]
    schedule_text = await get_today_schedule_text(tutor_id)
    # Проверяем активную подписку
    has_active_subscription = db.check_tutor_subscription(tutor_id)
    subscription_icon = "💎 " if has_active_subscription else ""
    
    welcome_message = f"{subscription_icon}{WELCOME_BACK_TEXT.format(tutor_name=tutor[2], schedule_text=schedule_text)}"

    try:
        # Пытаемся изменить текущее сообщение
        await callback_query.message.edit_text(
            welcome_message,
            reply_markup=get_main_menu_keyboard(),
            parse_mode="HTML"
        )
    except TelegramBadRequest:
        # Если не получается изменить, отправляем новое сообщение
        await callback_query.message.answer(
            welcome_message,
            reply_markup=get_main_menu_keyboard(),
            parse_mode="HTML"
        )


# # Обработчик возврата к ученику из меню приглашения
# @router.callback_query(F.data.startswith("back_to_student_"))
# async def back_to_student_from_invite(callback_query: types.CallbackQuery):
#     await callback_query.answer()
    
#     student_id = int(callback_query.data.split("_")[3])
#     student = db.get_student_by_id(student_id)
    
#     if not student:
#         await callback_query.message.edit_text("❌ Ученик не найден!")
#         return
    
#     text = format_student_info(student)
    
#     try:
#         await callback_query.message.edit_text(
#             text,
#             reply_markup=get_student_detail_keyboard(student_id),
#             parse_mode="HTML"
#         )
#     except TelegramBadRequest:
#         await callback_query.message.answer(
#             text,
#             reply_markup=get_student_detail_keyboard(student_id),
#             parse_mode="HTML"
#         )