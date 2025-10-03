from datetime import datetime
from aiogram import types, Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.exceptions import TelegramBadRequest
from handlers.start.welcome import show_main_menu
from payment.config import TARIF
from .models import PaymentManager
from .yookassa_integration import YooKassaManager
import logging
from handlers.schedule.planner.timer.planner_manager import planner_manager

logger = logging.getLogger(__name__)
router = Router()
yookassa = YooKassaManager()

async def safe_edit_message(message, text, reply_markup=None, parse_mode=None):
    """
    Безопасное редактирование сообщения с обработкой ошибки 'message not modified'
    """
    try:
        await message.edit_text(
            text=text,
            reply_markup=reply_markup,
            parse_mode=parse_mode
        )
        return True
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            # Сообщение не изменилось - это нормально
            return False
        else:
            logger.error(f"Error editing message: {e}")
            return False
    except Exception as e:
        logger.error(f"Error editing message: {e}")
        return False

async def get_settings_message(user_id: int) -> tuple:
    """Получает текст и клавиатуру для настроек"""
    # Получаем актуальную информацию о подписке
    payment_info = await PaymentManager.get_payment_info(user_id)
    logger.info(f"Payment info for user {user_id}: {payment_info}")
    
    # Дополнительная проверка: если есть valid_until, но is_active = False
    if payment_info and payment_info.get('valid_until') and not payment_info.get('is_active', False):
        # Проверяем, не истекла ли подписка
        try:
            valid_until = payment_info['valid_until']
            if isinstance(valid_until, str):
                valid_until = datetime.strptime(valid_until, '%Y-%m-%d %H:%M:%S')
            
            if valid_until > datetime.now():
                # Подписка активна, но помечена как неактивная - исправляем
                message_text = f"💰 **Статус подписки**\n\n" \
                              f"✅ Активная подписка\n" \
                              f"📅 Действует до: {valid_until.strftime('%d.%m.%Y %H:%M')}\n" \
                              f"💳 Тариф: {payment_info.get('tariff', 'Не указан')}\n\n" \
                              f"Вы можете продлить подписку:"
            else:
                message_text = "❌ **Сервис не оплачен**\n\n" \
                              "Для доступа к полному функционалу необходимо оплатить подписку."
        except:
            message_text = "❌ **Сервис не оплачен**\n\n" \
                          "Для доступа к полному функционалу необходимо оплатить подписку."
    
    elif payment_info and payment_info.get('is_active', False):
        # Форматируем дату для красивого отображения
        valid_until = payment_info['valid_until']
        if isinstance(valid_until, str):
            # Если дата в строковом формате, преобразуем
            try:
                valid_until = datetime.strptime(valid_until, '%Y-%m-%d %H:%M:%S')
            except:
                pass
        
        if isinstance(valid_until, datetime):
            formatted_date = valid_until.strftime('%d.%m.%Y %H:%M')
        else:
            formatted_date = str(valid_until)
        
        message_text = f"**Статус подписки**\n\n" \
                      f"✅ Активная подписка\n" \
                      f"📅 Действует до: {formatted_date}\n" \
                      f"💳 Тариф: {payment_info.get('tariff', 'Не указан')}\n\n" \
                      f"Вы можете продлить подписку:"
    else:
        message_text = "❌ **Сервис не оплачен**\n\n" \
                      "Для доступа к полному функционалу необходимо оплатить подписку."
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Оплата сервиса", callback_data="payment_menu")],
        # [InlineKeyboardButton(text="🔄 Обновить статус", callback_data="settings")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_main_menu")]
    ])
    
    return message_text, keyboard

@router.callback_query(F.data == "settings")
async def settings_handler(callback: types.CallbackQuery, state: FSMContext):
    """Обработчик кнопки настроек с актуальной информацией"""
    try:
        user_id = callback.from_user.id
        logger.info(f"Settings handler called for user {user_id}")
        
        # УБРАЛ ОТЛАДОЧНЫЙ ВЫЗОВ - он вызывал ошибку
        # await PaymentManager.debug_check_payments(user_id)
        
        # Получаем актуальное сообщение и клавиатуру
        message_text, keyboard = await get_settings_message(user_id)
        
        # Всегда обновляем сообщение, чтобы показать актуальный статус
        success = await safe_edit_message(
            callback.message,
            text=message_text,
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
        
        if success:
            await callback.answer("🔄 Проверка подписки")
        else:
            await callback.answer("✅ Статус актуален")
        
    except Exception as e:
        logger.error(f"Error in settings_handler: {e}", exc_info=True)
        await callback.answer("❌ Ошибка загрузки настроек", show_alert=True)

@router.callback_query(F.data == "payment_menu")
async def payment_menu_handler(callback: types.CallbackQuery, state: FSMContext):
    """Меню выбора тарифа оплаты"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📅 1 месяц - 120 руб", callback_data="payment_1month")],
        [InlineKeyboardButton(text="📅 6 месяцев - 650 руб", callback_data="payment_6months")],
        [InlineKeyboardButton(text="📅 1 год - 1000 руб", callback_data="payment_1year")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_settings")]
    ])
     
    text = TARIF
    
    await safe_edit_message(
        callback.message,
        text=text,
        reply_markup=keyboard,
        parse_mode='Markdown'
    )
    await callback.answer()

@router.callback_query(F.data.startswith("payment_"))
async def process_payment_handler(callback: types.CallbackQuery, state: FSMContext):
    """Обработчик выбора тарифа"""
    try:
        tariff_type = callback.data
        
        tariffs = {
            "payment_1month": {"amount": 120, "days": 30, "name": "1 месяц"},
            "payment_6months": {"amount": 650, "days": 180, "name": "6 месяцев"},
            "payment_1year": {"amount": 1000, "days": 365, "name": "1 год"}
        }
        
        if tariff_type in tariffs:
            tariff = tariffs[tariff_type]
            
            # Сохраняем выбор в состоянии
            await state.update_data({
                "selected_tariff": tariff_type,
                "amount": tariff["amount"],
                "days": tariff["days"],
                "tariff_name": tariff["name"]
            })
            
            # Создаем платеж в ЮKassa
            payment_url = await yookassa.create_payment(
                amount=tariff["amount"],
                user_id=callback.from_user.id,
                tariff_name=tariff["name"],
                tariff_days=tariff["days"]
            )
            
            if payment_url:
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="💳 Перейти к оплате", url=payment_url)],
                    [InlineKeyboardButton(text="✅ Я оплатил", callback_data="check_payment")],
                    [InlineKeyboardButton(text="◀️ Назад к тарифам", callback_data="payment_menu")]
                ])
                
                text = f"💳 **Оплата тарифа: {tariff['name']}**\n\n" \
                      f"Сумма: {tariff['amount']} руб.\n" \
                      f"Срок: {tariff['days']} дней\n\n" \
                      f"Нажмите кнопку ниже для перехода к оплате:"
                
                await safe_edit_message(
                    callback.message,
                    text=text,
                    reply_markup=keyboard,
                    parse_mode='Markdown'
                )
            else:
                await safe_edit_message(
                    callback.message,
                    text="❌ Ошибка создания платежа. Попробуйте позже.",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="◀️ Назад", callback_data="payment_menu")]
                    ])
                )
        
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error in process_payment_handler: {e}", exc_info=True)
        await callback.answer("❌ Ошибка создания платежа", show_alert=True)

@router.callback_query(F.data == "check_payment")
async def check_payment_handler(callback: types.CallbackQuery, state: FSMContext):
    """Проверка оплаты через API ЮKassa с продлением подписки"""
    try:
        user_id = callback.from_user.id
        logger.info(f"Checking payment for user {user_id}")
        
        # Получаем последний платеж пользователя
        payment_info = await yookassa.get_last_payment(user_id)
        logger.info(f"Payment info from YooKassa: {payment_info}")
        
        if not payment_info:
            await callback.answer("❌ Платеж не найден", show_alert=True)
            return
        
        status = payment_info.get('status')
        
        if status == 'succeeded':
            # Получаем данные о выбранном тарифе из состояния
            data = await state.get_data()
            if not data:
                await callback.answer("❌ Данные о тарифе не найдены", show_alert=True)
                return
            
            tariff_days = data.get('days', 30)
            tariff_name = data.get('tariff_name', '1 месяц')
            amount = data.get('amount', 0)
            
            # Получаем количество дней из метаданных платежа
            days = int(payment_info['metadata']['days'])
            
            # СОЗДАЕМ ЗАПИСЬ В ТАБЛИЦЕ PAYMENTS
            payment_id = payment_info.get('id', f"manual_{datetime.now().timestamp()}")
            success = await PaymentManager.create_payment_record(
                user_id=user_id,
                payment_id=payment_id,
                tariff_name=tariff_name,
                amount=amount,
                status='succeeded',
                days=days  # ← Исправлено
            )
            
            if not success:
                logger.error(f"Failed to create payment record for user {user_id}")
            
            # ✅ ВСТАВЛЯЕМ ЗДЕСЬ - НЕМЕДЛЕННАЯ АКТИВАЦИЯ ПЛАНЕРА
            # После создания/обновления подписки:
            await PaymentManager.activate_planner_immediately(user_id)
            
            # Проверяем текущий статус подписки пользователя
            current_subscription = await PaymentManager.get_payment_info(user_id)
            logger.info(f"Current subscription after payment: {current_subscription}")
            
            if current_subscription and current_subscription.get('is_active', False):
                # Получаем дату окончания подписки
                valid_until_str = current_subscription.get('valid_until')
                if valid_until_str:
                    try:
                        # Преобразуем строку в datetime объект
                        valid_until = datetime.strptime(valid_until_str, '%Y-%m-%d %H:%M:%S')
                        formatted_date = valid_until.strftime('%d.%m.%Y')
                    except:
                        formatted_date = valid_until_str
                else:
                    formatted_date = "не определена"
                
                # Формируем сообщение
                text = (
                    f"✅ Вы продлили подписку на {days} дней\n\n"
                    f"📅 Подписка активна до: {formatted_date}\n"
                    f"💳 Тариф: {tariff_name}\n\n"
                    f"🎉 Вам доступен весь функционал!"
                )
                
                # ✅ ВСТАВЛЯЕМ ЗДЕСЬ - СООБЩЕНИЕ ОБ АКТИВАЦИИ ПЛАНЕРА
                await callback.message.answer(
                    "✅ Оплата прошла успешно! Планер активирован.\n"
                    "Теперь вы можете создавать и редактировать задачи для учеников."
                )
            else:
                text = "❌ Ошибка активации подписки. Обратитесь в поддержку."
            
            # Показываем подробное сообщение
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ В главное меню", callback_data="back_to_main_menu")]
            ])
            
            await safe_edit_message(
                callback.message,
                text=text,
                reply_markup=keyboard,
                parse_mode='Markdown'
            )
            
            await callback.answer()
            
        elif status == 'pending':
            await callback.answer("⏳ Платеж в обработке", show_alert=True)
        elif status in ['canceled', 'failed']:
            await callback.answer("❌ Платеж не прошел", show_alert=True)
        else:
            await callback.answer("❓ Неизвестный статус платежа", show_alert=True)
            
    except Exception as e:
        logger.error(f"Error in check_payment_handler: {e}", exc_info=True)
        await callback.answer("❌ Ошибка проверки платежа", show_alert=True)


@router.callback_query(F.data == "back_to_settings")
async def back_to_settings_handler(callback: types.CallbackQuery, state: FSMContext):
    """Возврат к настройкам"""
    await settings_handler(callback, state)

@router.callback_query(F.data == "back_to_main_menu")
async def back_to_main_menu_handler(callback: types.CallbackQuery):
    """Обработчик возврата в главное меню"""
    try:
        from database import Database
        
        db = Database()
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM tutors WHERE telegram_id = ?", (callback.from_user.id,))
            tutor = cursor.fetchone()
        
        if not tutor:
            await safe_edit_message(
                callback.message,
                text="❌ Ошибка: не найдены данные репетитора",
                parse_mode="HTML"
            )
            return
        
        # Используем универсальную функцию
        await show_main_menu(
            chat_id=callback.from_user.id,
            callback_query=callback
        )
        
    except Exception as e:
        logger.error(f"Error in back_to_main_menu_handler: {e}", exc_info=True)
        await callback.answer("❌ Ошибка возврата в главное меню", show_alert=True)
    
    await callback.answer()

async def handle_payment_success(telegram_id: int):
    """Обработка успешной оплаты - включаем планер"""
    success = await planner_manager.update_tutor_planner_status(telegram_id, True)
    if success:
        logger.info(f"Планер включен для репетитора {telegram_id} после оплаты")
    else:
        logger.error(f"Ошибка при включении планера для репетитора {telegram_id}")

async def handle_payment_expired(telegram_id: int):
    """Обработка истечения подписки - отключаем планер"""
    success = await planner_manager.update_tutor_planner_status(telegram_id, False)
    if success:
        logger.info(f"Планер отключен для репетитора {telegram_id} (подписка истекла)")
    else:
        logger.error(f"Ошибка при отключении планера для репетитора {telegram_id}")