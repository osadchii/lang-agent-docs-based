"""Repository helpers for working with language profiles."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Select, func, select, update

from app.models.language_profile import LanguageProfile
from app.repositories.base import BaseRepository


class LanguageProfileRepository(BaseRepository[LanguageProfile]):
    """Persistence helpers for LanguageProfile entities."""

    async def list_for_user(self, user_id: uuid.UUID) -> list[LanguageProfile]:
        stmt: Select[tuple[LanguageProfile]] = (
            select(LanguageProfile)
            .where(
                LanguageProfile.user_id == user_id,
                LanguageProfile.deleted.is_(False),
            )
            .order_by(
                LanguageProfile.is_active.desc(),
                LanguageProfile.created_at.asc(),
            )
        )
        result = await self.session.execute(stmt)
        return list(result.scalars())

    async def count_for_user(self, user_id: uuid.UUID) -> int:
        stmt = select(func.count()).where(
            LanguageProfile.user_id == user_id,
            LanguageProfile.deleted.is_(False),
        )
        result = await self.session.execute(stmt)
        return int(result.scalar_one())

    async def get_by_id_for_user(
        self,
        profile_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> LanguageProfile | None:
        stmt = select(LanguageProfile).where(
            LanguageProfile.id == profile_id,
            LanguageProfile.user_id == user_id,
            LanguageProfile.deleted.is_(False),
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_language(
        self,
        user_id: uuid.UUID,
        language: str,
    ) -> LanguageProfile | None:
        stmt = select(LanguageProfile).where(
            LanguageProfile.user_id == user_id,
            LanguageProfile.language == language,
            LanguageProfile.deleted.is_(False),
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_active_for_user(self, user_id: uuid.UUID) -> LanguageProfile | None:
        stmt = select(LanguageProfile).where(
            LanguageProfile.user_id == user_id,
            LanguageProfile.deleted.is_(False),
            LanguageProfile.is_active.is_(True),
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_alternate_profile(
        self, user_id: uuid.UUID, *, exclude_id: uuid.UUID
    ) -> LanguageProfile | None:
        stmt = (
            select(LanguageProfile)
            .where(
                LanguageProfile.user_id == user_id,
                LanguageProfile.deleted.is_(False),
                LanguageProfile.id != exclude_id,
            )
            .order_by(LanguageProfile.created_at.asc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def deactivate_user_profiles(
        self, user_id: uuid.UUID, *, exclude: uuid.UUID | None = None
    ) -> None:
        stmt = update(LanguageProfile).where(
            LanguageProfile.user_id == user_id,
            LanguageProfile.deleted.is_(False),
        )
        if exclude is not None:
            stmt = stmt.where(LanguageProfile.id != exclude)
        await self.session.execute(stmt.values(is_active=False))

    async def soft_delete(self, profile: LanguageProfile) -> None:
        profile.deleted = True
        profile.deleted_at = datetime.now(tz=timezone.utc)
        profile.is_active = False
        await self.session.flush()


__all__ = ["LanguageProfileRepository"]
