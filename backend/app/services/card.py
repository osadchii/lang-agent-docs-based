"""Card service exposing list/detail operations constrained by ownership."""

from __future__ import annotations

import uuid

from app.core.errors import ErrorCode, NotFoundError
from app.models.card import Card, CardStatus
from app.models.user import User
from app.repositories.card import CardRepository
from app.repositories.deck import DeckRepository


class CardService:
    """Coordinate card queries using repositories."""

    MAX_PAGE_SIZE = 100

    def __init__(self, card_repo: CardRepository, deck_repo: DeckRepository) -> None:
        self.card_repo = card_repo
        self.deck_repo = deck_repo

    async def list_cards(
        self,
        user: User,
        *,
        deck_id: uuid.UUID,
        status: CardStatus | None = None,
        search: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[Card], int]:
        """Return paginated cards for a specific deck owned by the user."""
        deck = await self.deck_repo.get_for_user(deck_id, user.id)
        if deck is None:
            raise NotFoundError(
                code=ErrorCode.DECK_NOT_FOUND,
                message="?????? ?? ??????.",
            )

        safe_limit = max(1, min(limit, self.MAX_PAGE_SIZE))
        safe_offset = max(0, offset)

        return await self.card_repo.list_for_deck(
            deck.id,
            status=status,
            search=search,
            limit=safe_limit,
            offset=safe_offset,
        )

    async def get_card(self, user: User, card_id: uuid.UUID) -> Card:
        """Fetch a single card for the user."""
        card = await self.card_repo.get_for_user(card_id, user.id)
        if card is None:
            raise NotFoundError(
                code=ErrorCode.CARD_NOT_FOUND,
                message="???????? ?? ????????.",
            )
        return card


__all__ = ["CardService"]
