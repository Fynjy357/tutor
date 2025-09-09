import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import aiohttp
from payment.yookassa_integration import YooKassaManager

@pytest.mark.asyncio
async def test_create_payment_success():
    """Тест успешного создания платежа в YooKassa"""
    # Создаем экземпляр менеджера
    yookassa = YooKassaManager()
    
    # Мокаем base64.b64encode чтобы избежать реального кодирования
    with patch('payment.yookassa_integration.base64.b64encode') as mock_b64:
        mock_b64.return_value.decode.return_value = 'fake_auth_token'
        
        # Создаем правильный мок для асинхронного контекстного менеджера
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            'confirmation': {
                'confirmation_url': 'https://payment.url'
            }
        })
        
        # Создаем мок для асинхронного контекстного менеджера
        mock_post_context = AsyncMock()
        mock_post_context.__aenter__ = AsyncMock(return_value=mock_response)
        mock_post_context.__aexit__ = AsyncMock(return_value=None)
        
        # Мокаем session.post чтобы возвращать контекстный менеджер
        mock_session = MagicMock()
        mock_session.post.return_value = mock_post_context
        
        # Мокаем ClientSession.__aenter__ и __aexit__
        mock_session_context = AsyncMock()
        mock_session_context.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_context.__aexit__ = AsyncMock(return_value=None)
        
        with patch('aiohttp.ClientSession', return_value=mock_session_context):
            result = await yookassa.create_payment(120, 123, '1 месяц', 30)
            
            assert result == 'https://payment.url'
            mock_session.post.assert_called_once()

@pytest.mark.asyncio
async def test_create_payment_failure():
    """Тест неудачного создания платежа в YooKassa"""
    yookassa = YooKassaManager()
    
    with patch('payment.yookassa_integration.base64.b64encode') as mock_b64:
        mock_b64.return_value.decode.return_value = 'fake_auth_token'
        
        mock_response = AsyncMock()
        mock_response.status = 400
        
        mock_post_context = AsyncMock()
        mock_post_context.__aenter__ = AsyncMock(return_value=mock_response)
        mock_post_context.__aexit__ = AsyncMock(return_value=None)
        
        mock_session = MagicMock()
        mock_session.post.return_value = mock_post_context
        
        mock_session_context = AsyncMock()
        mock_session_context.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_context.__aexit__ = AsyncMock(return_value=None)
        
        with patch('aiohttp.ClientSession', return_value=mock_session_context):
            result = await yookassa.create_payment(120, 123, '1 месяц', 30)
            
            assert result is None
            mock_session.post.assert_called_once()

@pytest.mark.asyncio
async def test_create_payment_exception():
    """Тест создания платежа с исключением"""
    yookassa = YooKassaManager()
    
    with patch('payment.yookassa_integration.base64.b64encode') as mock_b64:
        mock_b64.return_value.decode.return_value = 'fake_auth_token'
        
        # Создаем исключение при вызове post
        mock_session = MagicMock()
        mock_session.post.side_effect = Exception("Network error")
        
        mock_session_context = AsyncMock()
        mock_session_context.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_context.__aexit__ = AsyncMock(return_value=None)
        
        with patch('aiohttp.ClientSession', return_value=mock_session_context):
            result = await yookassa.create_payment(120, 123, '1 месяц', 30)
            
            assert result is None
            mock_session.post.assert_called_once()

# Альтернативное решение - используем библиотеку pytest-asyncio и aioresponses
@pytest.mark.asyncio
async def test_create_payment_success_with_aioresponses():
    """Тест успешного создания платежа с использованием aioresponses"""
    try:
        from aioresponses import aioresponses
    except ImportError:
        pytest.skip("aioresponses не установлен")
    
    yookassa = YooKassaManager()
    
    with patch('payment.yookassa_integration.base64.b64encode') as mock_b64:
        mock_b64.return_value.decode.return_value = 'fake_auth_token'
        
        with aioresponses() as m:
            m.post(
                "https://api.yookassa.ru/v3/payments",
                status=200,
                payload={
                    'confirmation': {
                        'confirmation_url': 'https://payment.url'
                    }
                }
            )
            
            result = await yookassa.create_payment(120, 123, '1 месяц', 30)
            
            assert result == 'https://payment.url'

@pytest.mark.asyncio
async def test_create_payment_failure_with_aioresponses():
    """Тест неудачного создания платежа с использованием aioresponses"""
    try:
        from aioresponses import aioresponses
    except ImportError:
        pytest.skip("aioresponses не установлен")
    
    yookassa = YooKassaManager()
    
    with patch('payment.yookassa_integration.base64.b64encode') as mock_b64:
        mock_b64.return_value.decode.return_value = 'fake_auth_token'
        
        with aioresponses() as m:
            m.post(
                "https://api.yookassa.ru/v3/payments",
                status=400
            )
            
            result = await yookassa.create_payment(120, 123, '1 месяц', 30)
            
            assert result is None