"""Schemas for card list/detail API responses."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.card import CardRating, CardStatus
from app.schemas.dialog import PaginationMeta


class CardResponse(BaseModel):
    """Single card representation exposed via the API."""

    id: UUID
    deck_id: UUID
    word: str
    translation: str
    example: str
    example_translation: str
    lemma: str
    notes: str | None
    status: CardStatus
    interval_days: int
    next_review: datetime
    reviews_count: int
    ease_factor: float
    last_rating: CardRating | None
    last_reviewed_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CardListResponse(BaseModel):
    """Response body for GET /api/cards."""

    data: list[CardResponse]
    pagination: PaginationMeta


__all__ = ["CardListResponse", "CardResponse"]
