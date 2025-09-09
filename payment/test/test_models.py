import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from payment.models import PaymentManager, db
from datetime import datetime, timedelta

@pytest.mark.asyncio
async def test_get_payment_info_exists():
    """Тест получения информации об оплате (подписка существует)"""
    future_date = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
    
    mock_result = {
        'valid_until': future_date,
        'tariff': 'Premium',
        'is_active': True
    }
    
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = mock_result
    
    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    mock_conn.__enter__.return_value = mock_conn
    mock_conn.__exit__.return_value = None
    
    with patch.object(db, 'get_connection', return_value=mock_conn):
        result = await PaymentManager.get_payment_info(123)
        
        assert result is not None
        assert result['valid_until'] == future_date
        assert result['tariff'] == 'Premium'
        assert result['is_active'] == True

@pytest.mark.asyncio
async def test_get_payment_info_not_exists():
    """Тест получения информации об оплате (подписка не существует)"""
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = None
    
    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    mock_conn.__enter__.return_value = mock_conn
    mock_conn.__exit__.return_value = None
    
    with patch.object(db, 'get_connection', return_value=mock_conn):
        result = await PaymentManager.get_payment_info(123)
        
        assert result is None

@pytest.mark.asyncio
async def test_get_payment_info_expired():
    """Тест получения информации об оплате (подписка истекла)"""
    past_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    
    mock_result = {
        'valid_until': past_date,
        'tariff': 'Premium',
        'is_active': True
    }
    
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = mock_result
    
    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    mock_conn.__enter__.return_value = mock_conn
    mock_conn.__exit__.return_value = None
    
    with patch.object(db, 'get_connection', return_value=mock_conn):
        result = await PaymentManager.get_payment_info(123)
        
        assert result is not None
        assert result['is_active'] == False

@pytest.mark.asyncio
async def test_update_subscription_success():
    """Тест обновления подписки (успех)"""
    mock_cursor = MagicMock()
    mock_cursor.execute.return_value = None
    
    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    mock_conn.commit.return_value = None
    mock_conn.__enter__.return_value = mock_conn
    mock_conn.__exit__.return_value = None
    
    with patch.object(db, 'get_connection', return_value=mock_conn):
        success = await PaymentManager.update_subscription(
            user_id=123,
            days=30,
            tariff="Premium"
        )
        
        assert success == True
        mock_cursor.execute.assert_called_once()

@pytest.mark.asyncio
async def test_update_subscription_failure():
    """Тест обновления подписки (ошибка)"""
    mock_cursor = MagicMock()
    mock_cursor.execute.side_effect = Exception("Database error")
    
    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    mock_conn.__enter__.return_value = mock_conn
    mock_conn.__exit__.return_value = None
    
    with patch.object(db, 'get_connection', return_value=mock_conn):
        success = await PaymentManager.update_subscription(
            user_id=123,
            days=30,
            tariff="Premium"
        )
        
        assert success == False

@pytest.mark.asyncio
async def test_check_subscription_active():
    """Тест проверки активной подписки"""
    future_date = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
    
    mock_result = {
        'valid_until': future_date,
        'tariff': 'Premium',
        'is_active': True
    }
    
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = mock_result
    
    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    mock_conn.__enter__.return_value = mock_conn
    mock_conn.__exit__.return_value = None
    
    with patch.object(db, 'get_connection', return_value=mock_conn):
        is_active = await PaymentManager.check_subscription(123)
        
        assert is_active == True

@pytest.mark.asyncio
async def test_check_subscription_inactive():
    """Тест проверки неактивной подписки"""
    # Мокаем get_payment_info чтобы он возвращал None
    with patch.object(PaymentManager, 'get_payment_info', return_value=None):
        is_active = await PaymentManager.check_subscription(123)
        
        # Метод возвращает None, а не False, когда подписки нет
        assert is_active is None

@pytest.mark.asyncio
async def test_check_subscription_expired():
    """Тест проверки истекшей подписки"""
    past_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    
    mock_info = {
        'valid_until': past_date,
        'tariff': 'Premium',
        'is_active': False  # Подписка истекла
    }
    
    with patch.object(PaymentManager, 'get_payment_info', return_value=mock_info):
        is_active = await PaymentManager.check_subscription(123)
        
        # Метод возвращает False, когда подписка есть но неактивна
        assert is_active == False