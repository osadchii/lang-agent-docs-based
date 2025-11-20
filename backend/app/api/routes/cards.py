"""Card endpoints powering Mini App study screens."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Path, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import build_enhanced_llm_service, get_cache_client
from app.core.auth import get_current_user
from app.core.cache import CacheClient
from app.core.db import get_session
from app.models.card import Card, CardStatus
from app.models.user import User
from app.repositories.card import CardRepository, CardReviewRepository
from app.repositories.deck import DeckRepository
from app.repositories.language_profile import LanguageProfileRepository
from app.schemas.card import (
    CardCreateRequest,
    CardCreateResult,
    CardListResponse,
    CardResponse,
    NextCardResponse,
    RateCardRequest,
    RateCardResponse,
)
from app.schemas.dialog import PaginationMeta
from app.services.card import CardService
from app.services.llm_enhanced import EnhancedLLMService

router = APIRouter(tags=["cards"])


def _serialize_card(card: Card) -> CardResponse:
    return CardResponse(
        id=card.id,
        deck_id=card.deck_id,
        word=card.word,
        translation=card.translation,
        example=card.example,
        example_translation=card.example_translation,
        lemma=card.lemma,
        notes=card.notes,
        status=card.status,
        interval_days=card.interval_days,
        next_review=card.next_review,
        reviews_count=card.reviews_count,
        ease_factor=float(card.ease_factor),
        last_rating=card.last_rating,
        last_reviewed_at=card.last_reviewed_at,
        created_at=card.created_at,
        updated_at=card.updated_at,
    )


def _serialize_next_card(card: Card) -> NextCardResponse:
    return NextCardResponse(
        id=card.id,
        deck_id=card.deck_id,
        word=card.word,
        translation=card.translation,
        example=card.example,
        example_translation=card.example_translation,
        status=card.status,
        next_review=card.next_review,
    )


async def get_card_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> CardService:
    card_repo = CardRepository(session)
    deck_repo = DeckRepository(session)
    profile_repo = LanguageProfileRepository(session)
    review_repo = CardReviewRepository(session)
    return CardService(card_repo, deck_repo, profile_repo, review_repo)


async def get_llm_service(
    cache: CacheClient = Depends(get_cache_client),  # noqa: B008
) -> EnhancedLLMService:
    """Provide enhanced LLM service with shared cache client."""
    return build_enhanced_llm_service(cache)


@router.get(
    "/cards",
    response_model=CardListResponse,
    summary="List cards for a deck",
)
async def list_cards(
    deck_id: Annotated[UUID, Query(description="Deck identifier")],
    status: Annotated[
        CardStatus | None,
        Query(description="Filter by spaced-repetition status."),
    ] = None,
    search: Annotated[
        str | None,
        Query(
            min_length=1,
            max_length=200,
            description="Case-insensitive substring filter for word/translation/lemma.",
        ),
    ] = None,
    limit: Annotated[
        int,
        Query(
            ge=1,
            le=100,
            description="Maximum cards to fetch.",
        ),
    ] = 20,
    offset: Annotated[
        int,
        Query(
            ge=0,
            description="Number of cards to skip.",
        ),
    ] = 0,
    user: User = Depends(get_current_user),  # noqa: B008
    service: CardService = Depends(get_card_service),  # noqa: B008
) -> CardListResponse:
    cards, total = await service.list_cards(
        user,
        deck_id=deck_id,
        status=status,
        search=search,
        limit=limit,
        offset=offset,
    )
    data = [_serialize_card(card) for card in cards]
    has_more = offset + limit < total
    pagination = PaginationMeta(
        limit=limit,
        offset=offset,
        count=total,
        has_more=has_more,
        next_offset=(offset + limit) if has_more else None,
    )
    return CardListResponse(data=data, pagination=pagination)


@router.post(
    "/cards",
    response_model=CardCreateResult,
    status_code=status.HTTP_201_CREATED,
    summary="Create one or more cards using LLM",
)
async def create_cards(
    payload: CardCreateRequest,
    user: User = Depends(get_current_user),  # noqa: B008
    service: CardService = Depends(get_card_service),  # noqa: B008
    llm_service: EnhancedLLMService = Depends(get_llm_service),  # noqa: B008
) -> CardCreateResult:
    result = await service.create_cards(user, payload, llm_service=llm_service)
    return result


@router.get(
    "/cards/next",
    response_model=NextCardResponse,
    responses={status.HTTP_204_NO_CONTENT: {"description": "No cards to study"}},
    summary="Fetch the next due card for study",
)
async def next_card(
    deck_id: Annotated[UUID | None, Query(description="Deck identifier (optional)")] = None,
    user: User = Depends(get_current_user),  # noqa: B008
    service: CardService = Depends(get_card_service),  # noqa: B008
) -> NextCardResponse | Response:
    card = await service.get_next_card(user, deck_id=deck_id)
    if card is None:
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    return _serialize_next_card(card)


@router.post(
    "/cards/rate",
    response_model=RateCardResponse,
    summary="Rate a card after reviewing it",
)
async def rate_card(
    payload: RateCardRequest,
    user: User = Depends(get_current_user),  # noqa: B008
    service: CardService = Depends(get_card_service),  # noqa: B008
) -> RateCardResponse:
    card = await service.rate_card(user, payload)
    last_rating = card.last_rating or payload.rating
    last_reviewed_at = card.last_reviewed_at or card.next_review
    return RateCardResponse(
        id=card.id,
        status=card.status,
        interval_days=card.interval_days,
        next_review=card.next_review,
        reviews_count=card.reviews_count,
        last_rating=last_rating,
        last_reviewed_at=last_reviewed_at,
    )


@router.get(
    "/cards/{card_id}",
    response_model=CardResponse,
    summary="Fetch a single card",
)
async def get_card(
    card_id: Annotated[UUID, Path(description="Card identifier")],
    user: User = Depends(get_current_user),  # noqa: B008
    service: CardService = Depends(get_card_service),  # noqa: B008
) -> CardResponse:
    card = await service.get_card(user, card_id)
    return _serialize_card(card)


__all__ = ["get_card_service", "get_llm_service", "router"]
