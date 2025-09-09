import pytest
from unittest.mock import AsyncMock, patch
from aiogram.types import Update, Message, CallbackQuery, User, Chat
from payment.middleware import SubscriptionMiddleware
from payment.models import PaymentManager

@pytest.mark.asyncio
async def test_middleware_non_premium_message(mock_update_message):
    """Тест middleware для не-премиум сообщения"""
    middleware = SubscriptionMiddleware()
    handler = AsyncMock()
    
    # Обычная команда
    mock_update_message.message.text = "/start"
    
    await middleware(handler, mock_update_message, {})
    
    handler.assert_called_once()

@pytest.mark.asyncio
async def test_middleware_premium_message_with_subscription(mock_update_message):
    """Тест middleware для премиум сообщения с подпиской"""
    middleware = SubscriptionMiddleware()
    handler = AsyncMock()
    
    # Премиум команда
    mock_update_message.message.text = "/premium"
    
    with patch.object(PaymentManager, 'check_subscription', AsyncMock(return_value=True)):
        await middleware(handler, mock_update_message, {})
        
        handler.assert_called_once()

@pytest.mark.asyncio
async def test_middleware_premium_message_without_subscription(mock_update_message):
    """Тест middleware для премиум сообщения без подписки"""
    middleware = SubscriptionMiddleware()
    handler = AsyncMock()
    
    # Премиум команда
    mock_update_message.message.text = "/premium"
    
    with patch.object(PaymentManager, 'check_subscription', AsyncMock(return_value=False)):
        await middleware(handler, mock_update_message, {})
        
        handler.assert_not_called()
        mock_update_message.message.answer.assert_called_once()

@pytest.mark.asyncio
async def test_middleware_premium_callback_with_subscription(mock_update_callback):
    """Тест middleware для премиум callback с подпиской"""
    middleware = SubscriptionMiddleware()
    handler = AsyncMock()
    
    # Премиум callback
    mock_update_callback.callback_query.data = "generate_test"
    
    with patch.object(PaymentManager, 'check_subscription', AsyncMock(return_value=True)):
        await middleware(handler, mock_update_callback, {})
        
        handler.assert_called_once()

@pytest.mark.asyncio
async def test_middleware_premium_callback_without_subscription(mock_update_callback):
    """Тест middleware для премиум callback без подписки"""
    middleware = SubscriptionMiddleware()
    handler = AsyncMock()
    
    # Премиум callback
    mock_update_callback.callback_query.data = "generate_test"
    
    with patch.object(PaymentManager, 'check_subscription', AsyncMock(return_value=False)):
        await middleware(handler, mock_update_callback, {})
        
        handler.assert_not_called()
        mock_update_callback.callback_query.answer.assert_called_once()
        mock_update_callback.callback_query.message.answer.assert_called_once()