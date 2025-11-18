"""Repository helpers for Deck entities."""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy import Select, select
from sqlalchemy.orm import selectinload

from app.models.deck import Deck
from app.models.language_profile import LanguageProfile
from app.repositories.base import BaseRepository


class DeckRepository(BaseRepository[Deck]):
    """Persistence primitives for Deck objects."""

    async def list_for_user(
        self,
        user_id: uuid.UUID,
        *,
        profile_id: uuid.UUID | None = None,
        include_group: bool = True,
    ) -> list[Deck]:
        stmt: Select[tuple[Deck]] = (
            select(Deck)
            .join(LanguageProfile, Deck.profile_id == LanguageProfile.id)
            .options(selectinload(Deck.owner))
            .where(
                Deck.deleted.is_(False),
                LanguageProfile.deleted.is_(False),
                LanguageProfile.user_id == user_id,
            )
            .order_by(Deck.created_at.asc())
        )

        if profile_id is not None:
            stmt = stmt.where(Deck.profile_id == profile_id)
        if not include_group:
            stmt = stmt.where(Deck.is_group.is_(False))

        result = await self.session.execute(stmt)
        return list(result.scalars().unique())

    async def get_for_user(self, deck_id: uuid.UUID, user_id: uuid.UUID) -> Deck | None:
        stmt = (
            select(Deck)
            .join(LanguageProfile, Deck.profile_id == LanguageProfile.id)
            .options(selectinload(Deck.owner))
            .where(
                Deck.id == deck_id,
                Deck.deleted.is_(False),
                LanguageProfile.deleted.is_(False),
                LanguageProfile.user_id == user_id,
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_ids(self, deck_ids: Sequence[uuid.UUID]) -> list[Deck]:
        if not deck_ids:
            return []
        stmt = (
            select(Deck)
            .options(selectinload(Deck.owner))
            .where(Deck.id.in_(deck_ids), Deck.deleted.is_(False))
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().unique())


__all__ = ["DeckRepository"]
