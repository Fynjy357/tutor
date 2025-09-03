# handlers/students/handlers.py
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest
import logging

from handlers.students.config import ADD_STUDENT

from .states import AddStudentStates
from .keyboards import get_invite_keyboard, get_student_detail_keyboard
from .utils import format_student_info, get_students_stats
from handlers.students.keyboards_student import get_cancel_keyboard_add_students, get_students_menu_keyboard, get_students_list_keyboard
from .edit_handlers import router as edit_router
from handlers.students.keyboards import get_student_detail_keyboard
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
            reply_markup=get_students_list_keyboard(students, page=0),
            parse_mode="HTML"
        )
    except TelegramBadRequest:
        await callback_query.message.answer(
            text,
            reply_markup=get_students_list_keyboard(students, page=0),
            parse_mode="HTML"
        )




# Обработчик для кнопки приглашения
# @router.callback_query(F.data.startswith("invite_"))
# async def invite_menu(callback_query: types.CallbackQuery):
#     await callback_query.answer()
    
#     student_id = int(callback_query.data.split("_")[1])
#     student = db.get_student_by_id(student_id)
    
#     if not student:
#         await callback_query.message.edit_text("❌ Ученик не найден!")
#         return
    
#     await callback_query.message.edit_text(
#         f"👤 <b>Приглашение для {student['full_name']}</b>\n\n"
#         "Выберите, кого вы хотите пригласить:",
#         parse_mode="HTML",
#         reply_markup=get_invite_keyboard(student_id)
#     )

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