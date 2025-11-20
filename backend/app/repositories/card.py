"""Repositories for card and review persistence."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import selectinload

from app.models.card import Card, CardRating, CardReview, CardStatus
from app.models.deck import Deck
from app.models.language_profile import LanguageProfile
from app.repositories.base import BaseRepository


class CardRepository(BaseRepository[Card]):
    """Query helpers for Card entities."""

    async def list_for_deck(
        self,
        deck_id: uuid.UUID,
        *,
        status: CardStatus | None = None,
        search: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[Card], int]:
        stmt: Select[tuple[Card]] = (
            select(Card)
            .options(selectinload(Card.reviews))
            .where(Card.deck_id == deck_id, Card.deleted.is_(False))
            .order_by(Card.created_at.desc())
            .limit(limit)
            .offset(offset)
        )

        count_stmt = select(func.count()).where(
            Card.deck_id == deck_id,
            Card.deleted.is_(False),
        )

        if status is not None:
            stmt = stmt.where(Card.status == status)
            count_stmt = count_stmt.where(Card.status == status)

        if search:
            pattern = f"%{search.lower()}%"
            clause = or_(
                func.lower(Card.word).like(pattern),
                func.lower(Card.translation).like(pattern),
                func.lower(Card.lemma).like(pattern),
            )
            stmt = stmt.where(clause)
            count_stmt = count_stmt.where(clause)

        result = await self.session.execute(stmt)
        cards = list(result.scalars().unique())

        total_result = await self.session.execute(count_stmt)
        total = int(total_result.scalar_one())
        return cards, total

    async def find_by_lemma(self, deck_id: uuid.UUID, lemma: str) -> Card | None:
        """Return a single card by lemma within the deck to prevent duplicates."""
        stmt = (
            select(Card)
            .where(
                Card.deck_id == deck_id,
                Card.deleted.is_(False),
                func.lower(Card.lemma) == lemma.lower(),
            )
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_next_for_deck(self, deck_id: uuid.UUID) -> Card | None:
        """Return the next card for study: due first, then the oldest new one."""
        now = datetime.now(timezone.utc)

        due_stmt = (
            select(Card)
            .where(
                Card.deck_id == deck_id,
                Card.deleted.is_(False),
                Card.next_review <= now,
            )
            .order_by(Card.next_review.asc())
            .limit(1)
        )
        due_result = await self.session.execute(due_stmt)
        due_card = due_result.scalar_one_or_none()
        if due_card:
            return due_card

        new_stmt = (
            select(Card)
            .where(
                Card.deck_id == deck_id,
                Card.deleted.is_(False),
                Card.status == CardStatus.NEW,
            )
            .order_by(Card.created_at.asc())
            .limit(1)
        )
        new_result = await self.session.execute(new_stmt)
        return new_result.scalar_one_or_none()

    async def get_for_user(self, card_id: uuid.UUID, user_id: uuid.UUID) -> Card | None:
        stmt = (
            select(Card)
            .join(Deck, Card.deck_id == Deck.id)
            .join(LanguageProfile, Deck.profile_id == LanguageProfile.id)
            .options(selectinload(Card.reviews))
            .where(
                Card.id == card_id,
                Card.deleted.is_(False),
                Deck.deleted.is_(False),
                LanguageProfile.deleted.is_(False),
                LanguageProfile.user_id == user_id,
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_lemmas_for_profile(self, profile_id: uuid.UUID, limit: int = 200) -> list[str]:
        """Return recent lemmas for a profile to avoid duplicate suggestions."""
        safe_limit = max(1, limit)
        stmt = (
            select(Card.lemma)
            .join(Deck, Card.deck_id == Deck.id)
            .where(
                Deck.profile_id == profile_id,
                Deck.deleted.is_(False),
                Card.deleted.is_(False),
            )
            .order_by(Card.created_at.desc())
            .limit(safe_limit)
        )
        result = await self.session.execute(stmt)
        return [row[0] for row in result.all()]

    async def counters_for_deck(self, deck_id: uuid.UUID) -> tuple[int, int, int]:
        """Return total, new, and due counters for the deck."""
        now = datetime.now(timezone.utc)
        stmt = select(
            func.count(),
            func.count().filter(Card.status == CardStatus.NEW),
            func.count().filter(Card.next_review <= now),
        ).where(Card.deck_id == deck_id, Card.deleted.is_(False))

        result = await self.session.execute(stmt)
        total, new_count, due_count = result.one()
        return int(total or 0), int(new_count or 0), int(due_count or 0)


class CardReviewRepository(BaseRepository[CardReview]):
    """Basic helper for review history storage."""

    async def record_review(
        self,
        *,
        card_id: uuid.UUID,
        user_id: uuid.UUID,
        rating: CardRating,
        interval_before: int,
        interval_after: int,
        duration_seconds: int | None = None,
    ) -> CardReview:
        review = CardReview(
            card_id=card_id,
            user_id=user_id,
            rating=rating,
            interval_before=interval_before,
            interval_after=interval_after,
            duration_seconds=duration_seconds,
        )
        await self.add(review)
        return review


__all__ = ["CardRepository", "CardReviewRepository"]
