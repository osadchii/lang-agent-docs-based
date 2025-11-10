from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock
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
