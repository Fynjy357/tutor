from aiogram import types, Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.exceptions import TelegramBadRequest
from handlers.schedule.schedule_utils import get_today_schedule_text
from handlers.start.config import WELCOME_BACK_TEXT
from handlers.start.keyboards_start import get_registration_keyboard
from keyboards.main_menu import get_main_menu_keyboard
from .models import PaymentManager
from .yookassa_integration import YooKassaManager

# Импорты для функции get_today_schedule_text (добавьте если нужно)
# from your_module import get_today_schedule_text, db

router = Router()
yookassa = YooKassaManager()

@router.callback_query(F.data == "settings")
async def settings_handler(callback: types.CallbackQuery, state: FSMContext):
    """Обработчик кнопки настроек"""
    user_id = callback.from_user.id
    payment_info = await PaymentManager.get_payment_info(user_id)
    
    if payment_info and payment_info['is_active']:
        message_text = f"💰 **Статус подписки**\n\n" \
                      f"✅ Сервис оплачен\n" \
                      f"📅 Действует до: {payment_info['valid_until']}\n" \
                      f"💳 Тариф: {payment_info['tariff']}\n\n" \
                      f"Вы можете продлить подписку:"
    else:
        message_text = "❌ **Сервис не оплачен**\n\n" \
                      "Для доступа к полному функционалу необходимо оплатить подписку."
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Оплата сервиса", callback_data="payment_menu")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_main_menu")]
    ])
    
    await callback.message.edit_text(message_text, reply_markup=keyboard, parse_mode='Markdown')
    await callback.answer()

@router.callback_query(F.data == "payment_menu")
async def payment_menu_handler(callback: types.CallbackQuery, state: FSMContext):
    """Меню выбора тарифа оплаты"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📅 1 месяц - 120 руб", callback_data="payment_1month")],
        [InlineKeyboardButton(text="📅 6 месяцев - 650 руб", callback_data="payment_6months")],
        [InlineKeyboardButton(text="📅 1 год - 1000 руб", callback_data="payment_1year")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_settings")]
    ])  # ← Исправлено на back_to_settings
    
    text = "💳 **Выберите тариф подписки:**\n\n" \
           "• 1 месяц - 120 рублей\n" \
           "• 6 месяцев - 650 рублей (≈108 руб/мес)\n" \
           "• 1 год - 1000 рублей (≈83 руб/мес)\n\n" \
           "💰 **Экономия при долгосрочной подписке!**"
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode='Markdown')
    await callback.answer()

@router.callback_query(F.data.startswith("payment_"))
async def process_payment_handler(callback: types.CallbackQuery, state: FSMContext):
    """Обработчик выбора тарифа"""
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
            
            await callback.message.edit_text(text, reply_markup=keyboard, parse_mode='Markdown')
        else:
            await callback.message.edit_text(
                "❌ Ошибка создания платежа. Попробуйте позже.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="◀️ Назад", callback_data="payment_menu")]
                ])
            )
    
    await callback.answer()

@router.callback_query(F.data == "check_payment")
async def check_payment_handler(callback: types.CallbackQuery, state: FSMContext):
    """Проверка оплаты"""
    data = await state.get_data()
    
    # Здесь должна быть логика проверки оплаты через API ЮKassa
    # Временно имитируем успешную оплату
    
    if data:
        success = await PaymentManager.update_subscription(
            user_id=callback.from_user.id,
            days=data['days'],
            tariff=data['tariff_name']
        )
        
        if success:
            text = f"✅ **Оплата прошла успешно!**\n\n" \
                  f"Ваша подписка активирована на {data['days']} дней.\n" \
                  f"Тариф: {data['tariff_name']}\n\n" \
                  f"Теперь вам доступен полный функционал сервиса!"
        else:
            text = "❌ Ошибка активации подписки. Обратитесь в поддержку."
    else:
        text = "❌ Не найдены данные об оплате. Попробуйте выбрать тариф заново."
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ В главное меню", callback_data="back_to_main_menu")]
    ])  # ← Исправлено на back_to_main_menu
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode='Markdown')
    await callback.answer()

@router.callback_query(F.data == "back_to_settings")
async def back_to_settings_handler(callback: types.CallbackQuery, state: FSMContext):
    """Возврат к настройкам"""
    await settings_handler(callback, state)

@router.callback_query(F.data == "back_to_main_menu")
async def back_to_main_menu_handler(callback: types.CallbackQuery):
    """Обработчик возврата в главное меню"""
    # ВАЖНО: Раскомментируйте и настройте импорты для этих функций:
    from database import db
    
    # Получаем данные репетитора
    tutor = db.get_tutor_by_telegram_id(callback.from_user.id)
    
    # Временно закомментировал проблемные части:
    if not tutor:
        try:
            await callback.message.edit_text(
                "❌ Ошибка: не найдены данные репетитора",
                parse_mode="HTML"
            )
        except TelegramBadRequest:
            await callback.message.answer(
                "❌ Ошибка: не найдены данные репетитора",
                parse_mode="HTML"
            )
        return
    
    tutor_id = tutor[0]
    schedule_text = await get_today_schedule_text(tutor_id)
    
    # Временное решение - просто показываем главное меню
    try:
        await callback.message.edit_text(
            WELCOME_BACK_TEXT.format(tutor_name=tutor[2], schedule_text=schedule_text),
            reply_markup=get_main_menu_keyboard(),
            parse_mode="HTML"
        )
    except TelegramBadRequest:
        await callback.message.answer(
            WELCOME_BACK_TEXT.format(tutor_name=tutor[2], schedule_text=schedule_text),
            reply_markup=get_main_menu_keyboard(),
            parse_mode="HTML"
        )
    
    await callback.answer()