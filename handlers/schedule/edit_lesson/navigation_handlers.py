# navigation_handlers.py
from aiogram import F, Router, types
from aiogram.fsm.context import FSMContext
from database import db
from keyboards.main_menu import get_main_menu_keyboard

router = Router()

@router.callback_query(F.data == "main_menu")
async def back_to_main_menu(callback_query: types.CallbackQuery, state: FSMContext):
    """Обработчик возврата в главное меню"""
    try:
        await callback_query.answer()
        await state.clear()
        
        await callback_query.message.edit_text(
            "🏠 <b>Главное меню</b>\n\n"
            "Выберите нужный раздел:",
            reply_markup=get_main_menu_keyboard(),
            parse_mode="HTML"
        )
    except Exception as e:
        print(f"Ошибка в back_to_main_menu: {e}")
        await callback_query.answer("⚠️ Произошла ошибка", show_alert=True)

@router.callback_query(F.data == "edit_lesson")
async def back_to_edit_lesson(callback_query: types.CallbackQuery, state: FSMContext):
    """Обработчик возврата к редактированию занятий"""
    try:
        await callback_query.answer()
        
        # Импорты внутри функции чтобы избежать циклических импортов
        from .edit_lesson import EditLessonStates
        from .keyboards import get_date_selection_keyboard, group_lessons_by_date
        
        await state.set_state(EditLessonStates.choosing_date)
        tutor_id = db.get_tutor_id_by_telegram_id(callback_query.from_user.id)
        lessons = db.get_upcoming_lessons(tutor_id)
        lessons_by_date = group_lessons_by_date(lessons)
        keyboard = get_date_selection_keyboard(lessons_by_date)
        
        await callback_query.message.edit_text(
            "📅 Выберите дату для редактирования занятий:",
            reply_markup=keyboard
        )
    except Exception as e:
        print(f"Ошибка в back_to_edit_lesson: {e}")
        await callback_query.answer("⚠️ Произошла ошибка при загрузке занятий", show_alert=True)

@router.callback_query(F.data.startswith("edit_date_"))
async def back_to_date_lessons(callback_query: types.CallbackQuery, state: FSMContext):
    """Обработчик возврата к занятиям на конкретную дату"""
    try:
        await callback_query.answer()
        selected_date = callback_query.data.split("_")[2]
        
        # Импорт внутри функции
        from .utils import show_lessons_for_editing
        await show_lessons_for_editing(callback_query, state, selected_date)
    except Exception as e:
        print(f"Ошибка в back_to_date_lessons: {e}")
        await callback_query.answer("⚠️ Произошла ошибка при загрузке занятий", show_alert=True)

# Дополнительные обработчики для других кнопок "Назад"
@router.callback_query(F.data == "back_to_schedule")
async def back_to_schedule(callback_query: types.CallbackQuery, state: FSMContext):
    """Обработчик возврата к расписанию"""
    try:
        await callback_query.answer()
        await state.clear()
        
        # Здесь должен быть код для показа расписания
        await callback_query.message.edit_text(
            "📅 <b>Расписание занятий</b>\n\n"
            "Выберите действие:",
            parse_mode="HTML"
        )
    except Exception as e:
        print(f"Ошибка в back_to_schedule: {e}")
        await callback_query.answer("⚠️ Произошла ошибка", show_alert=True)

@router.callback_query(F.data == "back_to_students")
async def back_to_students(callback_query: types.CallbackQuery, state: FSMContext):
    """Обработчик возврата к управлению учениками"""
    try:
        await callback_query.answer()
        await state.clear()
        
        # Здесь должен быть код для показа управления учениками
        await callback_query.message.edit_text(
            "👥 <b>Учет учеников</b>\n\n"
            "Выберите действие:",
            parse_mode="HTML"
        )
    except Exception as e:
        print(f"Ошибка в back_to_students: {e}")
        await callback_query.answer("⚠️ Произошла ошибка", show_alert=True)