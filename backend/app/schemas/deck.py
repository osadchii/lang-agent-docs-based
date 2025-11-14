"""Pydantic schemas describing deck endpoints."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class DeckSummary(BaseModel):
    """Lightweight deck representation for listing endpoints."""

    id: UUID
    profile_id: UUID
    name: str
    description: str | None
    is_active: bool
    is_group: bool
    owner_id: UUID | None
    owner_name: str | None
    cards_count: int
    new_cards_count: int
    due_cards_count: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DeckListResponse(BaseModel):
    """Response body for GET /api/decks."""

    data: list[DeckSummary]


__all__ = ["DeckListResponse", "DeckSummary"]
