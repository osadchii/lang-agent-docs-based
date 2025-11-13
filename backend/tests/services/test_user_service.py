from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.services.user import UserService


@pytest.mark.asyncio
async def test_register_user_delegates_all_fields() -> None:
    repository = AsyncMock()
    service = UserService(repository)

    expected_user = object()
    repository.create.return_value = expected_user

    result = await service.register_user(
        telegram_id=123,
        first_name="Jane",
        last_name="Doe",
        username="janedoe",
        timezone="Europe/London",
        language_code="en",
    )

    repository.create.assert_awaited_once_with(
        telegram_id=123,
        first_name="Jane",
        last_name="Doe",
        username="janedoe",
        timezone="Europe/London",
        language_code="en",
    )
    assert result is expected_user


@pytest.mark.asyncio
async def test_get_by_telegram_passes_identifier() -> None:
    repository = AsyncMock()
    service = UserService(repository)

    await service.get_by_telegram(987654)

    repository.get_by_telegram_id.assert_awaited_once_with(987654)


@pytest.mark.asyncio
async def test_update_last_activity_passes_optional_timestamp() -> None:
    repository = AsyncMock()
    service = UserService(repository)

    user_id = uuid4()
    ts = datetime(2024, 1, 1, 12, 0, 0)

    await service.update_last_activity(user_id, timestamp=ts)

    repository.touch_last_activity.assert_awaited_once_with(user_id, timestamp=ts)


@pytest.mark.asyncio
async def test_get_or_create_user_creates_new_user_when_not_found() -> None:
    """Test that get_or_create_user creates a new user when telegram_id is not found."""
    repository = AsyncMock()
    service = UserService(repository)

    # User does not exist
    repository.get_by_telegram_id.return_value = None

    # Mock created user
    new_user = MagicMock()
    new_user.id = uuid4()
    repository.create.return_value = new_user

    result = await service.get_or_create_user(
        telegram_id=123456,
        first_name="Alice",
        last_name="Smith",
        username="alicesmith",
        language_code="en",
    )

    # Verify repository calls
    repository.get_by_telegram_id.assert_awaited_once_with(123456)
    repository.create.assert_awaited_once_with(
        telegram_id=123456,
        first_name="Alice",
        last_name="Smith",
        username="alicesmith",
        language_code="en",
    )
    repository.touch_last_activity.assert_not_awaited()

    assert result is new_user


@pytest.mark.asyncio
async def test_get_or_create_user_returns_existing_and_updates_last_activity() -> None:
    """Test that get_or_create_user updates last_activity for existing user."""
    repository = AsyncMock()
    service = UserService(repository)

    # Mock existing user
    existing_user = MagicMock()
    existing_user.id = uuid4()
    repository.get_by_telegram_id.return_value = existing_user

    # Mock session refresh
    repository.session.refresh = AsyncMock()

    result = await service.get_or_create_user(
        telegram_id=123456,
        first_name="Alice",
        last_name="Smith",
        username="alicesmith",
        language_code="en",
    )

    # Verify repository calls
    repository.get_by_telegram_id.assert_awaited_once_with(123456)
    repository.touch_last_activity.assert_awaited_once()

    # Check that timestamp was passed to touch_last_activity
    call_args = repository.touch_last_activity.call_args
    assert call_args[0][0] == existing_user.id  # user_id
    assert "timestamp" in call_args[1]  # keyword argument
    assert isinstance(call_args[1]["timestamp"], datetime)

    repository.session.refresh.assert_awaited_once_with(existing_user)
    repository.create.assert_not_awaited()

    assert result is existing_user
