import logging
from aiogram import Dispatcher, types, F

logger = logging.getLogger(__name__)

async def handle_confirmation_callback(callback_query: types.CallbackQuery, notification_manager, bot):
    """Обработчик инлайн-кнопок подтверждения"""
    data = callback_query.data
    user_id = callback_query.from_user.id

    # ДОБАВЬТЕ ЭТО ДЛЯ ДЕБАГА
    logger.info(f"📨 Получен callback: {data} от пользователя {user_id}")
    
    try:
        if data.startswith('notify_confirm_'):
            # Формат: notify_confirm_{lesson_id}_{confirmation_id}
            parts = data.split('_')
            if len(parts) >= 4:
                confirmation_id = parts[3]  # Берем последнюю часть
                lesson_id = parts[2]  # Третья часть - lesson_id
                
                # Обновляем статус в базе
                notification_manager.mark_confirmation(confirmation_id, True)
                
                # Отправляем уведомление репетитору о подтверждении
                try:
                    teacher_chat_id = notification_manager.get_teacher_chat_id_by_confirmation(confirmation_id)
                    
                    if teacher_chat_id:
                        # Получаем информацию о занятии для более детального уведомления
                        lesson_info = notification_manager.get_lesson_info(lesson_id)
                        if lesson_info:
                            student_name = lesson_info.get('student_name', 'неизвестный ученик')
                            lesson_time = lesson_info.get('lesson_date', 'неизвестное время')
                            
                            await bot.send_message(
                                chat_id=teacher_chat_id,
                                text=f"✅ Ученик подтвердил занятие\n"
                                     f"👤 Ученик: {student_name}\n"
                                     f"📅 Время: {lesson_time}\n"
                                     f"ID занятия: {lesson_id}"
                            )
                        else:
                            await bot.send_message(
                                chat_id=teacher_chat_id,
                                text=f"✅ Ученик подтвердил занятие\n"
                                     f"ID занятия: {lesson_id}"
                            )
                        logger.info(f"✅ Уведомление о подтверждении отправлено репетитору {teacher_chat_id}")
                    else:
                        logger.warning(f"⚠️ Не найден chat_id репетитора для подтверждения {confirmation_id}")
                        
                except Exception as e:
                    logger.error(f"❌ Ошибка при отправке уведомления репетитору: {e}")
                
                await callback_query.answer("✅ Занятие подтверждено!")
                await callback_query.message.edit_text(
                    f"✅ Вы подтвердили участие в занятии\n"
                    f"Ждем вас на уроке!",
                    reply_markup=None
                )
            
        elif data.startswith('notify_cancel_'):
            # Формат: notify_cancel_{lesson_id}_{confirmation_id}
            parts = data.split('_')
            if len(parts) >= 4:
                confirmation_id = parts[3]  # Берем последнюю часть
                lesson_id = parts[2]  # Третья часть - lesson_id
                
                # Обновляем статус в базе
                notification_manager.mark_confirmation(confirmation_id, False)
                
                # Отправляем уведомление репетитору об отмене
                try:
                    teacher_chat_id = notification_manager.get_teacher_chat_id_by_confirmation(confirmation_id)
                    
                    if teacher_chat_id:
                        # Получаем информацию о занятии
                        lesson_info = notification_manager.get_lesson_info(lesson_id)
                        if lesson_info:
                            student_name = lesson_info.get('student_name', 'неизвестный ученик')
                            lesson_time = lesson_info.get('lesson_date', 'неизвестное время')
                            
                            await bot.send_message(
                                chat_id=teacher_chat_id,
                                text=f"❌ Ученик отменил занятие\n"
                                     f"👤 Ученик: {student_name}\n"
                                     f"📅 Время: {lesson_time}\n"
                                     f"ID занятия: {lesson_id}"
                            )
                        else:
                            await bot.send_message(
                                chat_id=teacher_chat_id,
                                text=f"❌ Ученик отменил занятие\n"
                                     f"ID занятия: {lesson_id}"
                            )
                        logger.info(f"✅ Уведомление об отмене отправлено репетитору {teacher_chat_id}")
                    else:
                        logger.warning(f"⚠️ Не найден chat_id репетитора для подтверждения {confirmation_id}")
                        
                except Exception as e:
                    logger.error(f"❌ Ошибка при отправке уведомления репетитору: {e}")
                
                await callback_query.answer("❌ Занятие отменено")
                await callback_query.message.edit_text(
                    f"❌ Вы отменили участие в занятии\n"
                    f"Свяжитесь с преподавателем для переноса",
                    reply_markup=None
                )
            
        elif data.startswith('notify_reschedule_'):
            # Формат: notify_reschedule_{lesson_id}_{confirmation_id}
            parts = data.split('_')
            if len(parts) >= 4:
                confirmation_id = parts[3]
                lesson_id = parts[2]  # Третья часть - lesson_id
                
                # Обновляем статус в базе на "перенос"
                notification_manager.mark_confirmation(confirmation_id, 2)
                
                # Отправляем уведомление репетитору
                try:
                    teacher_chat_id = notification_manager.get_teacher_chat_id_by_confirmation(confirmation_id)
                    
                    if teacher_chat_id:
                        # Получаем информацию о занятии
                        lesson_info = notification_manager.get_lesson_info(lesson_id)
                        if lesson_info:
                            student_name = lesson_info.get('student_name', 'неизвестный ученик')
                            lesson_time = lesson_info.get('lesson_date', 'неизвестное время')
                            
                            await bot.send_message(
                                chat_id=teacher_chat_id,
                                text=f"🔄 Ученик запросил перенос занятия\n"
                                     f"👤 Ученик: {student_name}\n"
                                     f"📅 Текущее время: {lesson_time}\n"
                                     f"ID занятия: {lesson_id}\n\n"
                                     f"Свяжитесь с учеником для согласования нового времени"
                            )
                        else:
                            await bot.send_message(
                                chat_id=teacher_chat_id,
                                text=f"🔄 Ученик запросил перенос занятия\n"
                                     f"ID занятия: {lesson_id}\n\n"
                                     f"Свяжитесь с учеником для согласования нового времени"
                            )
                        logger.info(f"✅ Уведомление о переносе отправлено репетитору {teacher_chat_id}")
                    else:
                        logger.warning(f"⚠️ Не найден chat_id репетитора для подтверждения {confirmation_id}")
                        
                except Exception as e:
                    logger.error(f"❌ Ошибка при отправке уведомления репетитору: {e}")
                
                await callback_query.answer("🔄 Запрос на перенос отправлен")
                await callback_query.message.edit_text(
                    f"🔄 Запрос на перенос занятия отправлен преподавателю\n"
                    f"С вами свяжутся для согласования нового времени",
                    reply_markup=None
                )
            
    except Exception as e:
        logger.error(f"❌ Ошибка обработки callback: {e}")
        await callback_query.answer("⚠️ Произошла ошибка")

def register_confirmation_handlers(dp: Dispatcher, notification_manager, bot):
    """Регистрируем обработчики инлайн-кнопок"""
    
    # Единый обработчик для всех типов подтверждений
    async def confirmation_handler(callback_query: types.CallbackQuery):
        await handle_confirmation_callback(callback_query, notification_manager, bot)
    
    # Регистрируем отдельно для каждого типа callback
    dp.callback_query.register(
        confirmation_handler,
        F.data.startswith("notify_confirm_")
    )
    
    dp.callback_query.register(
        confirmation_handler,
        F.data.startswith("notify_cancel_")
    )
    
    dp.callback_query.register(
        confirmation_handler,
        F.data.startswith("notify_reschedule_")
    )
    
    logger.info("✅ Обработчики инлайн-кнопок подтверждения зарегистрированы")