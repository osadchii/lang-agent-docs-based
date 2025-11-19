"""Tests for callback query handling module."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.telegram.callbacks import handle_callback_query
from app.telegram.keyboards import (
    CALLBACK_ADD_CARD,
    CALLBACK_CANCEL,
    CALLBACK_PAGE,
    CALLBACK_REMOVE_CARD,
)
from telegram import CallbackQuery, Message, User


@pytest.fixture
def mock_user() -> User:
    """Create mock Telegram user."""
    user = MagicMock(spec=User)
    user.id = 123456789
    user.first_name = "Test"
    user.last_name = "User"
    user.username = "testuser"
    user.language_code = "ru"
    return user


@pytest.fixture
def mock_message() -> Message:
    """Create mock Telegram message."""
    message = MagicMock(spec=Message)
    message.text = "*casa* — дом\n\nПример: _Mi casa es tu casa_"
    message.caption = None
    message.reply_text = AsyncMock()
    return message


@pytest.fixture
def mock_callback_query(mock_user: User, mock_message: Message) -> CallbackQuery:
    """Create mock callback query."""
    query = MagicMock(spec=CallbackQuery)
    query.from_user = mock_user
    query.message = mock_message
    query.answer = AsyncMock()
    query.edit_message_text = AsyncMock()
    return query


@pytest.fixture
def mock_update(mock_callback_query: CallbackQuery) -> MagicMock:
    """Create mock update with callback query."""
    update = MagicMock()
    update.callback_query = mock_callback_query
    update.effective_user = mock_callback_query.from_user
    return update


@pytest.fixture
def mock_context() -> MagicMock:
    """Create mock bot context."""
    context = MagicMock()
    context.user_data = {}
    return context


@pytest.mark.asyncio
class TestHandleCallbackQuery:
    """Tests for handle_callback_query."""

    async def test_handle_add_card_callback(
        self,
        mock_update: MagicMock,
        mock_context: MagicMock,
        mock_callback_query: CallbackQuery,
    ) -> None:
        """Test handling add card callback."""
        mock_callback_query.data = f"{CALLBACK_ADD_CARD}:casa:дом"

        await handle_callback_query(mock_update, mock_context)

        mock_callback_query.answer.assert_called_once()
        mock_callback_query.edit_message_text.assert_not_called()
        mock_callback_query.message.reply_text.assert_awaited_once()

    async def test_handle_add_card_from_message(
        self,
        mock_update: MagicMock,
        mock_context: MagicMock,
        mock_callback_query: CallbackQuery,
    ) -> None:
        """Test handling callback with data extraction from message."""
        mock_callback_query.data = f"{CALLBACK_ADD_CARD}:from_message"

        await handle_callback_query(mock_update, mock_context)

        mock_callback_query.answer.assert_called_once()
        mock_callback_query.edit_message_text.assert_not_called()
        mock_callback_query.message.reply_text.assert_awaited_once()

    async def test_handle_remove_card_callback(
        self,
        mock_update: MagicMock,
        mock_context: MagicMock,
        mock_callback_query: CallbackQuery,
    ) -> None:
        """Test handling remove card callback."""
        card_id = "test-card-id"
        mock_callback_query.data = f"{CALLBACK_REMOVE_CARD}:{card_id}"

        await handle_callback_query(mock_update, mock_context)

        mock_callback_query.answer.assert_called_once()
        mock_callback_query.edit_message_text.assert_called_once()

    async def test_handle_pagination_callback(
        self,
        mock_update: MagicMock,
        mock_context: MagicMock,
        mock_callback_query: CallbackQuery,
    ) -> None:
        """Test handling pagination callback."""
        mock_callback_query.data = f"{CALLBACK_PAGE}:2"

        await handle_callback_query(mock_update, mock_context)

        # Check that answer was called (may be called twice - at start and in handler)
        assert mock_callback_query.answer.called
        # Check that page number is saved in context
        assert mock_context.user_data["current_page"] == 2

    async def test_handle_cancel_callback(
        self,
        mock_update: MagicMock,
        mock_context: MagicMock,
        mock_callback_query: CallbackQuery,
    ) -> None:
        """Test handling cancel callback."""
        mock_callback_query.data = CALLBACK_CANCEL

        await handle_callback_query(mock_update, mock_context)

        # Check that answer was called
        assert mock_callback_query.answer.called
        mock_callback_query.edit_message_text.assert_called_once()

    async def test_handle_unknown_callback(
        self,
        mock_update: MagicMock,
        mock_context: MagicMock,
        mock_callback_query: CallbackQuery,
    ) -> None:
        """Test handling unknown callback."""
        mock_callback_query.data = "unknown:action"

        await handle_callback_query(mock_update, mock_context)

        # Answer should be called (may be called twice)
        assert mock_callback_query.answer.called
        # Check last call
        call_args = mock_callback_query.answer.call_args
        assert call_args is not None
        assert "Неизвестное действие" in call_args.kwargs.get("text", "")

    async def test_handle_no_callback_query(
        self,
        mock_context: MagicMock,
    ) -> None:
        """Test handling update without callback query."""
        update = MagicMock()
        update.callback_query = None

        # Should not raise exceptions
        await handle_callback_query(update, mock_context)

    async def test_handle_callback_query_without_data(
        self,
        mock_update: MagicMock,
        mock_context: MagicMock,
        mock_callback_query: CallbackQuery,
    ) -> None:
        """Test handling callback query without data."""
        mock_callback_query.data = None

        # Should not raise exceptions
        await handle_callback_query(mock_update, mock_context)

    async def test_handle_add_card_invalid_message_format(
        self,
        mock_update: MagicMock,
        mock_context: MagicMock,
        mock_callback_query: CallbackQuery,
        mock_message: Message,
    ) -> None:
        """Test handling callback with invalid message format."""
        mock_callback_query.data = f"{CALLBACK_ADD_CARD}:from_message"
        # Message without required format
        mock_message.text = "Just some random text"

        await handle_callback_query(mock_update, mock_context)

        # Should call answer with error
        assert mock_callback_query.answer.called
        call_args = mock_callback_query.answer.call_args
        assert call_args is not None
        assert "Не удалось извлечь данные" in call_args.kwargs.get("text", "")
        assert mock_message.reply_text.await_count == 0

    async def test_handle_remove_card_invalid_format(
        self,
        mock_update: MagicMock,
        mock_context: MagicMock,
        mock_callback_query: CallbackQuery,
    ) -> None:
        """Test handling remove callback with invalid format."""
        mock_callback_query.data = CALLBACK_REMOVE_CARD  # Without card_id

        await handle_callback_query(mock_update, mock_context)

        # Should call answer with error
        assert mock_callback_query.answer.called
        call_args = mock_callback_query.answer.call_args
        assert call_args is not None
        assert "Неверный формат" in call_args.kwargs.get("text", "")

    async def test_handle_pagination_invalid_page_number(
        self,
        mock_update: MagicMock,
        mock_context: MagicMock,
        mock_callback_query: CallbackQuery,
    ) -> None:
        """Test handling pagination callback with invalid page number."""
        mock_callback_query.data = f"{CALLBACK_PAGE}:not_a_number"

        await handle_callback_query(mock_update, mock_context)

        # Should call answer with error
        assert mock_callback_query.answer.called
        call_args = mock_callback_query.answer.call_args
        assert call_args is not None
        assert "Неверный номер страницы" in call_args.kwargs.get("text", "")
