# from aiogram import Router, types, F
# from aiogram.fsm.context import FSMContext
# from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
# from database import db
# from handlers.schedule.states import AddLessonStates
# import logging

# router = Router()
# logger = logging.getLogger(__name__)

# # Обработчик выбора группового занятия
# # @router.callback_query(F.data == "lesson_type_group", AddLessonStates.choosing_lesson_type)
# # async def choose_group_for_lesson(callback_query: types.CallbackQuery, state: FSMContext):
# #     """Выбор группы для группового занятия"""
# #     await callback_query.answer()
    
# #     # Получаем ID репетитора
# #     tutor_id = db.get_tutor_id_by_telegram_id(callback_query.from_user.id)
    
# #     if not tutor_id:
# #         await callback_query.message.answer("❌ Репетитор не найден")
# #         return
    
# #     # Получаем список групп преподавателя
# #     groups = db.get_groups_by_tutor(tutor_id)
    
# #     # Логируем для отладки
# #     logger.info(f"Tutor ID: {tutor_id}, Found groups: {groups}")
    
# #     if not groups:
# #         # Если нет групп, предлагаем создать новую
# #         keyboard = InlineKeyboardMarkup(inline_keyboard=[
# #             [InlineKeyboardButton(text="➕ Создать новую группу", callback_data="create_group_for_lesson")],
# #             [InlineKeyboardButton(text="🔙 Назад", callback_data="add_lesson")]
# #         ])
        
# #         await callback_query.message.edit_text(
# #             "❌ <b>У вас нет групп</b>\n\nСначала создайте группу, чтобы добавить групповое занятие",
# #             reply_markup=keyboard,
# #             parse_mode="HTML"
# #         )
# #         return
    
# #     # Создаем клавиатуру с группами
# #     buttons = []
# #     for group in groups:
# #         buttons.append([InlineKeyboardButton(
# #             text=f"👥 {group['name']}",
# #             callback_data=f"select_group_{group['id']}"
# #         )])
    
# #     # Добавляем кнопки назад
# #     buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="add_lesson")])
    
# #     keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    
# #     await callback_query.message.edit_text(
# #         "👥 <b>Выберите группу для занятия:</b>",
# #         reply_markup=keyboard,
# #         parse_mode="HTML"
# #     )
# #     await state.set_state(AddLessonStates.choosing_group)

# # Обработчик выбора конкретной группы
# @router.callback_query(F.data.startswith("select_group_"), AddLessonStates.choosing_group)
# async def group_selected_for_lesson(callback_query: types.CallbackQuery, state: FSMContext):
#     """Группа выбрана для занятия"""
#     await callback_query.answer()
    
#     group_id = int(callback_query.data.split("_")[2])
    
#     # Получаем информацию о группе
#     group = db.get_group_by_id(group_id)
    
#     if not group:
#         await callback_query.message.answer("❌ Группа не найдена")
#         return
    
#     # Сохраняем выбранную группу в состоянии
#     await state.update_data(
#         group_id=group_id,
#         group_name=group['name'],
#         lesson_type='group'
#     )
    
#     # Переходим к выбору частоты занятия
#     keyboard = InlineKeyboardMarkup(inline_keyboard=[
#         [InlineKeyboardButton(text="📅 Единоразовое", callback_data="frequency_single")],
#         [InlineKeyboardButton(text="🔄 Регулярное", callback_data="frequency_regular")],
#         [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_group_selection")]
#     ])
    
#     await callback_query.message.edit_text(
#         f"✅ <b>Группа выбрана:</b> {group['name']}\n\n"
#         "📅 <b>Регулярное или единоразовое занятие добавить?</b>",
#         reply_markup=keyboard,
#         parse_mode="HTML"
#     )
#     await state.set_state(AddLessonStates.choosing_frequency)

# # Обработчик создания новой группы
# @router.callback_query(F.data == "create_group_for_lesson")
# async def create_group_from_lesson(callback_query: types.CallbackQuery, state: FSMContext):
#     """Создание группы из процесса добавления занятия"""
#     await callback_query.answer()
    
#     # Сохраняем, что мы в процессе добавления занятия
#     await state.update_data(creating_group_for_lesson=True)
    
#     # Переходим к созданию группы
#     from handlers.groups.handlers import add_group_start
#     await add_group_start(callback_query.message, state)