"""Business logic for deck listing and retrieval."""

from __future__ import annotations

import uuid

from app.core.errors import ErrorCode, NotFoundError
from app.models.deck import Deck
from app.models.user import User
from app.repositories.deck import DeckRepository


class DeckService:
    """High-level operations for deck management."""

    def __init__(self, repository: DeckRepository) -> None:
        self.repository = repository

    async def list_decks(
        self,
        user: User,
        *,
        profile_id: uuid.UUID | None = None,
        include_group: bool = True,
    ) -> list[Deck]:
        """Return decks belonging to the provided user."""
        return await self.repository.list_for_user(
            user.id,
            profile_id=profile_id,
            include_group=include_group,
        )

    async def get_user_deck(self, user: User, deck_id: uuid.UUID) -> Deck:
        """Fetch a single deck ensuring it belongs to the current user."""
        deck = await self.repository.get_for_user(deck_id, user.id)
        if deck is None:
            raise NotFoundError(
                code=ErrorCode.DECK_NOT_FOUND,
                message="?????? ?? ??????.",
            )
        return deck


__all__ = ["DeckService"]
