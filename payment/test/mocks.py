from unittest.mock import AsyncMock, MagicMock
from aiogram.types import User, Chat

def create_mock_user():
    """Создание mock пользователя"""
    return User(id=123, first_name="Test", is_bot=False, username="test_user")

def create_mock_chat():
    """Создание mock чата"""
    return Chat(id=456, type="private")

def create_mock_message(user=None, chat=None):
    """Создание mock сообщения"""
    user = user or create_mock_user()
    chat = chat or create_mock_chat()
    
    message = AsyncMock()
    message.from_user = user
    message.chat = chat
    message.text = "/start"
    message.answer = AsyncMock()
    return message

def create_mock_callback_query(user=None, chat=None):
    """Создание mock callback query"""
    user = user or create_mock_user()
    chat = chat or create_mock_chat()
    
    callback = AsyncMock()
    callback.from_user = user
    callback.data = "test_callback"
    callback.answer = AsyncMock()
    
    message = AsyncMock()
    message.from_user = user
    message.chat = chat
    message.edit_text = AsyncMock()
    message.answer = AsyncMock()
    
    callback.message = message
    return callback