"""Endpoints returning deck metadata for the Mini App."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.db import get_session
from app.models.deck import Deck
from app.models.user import User
from app.repositories.deck import DeckRepository
from app.schemas.deck import DeckListResponse, DeckSummary
from app.services.deck import DeckService

router = APIRouter(tags=["decks"])


def _owner_name(deck: Deck) -> str | None:
    owner: User | None = deck.owner
    if owner is None:
        return None
    for candidate in (owner.username, owner.first_name, owner.last_name):
        if candidate:
            return candidate
    return None


def _serialize_deck(deck: Deck) -> DeckSummary:
    return DeckSummary(
        id=deck.id,
        profile_id=deck.profile_id,
        name=deck.name,
        description=deck.description,
        is_active=deck.is_active,
        is_group=deck.is_group,
        owner_id=deck.owner_id,
        owner_name=_owner_name(deck),
        cards_count=deck.cards_count,
        new_cards_count=deck.new_cards_count,
        due_cards_count=deck.due_cards_count,
        created_at=deck.created_at,
        updated_at=deck.updated_at,
    )


async def get_deck_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> DeckService:
    repository = DeckRepository(session)
    return DeckService(repository)


@router.get(
    "/decks",
    response_model=DeckListResponse,
    summary="List decks for the active user",
)
async def list_decks(
    profile_id: Annotated[
        UUID | None,
        Query(
            default=None,
            description="Filter decks for a specific language profile.",
        ),
    ] = None,
    include_group: Annotated[
        bool,
        Query(
            default=True,
            description="Include decks shared with the user via groups.",
        ),
    ] = True,
    user: User = Depends(get_current_user),  # noqa: B008
    service: DeckService = Depends(get_deck_service),  # noqa: B008
) -> DeckListResponse:
    decks = await service.list_decks(user, profile_id=profile_id, include_group=include_group)
    data = [_serialize_deck(deck) for deck in decks]
    return DeckListResponse(data=data)


__all__ = ["get_deck_service", "router"]
