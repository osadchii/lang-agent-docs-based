"""Schemas for card list/detail API responses."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

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


class CardCreateRequest(BaseModel):
    """Request payload for creating one or more cards."""

    deck_id: UUID = Field(description="Target deck identifier")
    words: list[str] = Field(
        min_length=1,
        max_length=20,
        description="List of words or phrases to turn into flashcards.",
    )

    @model_validator(mode="after")
    def _normalize_words(self) -> "CardCreateRequest":
        normalized = [word.strip() for word in self.words if word.strip()]
        if not normalized:
            raise ValueError("At least one non-empty word is required")
        if len(normalized) > 20:
            raise ValueError("A maximum of 20 words can be created at once")
        object.__setattr__(self, "words", normalized)
        return self


class CardCreateResult(BaseModel):
    """Result of card creation attempt including duplicates or failures."""

    created: list[CardResponse] = Field(default_factory=list)
    duplicates: list[str] = Field(default_factory=list)
    failed: list[str] = Field(default_factory=list)


class NextCardResponse(BaseModel):
    """Next card returned for study flow."""

    id: UUID
    deck_id: UUID
    word: str
    translation: str
    example: str
    example_translation: str
    status: CardStatus
    next_review: datetime

    model_config = ConfigDict(from_attributes=True)


class RateCardRequest(BaseModel):
    """Rating payload for spaced-repetition session."""

    card_id: UUID
    rating: CardRating
    duration_seconds: int | None = Field(
        default=None, ge=0, description="Optional time spent on the card in seconds."
    )


class RateCardResponse(BaseModel):
    """Updated scheduling information after rating a card."""

    id: UUID
    status: CardStatus
    interval_days: int
    next_review: datetime
    reviews_count: int
    last_rating: CardRating
    last_reviewed_at: datetime

    model_config = ConfigDict(from_attributes=True)


__all__ = [
    "CardCreateRequest",
    "CardCreateResult",
    "CardListResponse",
    "CardResponse",
    "NextCardResponse",
    "RateCardRequest",
    "RateCardResponse",
]
