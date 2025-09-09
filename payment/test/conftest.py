import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from aiogram.types import Update, Message, CallbackQuery, User, Chat
import pytest

pytest_plugins = ['pytest_asyncio']

# Фикстуры для тестов
@pytest.fixture
def mock_user():
    """Фикстура для создания mock пользователя"""
    return User(id=123, first_name="Test", is_bot=False, username="test_user")

@pytest.fixture
def mock_chat():
    """Фикстура для создания mock чата"""
    return Chat(id=456, type="private")

@pytest.fixture
def mock_message(mock_user, mock_chat):
    """Фикстура для создания mock сообщения"""
    message = AsyncMock(spec=Message)
    message.from_user = mock_user
    message.chat = mock_chat
    message.text = "/start"
    message.answer = AsyncMock()
    return message

@pytest.fixture
def mock_callback_query(mock_user, mock_chat):
    """Фикстура для создания mock callback query"""
    callback = AsyncMock(spec=CallbackQuery)
    callback.from_user = mock_user
    callback.data = "test_callback"
    callback.answer = AsyncMock()
    
    message = AsyncMock(spec=Message)
    message.from_user = mock_user
    message.chat = mock_chat
    message.edit_text = AsyncMock()
    message.answer = AsyncMock()
    
    callback.message = message
    return callback

@pytest.fixture
def mock_update_message(mock_message):
    """Фикстура для создания mock update с сообщением"""
    update = AsyncMock(spec=Update)
    update.message = mock_message
    update.callback_query = None
    return update

@pytest.fixture
def mock_update_callback(mock_callback_query):
    """Фикстура для создания mock update с callback query"""
    update = AsyncMock(spec=Update)
    update.message = None
    update.callback_query = mock_callback_query
    return update

@pytest.fixture
def mock_state():
    """Фикстура для создания mock состояния"""
    state = AsyncMock()
    state.get_state = AsyncMock(return_value=None)
    state.update_data = AsyncMock()
    state.clear = AsyncMock()
    state.set_state = AsyncMock()
    return state

# Настройка event loop для асинхронных тестов
@pytest.fixture(scope="session")
def event_loop():
    """Создание event loop для асинхронных тестов"""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()