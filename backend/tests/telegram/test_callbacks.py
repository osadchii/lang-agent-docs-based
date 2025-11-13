"""Тесты для модуля обработки callback-запросов."""

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
    """Создать mock пользователя Telegram."""
    user = MagicMock(spec=User)
    user.id = 123456789
    user.first_name = "Test"
    user.last_name = "User"
    user.username = "testuser"
    user.language_code = "ru"
    return user


@pytest.fixture
def mock_message() -> Message:
    """Создать mock сообщения Telegram."""
    message = MagicMock(spec=Message)
    message.text = "*casa* — дом\n\nПример: _Mi casa es tu casa_"
    message.caption = None
    message.reply_text = AsyncMock()
    return message


@pytest.fixture
def mock_callback_query(mock_user: User, mock_message: Message) -> CallbackQuery:
    """Создать mock callback query."""
    query = MagicMock(spec=CallbackQuery)
    query.from_user = mock_user
    query.message = mock_message
    query.answer = AsyncMock()
    query.edit_message_text = AsyncMock()
    return query


@pytest.fixture
def mock_update(mock_callback_query: CallbackQuery) -> MagicMock:
    """Создать mock update с callback query."""
    update = MagicMock()
    update.callback_query = mock_callback_query
    update.effective_user = mock_callback_query.from_user
    return update


@pytest.fixture
def mock_context() -> MagicMock:
    """Создать mock контекста бота."""
    context = MagicMock()
    context.user_data = {}
    return context


@pytest.mark.asyncio
class TestHandleCallbackQuery:
    """Тесты для handle_callback_query."""

    async def test_handle_add_card_callback(
        self,
        mock_update: MagicMock,
        mock_context: MagicMock,
        mock_callback_query: CallbackQuery,
    ) -> None:
        """Тест обработки callback добавления карточки."""
        mock_callback_query.data = f"{CALLBACK_ADD_CARD}:casa:дом"

        await handle_callback_query(mock_update, mock_context)

        # Проверяем что answer был вызван
        mock_callback_query.answer.assert_called_once()
        # Проверяем что сообщение было отредактировано
        mock_callback_query.edit_message_text.assert_called_once()

    async def test_handle_add_card_from_message(
        self,
        mock_update: MagicMock,
        mock_context: MagicMock,
        mock_callback_query: CallbackQuery,
    ) -> None:
        """Тест обработки callback с извлечением данных из сообщения."""
        mock_callback_query.data = f"{CALLBACK_ADD_CARD}:from_message"

        await handle_callback_query(mock_update, mock_context)

        mock_callback_query.answer.assert_called_once()
        mock_callback_query.edit_message_text.assert_called_once()

    async def test_handle_remove_card_callback(
        self,
        mock_update: MagicMock,
        mock_context: MagicMock,
        mock_callback_query: CallbackQuery,
    ) -> None:
        """Тест обработки callback удаления карточки."""
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
        """Тест обработки callback пагинации."""
        mock_callback_query.data = f"{CALLBACK_PAGE}:2"

        await handle_callback_query(mock_update, mock_context)

        mock_callback_query.answer.assert_called_once()
        # Проверяем что номер страницы сохранен в context
        assert mock_context.user_data["current_page"] == 2

    async def test_handle_cancel_callback(
        self,
        mock_update: MagicMock,
        mock_context: MagicMock,
        mock_callback_query: CallbackQuery,
    ) -> None:
        """Тест обработки callback отмены."""
        mock_callback_query.data = CALLBACK_CANCEL

        await handle_callback_query(mock_update, mock_context)

        mock_callback_query.answer.assert_called_once()
        mock_callback_query.edit_message_text.assert_called_once()

    async def test_handle_unknown_callback(
        self,
        mock_update: MagicMock,
        mock_context: MagicMock,
        mock_callback_query: CallbackQuery,
    ) -> None:
        """Тест обработки неизвестного callback."""
        mock_callback_query.data = "unknown:action"

        await handle_callback_query(mock_update, mock_context)

        # Должен быть вызван answer с текстом ошибки
        mock_callback_query.answer.assert_called_once()
        call_args = mock_callback_query.answer.call_args
        assert call_args is not None
        assert "Неизвестное действие" in call_args.kwargs.get("text", "")

    async def test_handle_no_callback_query(
        self,
        mock_context: MagicMock,
    ) -> None:
        """Тест обработки update без callback query."""
        update = MagicMock()
        update.callback_query = None

        # Не должно быть исключений
        await handle_callback_query(update, mock_context)

    async def test_handle_callback_query_without_data(
        self,
        mock_update: MagicMock,
        mock_context: MagicMock,
        mock_callback_query: CallbackQuery,
    ) -> None:
        """Тест обработки callback query без data."""
        mock_callback_query.data = None

        # Не должно быть исключений
        await handle_callback_query(mock_update, mock_context)

    async def test_handle_add_card_invalid_message_format(
        self,
        mock_update: MagicMock,
        mock_context: MagicMock,
        mock_callback_query: CallbackQuery,
        mock_message: Message,
    ) -> None:
        """Тест обработки callback с неверным форматом сообщения."""
        mock_callback_query.data = f"{CALLBACK_ADD_CARD}:from_message"
        # Сообщение без нужного формата
        mock_message.text = "Just some random text"

        await handle_callback_query(mock_update, mock_context)

        # Должен быть вызван answer с ошибкой
        mock_callback_query.answer.assert_called_once()
        call_args = mock_callback_query.answer.call_args
        assert call_args is not None
        assert "Не удалось извлечь данные" in call_args.kwargs.get("text", "")

    async def test_handle_remove_card_invalid_format(
        self,
        mock_update: MagicMock,
        mock_context: MagicMock,
        mock_callback_query: CallbackQuery,
    ) -> None:
        """Тест обработки callback удаления с неверным форматом."""
        mock_callback_query.data = CALLBACK_REMOVE_CARD  # Без card_id

        await handle_callback_query(mock_update, mock_context)

        # Должен быть вызван answer с ошибкой
        mock_callback_query.answer.assert_called_once()
        call_args = mock_callback_query.answer.call_args
        assert call_args is not None
        assert "Неверный формат" in call_args.kwargs.get("text", "")

    async def test_handle_pagination_invalid_page_number(
        self,
        mock_update: MagicMock,
        mock_context: MagicMock,
        mock_callback_query: CallbackQuery,
    ) -> None:
        """Тест обработки callback пагинации с невалидным номером страницы."""
        mock_callback_query.data = f"{CALLBACK_PAGE}:not_a_number"

        await handle_callback_query(mock_update, mock_context)

        # Должен быть вызван answer с ошибкой
        mock_callback_query.answer.assert_called_once()
        call_args = mock_callback_query.answer.call_args
        assert call_args is not None
        assert "Неверный номер страницы" in call_args.kwargs.get("text", "")
