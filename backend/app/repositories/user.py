"""User repository for CRUD operations."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Select, select, update

from app.models.user import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    """Encapsulates persistence logic for User entities."""

    async def create(
        self,
        *,
        telegram_id: int,
        first_name: str,
        last_name: str | None = None,
        username: str | None = None,
        timezone: str | None = None,
        language_code: str | None = None,
        is_premium: bool = False,
    ) -> User:
        user = User(
            telegram_id=telegram_id,
            first_name=first_name,
            last_name=last_name,
            username=username,
            timezone=timezone or "UTC",
            language_code=language_code,
            is_premium=is_premium,
        )
        await self.add(user)
        await self.session.refresh(user)
        return user

    async def get(self, user_id: uuid.UUID) -> User | None:
        return await self.session.get(User, user_id)

    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        stmt = select(User).where(User.telegram_id == telegram_id, User.deleted.is_(False))
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_active(self, *, limit: int = 100, offset: int = 0) -> list[User]:
        stmt: Select[tuple[User]] = (
            select(User)
            .where(User.deleted.is_(False))
            .order_by(User.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars())

    async def soft_delete(self, user_id: uuid.UUID) -> None:
        now = datetime.now(tz=timezone.utc)
        stmt = update(User).where(User.id == user_id).values(deleted=True, deleted_at=now)
        await self.session.execute(stmt)

    async def touch_last_activity(self, user_id: uuid.UUID, *, timestamp: datetime | None = None) -> None:
        ts = timestamp or datetime.now(tz=timezone.utc)
        stmt = (
            update(User)
            .where(User.id == user_id)
            .values(last_activity=ts)
        )
        await self.session.execute(stmt)


__all__ = ["UserRepository"]
