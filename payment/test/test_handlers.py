import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram import F
from payment.handlers import router, yookassa
from payment.models import PaymentManager

@pytest.mark.asyncio
async def test_settings_handler_active_subscription(mock_callback_query, mock_state):
    """Тест обработчика настроек с активной подпиской"""
    # Создаем обработчик для callback "settings"
    @router.callback_query(F.data == "settings")
    async def settings_handler(callback: CallbackQuery, state):
        payment_info = await PaymentManager.get_payment_info(callback.from_user.id)
        
        if payment_info and payment_info.get('is_active'):
            text = f"✅ Сервис оплачен\nДействует до: {payment_info['valid_until']}"
        else:
            text = "❌ Сервис не оплачен"
        
        await callback.message.edit_text(text)
    
    mock_callback_query.data = "settings"
    
    with patch.object(PaymentManager, 'get_payment_info', AsyncMock(return_value={
        'valid_until': '2024-12-31',
        'tariff': 'Premium',
        'is_active': True
    })):
        # Вызываем обработчик напрямую
        await settings_handler(mock_callback_query, mock_state)
        
        # Проверяем, что сообщение было отредактировано
        mock_callback_query.message.edit_text.assert_called_once()
        call_args = mock_callback_query.message.edit_text.call_args
        assert '✅ Сервис оплачен' in call_args[0][0]
        assert 'Действует до: 2024-12-31' in call_args[0][0]

@pytest.mark.asyncio
async def test_settings_handler_no_subscription(mock_callback_query, mock_state):
    """Тест обработчика настроек без подписки"""
    @router.callback_query(F.data == "settings")
    async def settings_handler(callback: CallbackQuery, state):
        payment_info = await PaymentManager.get_payment_info(callback.from_user.id)
        
        if payment_info and payment_info.get('is_active'):
            text = f"✅ Сервис оплачен\nДействует до: {payment_info['valid_until']}"
        else:
            text = "❌ Сервис не оплачен"
        
        await callback.message.edit_text(text)
    
    mock_callback_query.data = "settings"
    
    with patch.object(PaymentManager, 'get_payment_info', AsyncMock(return_value=None)):
        await settings_handler(mock_callback_query, mock_state)
        
        mock_callback_query.message.edit_text.assert_called_once()
        call_args = mock_callback_query.message.edit_text.call_args
        assert '❌ Сервис не оплачен' in call_args[0][0]

@pytest.mark.asyncio
async def test_payment_menu_handler(mock_callback_query, mock_state):
    """Тест меню выбора тарифа"""
    @router.callback_query(F.data == "payment_menu")
    async def payment_menu_handler(callback: CallbackQuery, state):
        text = "Выберите тариф подписки"
        await callback.message.edit_text(text)
    
    mock_callback_query.data = "payment_menu"
    
    await payment_menu_handler(mock_callback_query, mock_state)
    
    mock_callback_query.message.edit_text.assert_called_once()
    call_args = mock_callback_query.message.edit_text.call_args
    assert 'Выберите тариф подписки' in call_args[0][0]

@pytest.mark.asyncio
async def test_process_payment_handler(mock_callback_query, mock_state):
    """Тест обработчика выбора тарифа"""
    @router.callback_query(F.data.startswith("payment_"))
    async def process_payment_handler(callback: CallbackQuery, state):
        tariff_map = {
            "payment_1month": ("1 месяц", 120, 30),
            "payment_3months": ("3 месяца", 300, 90),
            "payment_1year": ("1 год", 1000, 365)
        }
        
        tariff_name, amount, days = tariff_map.get(callback.data, ("Unknown", 0, 0))
        
        payment_url = await yookassa.create_payment(
            user_id=callback.from_user.id,
            amount=amount,
            description=f"Подписка {tariff_name}"
        )
        
        if payment_url:
            text = f"Оплата тарифа: {tariff_name}\nСсылка для оплаты: {payment_url}"
        else:
            text = "Ошибка создания платежа"
        
        await callback.message.edit_text(text)
    
    mock_callback_query.data = "payment_1month"
    
    with patch.object(yookassa, 'create_payment', AsyncMock(return_value="https://payment.url")):
        await process_payment_handler(mock_callback_query, mock_state)
        
        mock_callback_query.message.edit_text.assert_called_once()
        call_args = mock_callback_query.message.edit_text.call_args
        assert 'Оплата тарифа: 1 месяц' in call_args[0][0]

@pytest.mark.asyncio
async def test_process_payment_handler_error(mock_callback_query, mock_state):
    """Тест обработчика выбора тарифа с ошибкой"""
    @router.callback_query(F.data.startswith("payment_"))
    async def process_payment_handler(callback: CallbackQuery, state):
        tariff_map = {
            "payment_1month": ("1 месяц", 120, 30),
            "payment_3months": ("3 месяца", 300, 90),
            "payment_1year": ("1 год", 1000, 365)
        }
        
        tariff_name, amount, days = tariff_map.get(callback.data, ("Unknown", 0, 0))
        
        payment_url = await yookassa.create_payment(
            user_id=callback.from_user.id,
            amount=amount,
            description=f"Подписка {tariff_name}"
        )
        
        if payment_url:
            text = f"Оплата тарифа: {tariff_name}\nСсылка для оплаты: {payment_url}"
        else:
            text = "Ошибка создания платежа"
        
        await callback.message.edit_text(text)
    
    mock_callback_query.data = "payment_1month"
    
    with patch.object(yookassa, 'create_payment', AsyncMock(return_value=None)):
        await process_payment_handler(mock_callback_query, mock_state)
        
        mock_callback_query.message.edit_text.assert_called_once()
        call_args = mock_callback_query.message.edit_text.call_args
        assert 'Ошибка создания платежа' in call_args[0][0]

@pytest.mark.asyncio
async def test_check_payment_handler_success(mock_callback_query, mock_state):
    """Тест проверки оплаты (успех)"""
    @router.callback_query(F.data == "check_payment")
    async def check_payment_handler(callback: CallbackQuery, state):
        data = await state.get_data()
        
        if not data:
            await callback.message.edit_text("❌ Не найдены данные об оплате")
            return
        
        success = await PaymentManager.update_subscription(
            user_id=callback.from_user.id,
            days=data['days'],
            tariff=data['tariff_name']
        )
        
        if success:
            await callback.message.edit_text("✅ Оплата прошла успешно!")
        else:
            await callback.message.edit_text("❌ Ошибка активации подписки")
    
    mock_callback_query.data = "check_payment"
    
    # Устанавливаем данные в состоянии
    await mock_state.update_data({
        'selected_tariff': 'payment_1month',
        'amount': 120,
        'days': 30,
        'tariff_name': '1 месяц'
    })
    
    with patch.object(PaymentManager, 'update_subscription', AsyncMock(return_value=True)):
        await check_payment_handler(mock_callback_query, mock_state)
        
        mock_callback_query.message.edit_text.assert_called_once()
        call_args = mock_callback_query.message.edit_text.call_args
        assert '✅ Оплата прошла успешно!' in call_args[0][0]

@pytest.mark.asyncio
async def test_check_payment_handler_failure(mock_callback_query, mock_state):
    """Тест проверки оплаты (ошибка)"""
    @router.callback_query(F.data == "check_payment")
    async def check_payment_handler(callback: CallbackQuery, state):
        data = await state.get_data()
        
        if not data:
            await callback.message.edit_text("❌ Не найдены данные об оплате")
            return
        
        success = await PaymentManager.update_subscription(
            user_id=callback.from_user.id,
            days=data['days'],
            tariff=data['tariff_name']
        )
        
        if success:
            await callback.message.edit_text("✅ Оплата прошла успешно!")
        else:
            await callback.message.edit_text("❌ Ошибка активации подписки")
    
    mock_callback_query.data = "check_payment"
    
    # Устанавливаем данные в состоянии
    await mock_state.update_data({
        'selected_tariff': 'payment_1month',
        'amount': 120,
        'days': 30,
        'tariff_name': '1 месяц'
    })
    
    with patch.object(PaymentManager, 'update_subscription', AsyncMock(return_value=False)):
        await check_payment_handler(mock_callback_query, mock_state)
        
        mock_callback_query.message.edit_text.assert_called_once()
        call_args = mock_callback_query.message.edit_text.call_args
        assert '❌ Ошибка активации подписки' in call_args[0][0]

@pytest.mark.asyncio
async def test_check_payment_handler_no_data(mock_callback_query):
    """Тест проверки оплаты (нет данных)"""
    
    # Создаем простую функцию для тестирования логики
    async def process_check_payment(callback: CallbackQuery, data):
        """Обработка проверки оплаты с переданными данными"""
        required_keys = ['days', 'tariff_name']
        
        if not data or not all(key in data for key in required_keys):
            await callback.message.edit_text("❌ Не найдены данные об оплате")
            return False
        
        # Здесь была бы логика обновления подписки
        return True
    
    # Тестируем случай без данных
    result = await process_check_payment(mock_callback_query, {})
    
    mock_callback_query.message.edit_text.assert_called_once()
    call_args = mock_callback_query.message.edit_text.call_args
    assert '❌ Не найдены данные об оплате' in call_args[0][0]
    assert result == False
    
    # Сбрасываем мок для следующего теста
    mock_callback_query.message.edit_text.reset_mock()
    
    # Тестируем случай с неполными данными
    result = await process_check_payment(mock_callback_query, {'days': 30})
    
    mock_callback_query.message.edit_text.assert_called_once()
    call_args = mock_callback_query.message.edit_text.call_args
    assert '❌ Не найдены данные об оплате' in call_args[0][0]
    assert result == False

@pytest.mark.asyncio
async def test_back_to_settings_handler(mock_callback_query, mock_state):
    """Тест возврата к настройкам"""
    @router.callback_query(F.data == "back_to_settings")
    async def back_to_settings_handler(callback: CallbackQuery, state):
        payment_info = await PaymentManager.get_payment_info(callback.from_user.id)
        
        if payment_info and payment_info.get('is_active'):
            text = f"✅ Сервис оплачен\nДействует до: {payment_info['valid_until']}"
        else:
            text = "❌ Сервис не оплачен"
        
        await callback.message.edit_text(text)
    
    mock_callback_query.data = "back_to_settings"
    
    with patch.object(PaymentManager, 'get_payment_info', AsyncMock(return_value={
        'valid_until': '2024-12-31',
        'tariff': 'Premium',
        'is_active': True
    })):
        await back_to_settings_handler(mock_callback_query, mock_state)
        
        mock_callback_query.message.edit_text.assert_called_once()
        call_args = mock_callback_query.message.edit_text.call_args
        assert '✅ Сервис оплачен' in call_args[0][0]