"""User service orchestrating repository operations."""

from __future__ import annotations

import uuid
from datetime import datetime

from app.models.user import User
from app.repositories.user import UserRepository


class UserService:
    """High-level user operations."""

    def __init__(self, repository: UserRepository) -> None:
        self.repository = repository

    async def register_user(
        self,
        *,
        telegram_id: int,
        first_name: str,
        last_name: str | None = None,
        username: str | None = None,
        timezone: str | None = None,
        language_code: str | None = None,
    ) -> User:
        return await self.repository.create(
            telegram_id=telegram_id,
            first_name=first_name,
            last_name=last_name,
            username=username,
            timezone=timezone,
            language_code=language_code,
        )

    async def get_by_telegram(self, telegram_id: int) -> User | None:
        return await self.repository.get_by_telegram_id(telegram_id)

    async def update_last_activity(
        self, user_id: uuid.UUID, *, timestamp: datetime | None = None
    ) -> None:
        await self.repository.touch_last_activity(user_id, timestamp=timestamp)


__all__ = ["UserService"]
