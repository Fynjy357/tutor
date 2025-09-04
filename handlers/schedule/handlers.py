# handlers/schedule/handlers.py
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest
import logging
from datetime import datetime
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from handlers.schedule.keyboards_schedule import get_schedule_keyboard
from keyboards.main_menu import get_main_menu_keyboard
from database import db
from handlers.schedule.add_lesson.handlers_add_lesson import router as add_new_lesson


router = Router()
router.include_router(add_new_lesson)
logger = logging.getLogger(__name__)


@router.callback_query(F.data == "schedule")
async def show_schedule(callback_query: types.CallbackQuery, state: FSMContext):
    """Показ расписания занятий на неделю"""
    await callback_query.answer()
    
    # Очищаем состояние если было активно
    current_state = await state.get_state()
    if current_state:
        await state.clear()
    
    # Получаем ID репетитора
    tutor_id = db.get_tutor_id_by_telegram_id(callback_query.from_user.id)
    if not tutor_id:
        await callback_query.message.edit_text("❌ Ошибка: не найден ID репетитора.")
        return
    
    # Получаем расписание на ближайшую неделю
    schedule_text = await get_upcoming_lessons(tutor_id)
    
    try:
        await callback_query.message.edit_text(
            schedule_text,
            reply_markup=get_schedule_keyboard(),
            parse_mode="HTML"
        )
    except TelegramBadRequest:
        await callback_query.message.answer(
            schedule_text,
            reply_markup=get_schedule_keyboard(),
            parse_mode="HTML"
        )

async def get_upcoming_lessons(tutor_id: int) -> str:
    """Формирует текст расписания на неделю с группировкой"""
    lessons = db.get_upcoming_lessons(tutor_id)
    
    if not lessons:
        return "📅 <b>Расписание занятий</b>\n\nНа ближайшую неделю занятий нет."
    
    # Группируем занятия по дате+времени и группе
    schedule_dict = {}
    
    for lesson in lessons:
        lesson_date = datetime.strptime(lesson['lesson_date'], '%Y-%m-%d %H:%M:%S')
        time_key = lesson_date.strftime('%Y-%m-%d %H:%M')
        group_id = lesson.get('group_id')
        
        if time_key not in schedule_dict:
            schedule_dict[time_key] = {
                'datetime': lesson_date,
                'individual_lessons': [],
                'group_lessons': {}
            }
        
        # Проверяем тип занятия
        if group_id:
            if group_id not in schedule_dict[time_key]['group_lessons']:
                schedule_dict[time_key]['group_lessons'][group_id] = {
                    'group_name': lesson.get('group_name', f'Группа #{group_id}'),
                    'students': [],
                    'duration': lesson['duration'],
                    'price': lesson['price'],
                    'status': lesson['status']
                }
            schedule_dict[time_key]['group_lessons'][group_id]['students'].append(lesson['student_name'])
        else:
            schedule_dict[time_key]['individual_lessons'].append(lesson)
    
    # Форматируем расписание
    schedule_text = "📅 <b>Расписание занятий на неделю</b>\n\n"
    
    for time_key in sorted(schedule_dict.keys()):
        slot_data = schedule_dict[time_key]
        display_time = slot_data['datetime'].strftime('%d.%m %H:%M')
        
        schedule_text += f"🕐 <b>{display_time}</b>\n"
        
        # Показываем групповые занятия
        for group_id, group_data in slot_data['group_lessons'].items():
            schedule_text += f"👥 <b>Группа: {group_data['group_name']}</b>\n"
            schedule_text += f"⏱ Длительность: {group_data['duration']} мин\n"
            schedule_text += f"💰 Цена: {group_data['price']} руб\n"
            schedule_text += f"📊 Статус: {group_data['status']}\n"
            schedule_text += f"👨‍🎓 Учеников: {len(group_data['students'])}\n"
            
            # Список учеников
            students = ", ".join(group_data['students'])
            schedule_text += f"🎓 Ученики: {students}\n"
        
        # Показываем индивидуальные занятия
        for lesson in slot_data['individual_lessons']:
            schedule_text += f"👤 {lesson['student_name']}\n"
            schedule_text += f"⏱ Длительность: {lesson['duration']} мин\n"
            schedule_text += f"💰 Цена: {lesson['price']} руб\n"
            schedule_text += f"📊 Статус: {lesson['status']}\n"
        
        schedule_text += "───────────────\n"
    
    schedule_text += "\nВыберите действие:"
    
    return schedule_text


@router.callback_query(F.data == "back_from_schedule")
async def back_from_schedule(callback_query: types.CallbackQuery, state: FSMContext):
    """Возврат в главное меню из расписания"""
    await callback_query.answer()
    
    # Получаем данные репетитора для приветствия
    tutor = db.get_tutor_by_telegram_id(callback_query.from_user.id)
    tutor_name = tutor[2] if tutor else "Пользователь"
    
    welcome_text = f"""
<b>Добро пожаловать назад, {tutor_name}!</b>

Рады снова видеть вас в ежедневнике репетитора.

Выберите нужный раздел:
"""
    
    try:
        await callback_query.message.edit_text(
            welcome_text,
            reply_markup=get_main_menu_keyboard(),
            parse_mode="HTML"
        )
    except TelegramBadRequest:
        await callback_query.message.answer(
            welcome_text,
            reply_markup=get_main_menu_keyboard(),
            parse_mode="HTML"
        )