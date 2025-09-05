import logging
from aiogram import Dispatcher, types, F

logger = logging.getLogger(__name__)

async def handle_confirmation_callback(callback_query: types.CallbackQuery, notification_manager):
    """Обработчик инлайн-кнопок подтверждения"""
    data = callback_query.data
    user_id = callback_query.from_user.id

    # ДОБАВЬТЕ ЭТО ДЛЯ ДЕБАГА
    logger.info(f"📨 Получен callback: {data} от пользователя {user_id}")
    
    try:
        if data.startswith('confirm_'):
            # Формат: confirm_{lesson_id}_{confirmation_id}
            parts = data.split('_')
            if len(parts) >= 3:
                confirmation_id = parts[-1]  # Берем последнюю часть
                # Обновляем статус в базе
                notification_manager.mark_confirmation(confirmation_id, True)
                await callback_query.answer("✅ Занятие подтверждено!")
                await callback_query.message.edit_text(
                    f"✅ Вы подтвердили участие в занятии\n"
                    f"Ждем вас на уроке!",
                    reply_markup=None
                )
            
        elif data.startswith('cancel_'):
            # Формат: cancel_{lesson_id}_{confirmation_id}
            parts = data.split('_')
            if len(parts) >= 3:
                confirmation_id = parts[-1]  # Берем последнюю часть
                # Обновляем статус в базе
                notification_manager.mark_confirmation(confirmation_id, False)
                await callback_query.answer("❌ Занятие отменено")
                await callback_query.message.edit_text(
                    f"❌ Вы отменили участие в занятии\n"
                    f"Свяжитесь с преподавателем для переноса",
                    reply_markup=None
                )
            
        elif data.startswith('reschedule_'):
            # Формат: reschedule_{lesson_id}_{confirmation_id}
            parts = data.split('_')
            if len(parts) >= 3:
                confirmation_id = parts[-1]  # Берем последнюю часть
                logger.info(f"🔍 confirmation_id: {confirmation_id}")
                await callback_query.answer("🔄 Запрос на перенос отправлен")
                await callback_query.message.edit_text(
                    f"🔄 Запрос на перенос занятия отправлен\n"
                    f"С вами свяжется преподаватель",
                    reply_markup=None
                )
            
    except Exception as e:
        logger.error(f"❌ Ошибка обработки callback: {e}")
        await callback_query.answer("⚠️ Произошла ошибка")

def register_confirmation_handlers(dp: Dispatcher, notification_manager):
    """Регистрируем обработчики инлайн-кнопок"""
    
    # Единый обработчик для всех типов подтверждений
    async def confirmation_handler(callback_query: types.CallbackQuery):
        await handle_confirmation_callback(callback_query, notification_manager)
    
    # Регистрируем отдельно для каждого типа callback
    dp.callback_query.register(
        confirmation_handler,
        F.data.startswith("confirm_")
    )
    
    dp.callback_query.register(
        confirmation_handler,
        F.data.startswith("cancel_")
    )
    
    dp.callback_query.register(
        confirmation_handler,
        F.data.startswith("reschedule_")
    )
    
    logger.info("✅ Обработчики инлайн-кнопок подтверждения зарегистрированы")