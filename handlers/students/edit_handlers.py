# handlers/students/edit_handlers.py
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
import logging

from handlers.students.keyboards import get_student_detail_keyboard

from .states import EditStudentStates
from keyboards.students_edit import get_edit_student_keyboard, get_status_keyboard, get_cancel_edit_keyboard
from .utils import format_student_info
from database import db

router = Router()
logger = logging.getLogger(__name__)

# Обработчик начала редактирования ученика
@router.callback_query(F.data.startswith("edit_student_"))
async def edit_student_start(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.answer()
    
    try:
        student_id = int(callback_query.data.split("_")[2])
        student = db.get_student_by_id(student_id)
        
        if not student:
            await callback_query.message.edit_text("❌ Ученик не найден!")
            return
        
        await state.update_data(student_id=student_id)
        await state.set_state(EditStudentStates.waiting_for_edit_choice)
        
        await callback_query.message.edit_text(
            f"✏️ <b>Редактирование ученика</b>\n\n"
            f"👤 {student['full_name']}\n\n"
            "Выберите, что хотите изменить:",
            parse_mode="HTML",
            reply_markup=get_edit_student_keyboard(student_id)
        )
            
    except (ValueError, IndexError) as e:
        logger.error(f"Ошибка парсинга callback data: {e}")
        await callback_query.message.edit_text("❌ Ошибка при обработке запроса!")
    except Exception as e:
        logger.error(f"Ошибка в edit_student_start: {e}")
        await callback_query.message.edit_text("❌ Произошла ошибка при загрузке информации")

# Обработчик выбора редактирования ФИО
@router.callback_query(F.data.startswith("edit_name_"))
async def edit_name_start(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.answer()
    
    try:
        student_id = int(callback_query.data.split("_")[2])
        student = db.get_student_by_id(student_id)
        
        if not student:
            await callback_query.message.edit_text("❌ Ученик не найден!")
            return
        
        await state.update_data(student_id=student_id)
        await state.set_state(EditStudentStates.waiting_for_name)
        await callback_query.message.edit_text(
            f"✏️ <b>Изменение ФИО</b>\n\n"
            f"Текущее ФИО: {student['full_name']}\n\n"
            "Введите новое ФИО ученика:",
            parse_mode="HTML",
            reply_markup=get_cancel_edit_keyboard(student_id)
        )
            
    except (ValueError, IndexError) as e:
        logger.error(f"Ошибка парсинга callback data: {e}")
        await callback_query.message.edit_text("❌ Ошибка при обработке запроса!")

# Обработчик ввода нового ФИО
@router.message(EditStudentStates.waiting_for_name)
async def process_edit_name(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    logger.info(f"Текущее состояние: {current_state}")
    if not message.text or len(message.text.strip()) < 2:
        await message.answer("Пожалуйста, введите корректное ФИО ученика (минимум 2 символа):")
        return
    
    data = await state.get_data()
    student_id = data['student_id']
    
    # Обновляем ФИО в базе данных
    success = db.update_student_field(student_id, 'full_name', message.text.strip())
    
    if success:
        await message.answer(
            f"✅ <b>ФИО успешно изменено!</b>\n\n"
            f"Новое ФИО: {message.text.strip()}",
            parse_mode="HTML"
        )
        
        # Показываем обновленную информацию об ученике
        student = db.get_student_by_id(student_id)
        text = format_student_info(student)
        
        await message.answer(
            text,
            reply_markup=get_student_detail_keyboard(student_id),
            parse_mode="HTML"
        )
    else:
        await message.answer(
            "❌ <b>Ошибка при изменении ФИО!</b>\n\n"
            "Пожалуйста, попробуйте позже.",
            parse_mode="HTML"
        )
    
    await state.clear()

# Обработчик выбора редактирования телефона ученика
@router.callback_query(F.data.startswith("edit_phone_"))
async def edit_phone_start(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.answer()
    
    try:
        student_id = int(callback_query.data.split("_")[2])
        student = db.get_student_by_id(student_id)
        
        if not student:
            await callback_query.message.edit_text("❌ Ученик не найден!")
            return
        
        await state.update_data(student_id=student_id)
        await state.set_state(EditStudentStates.waiting_for_phone)
        
        current_phone = student['phone'] if student['phone'] != '-' else 'не указан'
        
        await callback_query.message.edit_text(
            f"📞 <b>Изменение телефона ученика</b>\n\n"
            f"Текущий телефон: {current_phone}\n\n"
            "Введите новый телефон ученика (или '-' чтобы удалить):",
            parse_mode="HTML",
            reply_markup=get_cancel_edit_keyboard(student_id)
        )
            
    except (ValueError, IndexError) as e:
        logger.error(f"Ошибка парсинга callback data: {e}")
        await callback_query.message.edit_text("❌ Ошибка при обработке запроса!")

# Обработчик ввода нового телефона ученика
@router.message(EditStudentStates.waiting_for_phone)
async def process_edit_phone(message: types.Message, state: FSMContext):
    phone = message.text.strip() if message.text else "-"
    
    data = await state.get_data()
    student_id = data['student_id']
    
    # Обновляем телефон в базе данных
    success = db.update_student_field(student_id, 'phone', phone)
    
    if success:
        phone_display = phone if phone != '-' else 'не указан'
        await message.answer(
            f"✅ <b>Телефон ученика успешно изменен!</b>\n\n"
            f"Новый телефон: {phone_display}",
            parse_mode="HTML"
        )
        
        # Показываем обновленную информацию об ученике
        student = db.get_student_by_id(student_id)
        text = format_student_info(student)
        
        await message.answer(
            text,
            reply_markup=get_student_detail_keyboard(student_id),
            parse_mode="HTML"
        )
    else:
        await message.answer(
            "❌ <b>Ошибка при изменении телефона!</b>\n\n"
            "Пожалуйста, попробуйте позже.",
            parse_mode="HTML"
        )
    
    await state.clear()

# Обработчик выбора редактирования телефона родителя
@router.callback_query(F.data.startswith("edit_parent_phone_"))
async def edit_parent_phone_start(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.answer()
    
    try:
        student_id = int(callback_query.data.split("_")[3])
        student = db.get_student_by_id(student_id)
        
        if not student:
            await callback_query.message.edit_text("❌ Ученик не найден!")
            return
        
        await state.update_data(student_id=student_id)
        await state.set_state(EditStudentStates.waiting_for_parent_phone)
        
        current_phone = student['parent_phone'] if student['parent_phone'] != '-' else 'не указан'
        
        await callback_query.message.edit_text(
            f"👨‍👩‍👧‍👦 <b>Изменение телефона родителя</b>\n\n"
            f"Текущий телефон родителя: {current_phone}\n\n"
            "Введите новый телефон родителя (или '-' чтобы удалить):",
            parse_mode="HTML",
            reply_markup=get_cancel_edit_keyboard(student_id)
        )
            
    except (ValueError, IndexError) as e:
        logger.error(f"Ошибка парсинга callback data: {e}")
        await callback_query.message.edit_text("❌ Ошибка при обработке запроса!")

# Обработчик ввода нового телефона родителя
@router.message(EditStudentStates.waiting_for_parent_phone)
async def process_edit_parent_phone(message: types.Message, state: FSMContext):
    parent_phone = message.text.strip() if message.text else "-"
    
    data = await state.get_data()
    student_id = data['student_id']
    
    # Обновляем телефон родителя в базе данных
    success = db.update_student_field(student_id, 'parent_phone', parent_phone)
    
    if success:
        phone_display = parent_phone if parent_phone != '-' else 'не указан'
        await message.answer(
            f"✅ <b>Телефон родителя успешно изменен!</b>\n\n"
            f"Новый телефон родителя: {phone_display}",
            parse_mode="HTML"
        )
        
        # Показываем обновленную информацию об ученике
        student = db.get_student_by_id(student_id)
        text = format_student_info(student)
        
        await message.answer(
            text,
            reply_markup=get_student_detail_keyboard(student_id),
            parse_mode="HTML"
        )
    else:
        await message.answer(
            "❌ <b>Ошибка при изменении телефона родителя!</b>\n\n"
            "Пожалуйста, попробуйте позже.",
            parse_mode="HTML"
        )
    
    await state.clear()

# Обработчик выбора редактирования статуса
@router.callback_query(F.data.startswith("edit_status_"))
async def edit_status_start(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.answer()
    
    try:
        student_id = int(callback_query.data.split("_")[2])
        student = db.get_student_by_id(student_id)
        
        if not student:
            await callback_query.message.edit_text("❌ Ученик не найден!")
            return
        
        await state.update_data(student_id=student_id)
        
        status_emoji = {
            'active': '✅',
            'paused': '⏸️', 
            'inactive': '❌'
        }.get(student['status'].lower(), '❓')
        
        await callback_query.message.edit_text(
            f"📊 <b>Изменение статуса</b>\n\n"
            f"Текущий статус: {status_emoji} {student['status']}\n\n"
            "Выберите новый статус:",
            parse_mode="HTML",
            reply_markup=get_status_keyboard(student_id)
        )
            
    except (ValueError, IndexError) as e:
        logger.error(f"Ошибка парсинга callback data: {e}")
        await callback_query.message.edit_text("❌ Ошибка при обработке запроса!")

# Обработчики установки статуса
@router.callback_query(F.data.startswith("set_status_"))
async def set_status(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.answer()
    
    try:
        parts = callback_query.data.split("_")
        status = parts[2]  # active, paused, inactive
        student_id = int(parts[3])
        
        status_map = {
            'active': 'active',
            'paused': 'paused',
            'inactive': 'inactive'
        }
        
        if status not in status_map:
            await callback_query.message.edit_text("❌ Неверный статус!")
            return
        
        # Обновляем статус в базе данных
        success = db.update_student_field(student_id, 'status', status_map[status])
        
        if success:
            status_emoji = {
                'active': '✅',
                'paused': '⏸️',
                'inactive': '❌'
            }[status]
            
            await callback_query.message.edit_text(
                f"✅ <b>Статус успешно изменен!</b>\n\n"
                f"Новый статус: {status_emoji} {status_map[status]}",
                parse_mode="HTML"
            )
            
            # Показываем обновленную информацию об ученике
            student = db.get_student_by_id(student_id)
            text = format_student_info(student)
            
            await callback_query.message.answer(
                text,
                reply_markup=get_student_detail_keyboard(student_id),
                parse_mode="HTML"
            )
        else:
            await callback_query.message.edit_text(
                "❌ <b>Ошибка при изменении статуса!</b>\n\n"
                "Пожалуйста, попробуйте позже.",
                parse_mode="HTML"
            )
            
    except (ValueError, IndexError) as e:
        logger.error(f"Ошибка парсинга callback data: {e}")
        await callback_query.message.edit_text("❌ Ошибка при обработке запроса!")
    except Exception as e:
        logger.error(f"Ошибка в set_status: {e}")
        await callback_query.message.edit_text("❌ Произошла ошибка при изменении статуса")
    
    await state.clear()