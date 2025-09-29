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


@router.callback_query(F.data.regexp(r"^edit_student_\d+$"))
async def edit_student_start(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.answer()
    
    try:
        student_id = int(callback_query.data.split("_")[-1])
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
            
    except Exception as e:
        logger.error(f"Ошибка в edit_student_start: {e}")
        await callback_query.message.edit_text("❌ Произошла ошибка при загрузке информации")

# пришлось редактировать метод, старый оставил на всякий случай, но со старым не работает редактирование комментария отчета
# Обработчик начала редактирования ученика
# @router.callback_query(F.data.startswith("edit_student_"))
# async def edit_student_start(callback_query: types.CallbackQuery, state: FSMContext):
#     await callback_query.answer()
    
#     try:
#         student_id = int(callback_query.data.split("_")[2])
#         student = db.get_student_by_id(student_id)
        
#         if not student:
#             await callback_query.message.edit_text("❌ Ученик не найден!")
#             return
        
#         await state.update_data(student_id=student_id)
#         await state.set_state(EditStudentStates.waiting_for_edit_choice)
        
#         await callback_query.message.edit_text(
#             f"✏️ <b>Редактирование ученика</b>\n\n"
#             f"👤 {student['full_name']}\n\n"
#             "Выберите, что хотите изменить:",
#             parse_mode="HTML",
#             reply_markup=get_edit_student_keyboard(student_id)
#         )
            
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


# Функция для обработки смены статуса
async def handle_status_change(student_id: int, new_status: str):
    """Обрабатывает изменение статуса ученика"""
    try:
        # Обновляем статус ученика
        success = db.update_student_status(student_id, new_status)
        
        if not success:
            return False, "❌ Ошибка при обновлении статуса"
        
        # Если статус стал неактивным - полная деактивация
        if new_status.lower() == 'inactive':
            result = db.deactivate_student_completely(student_id)
            
            if 'error' in result:
                return False, f"❌ Ошибка при деактивации: {result['error']}"
            
            message = f"✅ Статус обновлен на 'неактивный'\n"
            
            if result['groups_removed'] > 0:
                message += f"👥 Удален из групп: {result['groups_removed']}\n"
            
            if result['future_lessons_deleted'] > 0:
                message += f"📅 Удалено будущих занятий: {result['future_lessons_deleted']}\n"
            
            if result['planner_actions_deactivated'] > 0:
                message += f"📋 Деактивировано регулярных действий: {result['planner_actions_deactivated']}\n"
            
            # Если ничего не удалялось/деактивировалось
            if not any([result['groups_removed'], result['future_lessons_deleted'], result['planner_actions_deactivated']]):
                message += "ℹ️ Не было активных записей для удаления"
            
            return True, message.strip()
        
        return True, f"✅ Статус обновлен на '{new_status}'"
        
    except Exception as e:
        logger.error(f"Ошибка при обработке смены статуса: {e}")
        return False, "❌ Ошибка при обработке смены статуса"





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

@router.callback_query(F.data.startswith("status_"))
async def process_status_selection(callback_query: types.CallbackQuery, state: FSMContext):
    """Обрабатывает выбор конкретного статуса (active/paused/inactive)"""
    await callback_query.answer()
    
    try:
        # Парсим данные из callback: status_{status}_{student_id}
        parts = callback_query.data.split("_")
        if len(parts) < 3:
            await callback_query.message.edit_text("❌ Ошибка формата данных!")
            return
        
        status = parts[1]  # active, paused, inactive
        student_id = int(parts[2])  # ID ученика
        
        # Если статус НЕ неактивный - обрабатываем как обычно
        if status != "inactive":
            # Обрабатываем смену статуса
            success, message = await handle_status_change(student_id, status)
            
            if success:
                # Определяем эмодзи для статуса
                status_emoji = {
                    'active': '✅',
                    'paused': '⏸️', 
                    'inactive': '❌'
                }.get(status.lower(), '❓')
                
                # Формируем финальное сообщение
                final_message = f"{message}\n\nСтатус: {status_emoji} {status.capitalize()}"
                
                await callback_query.message.edit_text(
                    final_message,
                    parse_mode="HTML",
                    reply_markup=types.InlineKeyboardMarkup(
                        inline_keyboard=[[
                            types.InlineKeyboardButton(
                                text="🔙 Назад к ученику",
                                callback_data=f"student_{student_id}"
                            )
                        ]]
                    )
                )
            else:
                # Если произошла ошибка
                await callback_query.message.edit_text(
                    message,
                    parse_mode="HTML",
                    reply_markup=types.InlineKeyboardMarkup(
                        inline_keyboard=[[
                            types.InlineKeyboardButton(
                                text="🔙 Назад",
                                callback_data=f"edit_status_{student_id}"
                            )
                        ]]
                    )
                )
        
        # Если статус неактивный - показываем подтверждение
        else:
            student = db.get_student_by_id(student_id)
            
            if not student:
                await callback_query.message.edit_text("❌ Ученик не найден!")
                return
            
            # Создаем клавиатуру подтверждения
            keyboard = [
                [
                    types.InlineKeyboardButton(
                        text="✅ Да, сделать неактивным",
                        callback_data=f"confirm_inactive_{student_id}"
                    )
                ],
                [
                    types.InlineKeyboardButton(
                        text="❌ Отмена", 
                        callback_data=f"edit_status_{student_id}"
                    )
                ]
            ]
            markup = types.InlineKeyboardMarkup(inline_keyboard=keyboard)
            
            await callback_query.message.edit_text(
                f"⚠️ <b>Подтверждение</b>\n\n"
                f"Вы точно хотите сделать ученика неактивным?\n\n"
                f"👤 <b>{student['full_name']}</b>\n\n"
                f"📞 {student.get('phone', 'Не указан')}\n\n"
                f"<i>При переводе ученика в неактивные произойдут следующие изменения:\n\n"
                f"📋 Основной список: Ученик будет скрыт из вашего основного списка.\n"
                f"🗓️ Занятия: Все запланированные уроки с ним будут автоматически удалены.\n"
                f"👥 Группы: Ученик будет исключен из всех групп.\n"
                f"🔕 Уведомления: Ученик перестанет получать автоматические напоминания о занятиях.\n"
                f"👤 Доступ: Ваш профиль пропадет из личного кабинета ученика.\n\n"
                f"Не волнуйтесь, все данные сохранятся! Вы сможете найти ученика в разделе «Неактивные ученики» и в любой момент вернуть его к активной работе, возобновив занятия.</i>",
                parse_mode="HTML",
                reply_markup=markup
            )
            
    except Exception as e:
        logger.error(f"Ошибка при обработке выбора статуса: {e}")
        await callback_query.message.edit_text(
            "❌ Ошибка при обработке запроса!",
            reply_markup=types.InlineKeyboardMarkup(
                inline_keyboard=[[
                    types.InlineKeyboardButton(
                        text="🔙 Назад",
                        callback_data="students_list"
                    )
                ]]
            )
        )
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

@router.callback_query(F.data.startswith("confirm_inactive_"))
async def process_confirmed_inactive(callback_query: types.CallbackQuery):
    """Обрабатывает подтвержденное установление статуса 'неактивный'"""
    await callback_query.answer()
    
    try:
        student_id = int(callback_query.data.split("_")[2])
        
        # Используем существующую функцию для смены статуса
        success, message = await handle_status_change(student_id, "inactive")
        
        if success:
            # Формируем финальное сообщение
            final_message = f"{message}\n\nСтатус: ❌ Inactive"
            
            await callback_query.message.edit_text(
                final_message,
                parse_mode="HTML",
                reply_markup=types.InlineKeyboardMarkup(
                    inline_keyboard=[[
                        types.InlineKeyboardButton(
                            text="🔙 Назад к ученику",
                            callback_data=f"student_{student_id}"
                        )
                    ]]
                )
            )
        else:
            # Если произошла ошибка
            await callback_query.message.edit_text(
                message,
                parse_mode="HTML",
                reply_markup=types.InlineKeyboardMarkup(
                    inline_keyboard=[[
                        types.InlineKeyboardButton(
                            text="🔙 Назад",
                            callback_data=f"edit_status_{student_id}"
                        )
                    ]]
                )
            )
            
    except Exception as e:
        logger.error(f"Ошибка при обработке подтверждения неактивности: {e}")
        await callback_query.message.edit_text(
            "❌ Ошибка при обработке запроса!",
            reply_markup=types.InlineKeyboardMarkup(
                inline_keyboard=[[
                    types.InlineKeyboardButton(
                        text="🔙 Назад",
                        callback_data="students_list"
                    )
                ]]
            )
        )
