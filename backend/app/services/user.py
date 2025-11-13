"""User service orchestrating repository operations."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

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

    async def get_or_create_user(
        self,
        *,
        telegram_id: int,
        first_name: str,
        last_name: str | None = None,
        username: str | None = None,
        language_code: str | None = None,
    ) -> User:
        """
        Get an existing user by telegram_id or create a new one.

        For existing users, updates last_activity timestamp.
        For new users, creates a record with provided Telegram data.

        Args:
            telegram_id: Telegram user ID
            first_name: User's first name from Telegram
            last_name: User's last name from Telegram (optional)
            username: User's username from Telegram (optional)
            language_code: User's language code from Telegram (optional)

        Returns:
            User instance (existing or newly created)
        """
        # Try to find existing user
        user = await self.repository.get_by_telegram_id(telegram_id)

        if user:
            # Update last_activity for existing user
            await self.repository.touch_last_activity(
                user.id, timestamp=datetime.now(tz=timezone.utc)
            )
            await self.repository.session.refresh(user)
            return user

        # Create new user with Telegram data
        return await self.repository.create(
            telegram_id=telegram_id,
            first_name=first_name,
            last_name=last_name,
            username=username,
            language_code=language_code,
        )


__all__ = ["UserService"]
