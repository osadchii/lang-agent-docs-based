from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ErrorCode, NotFoundError
from app.models.card import Card, CardRating, CardReview, CardStatus
from app.models.deck import Deck
from app.models.language_profile import LanguageProfile
from app.models.user import User
from app.repositories.card import CardRepository, CardReviewRepository
from app.repositories.deck import DeckRepository
from app.repositories.language_profile import LanguageProfileRepository
from app.schemas.card import CardCreateRequest, RateCardRequest
from app.schemas.llm_responses import CardContent
from app.services.card import CardService


async def _user(session: AsyncSession, *, telegram_id: int) -> User:
    now = datetime.now(tz=timezone.utc)
    user = User(
        id=uuid.uuid4(),
        telegram_id=telegram_id,
        first_name=f"User{telegram_id}",
        created_at=now,
        updated_at=now,
    )
    session.add(user)
    await session.flush()
    return user


async def _profile(session: AsyncSession, *, user: User) -> LanguageProfile:
    now = datetime.now(tz=timezone.utc)
    profile = LanguageProfile(
        id=uuid.uuid4(),
        user_id=user.id,
        language="es",
        language_name="Spanish",
        current_level="A1",
        target_level="A1",
        goals=["travel"],
        interface_language="ru",
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    session.add(profile)
    await session.flush()
    return profile


async def _deck(session: AsyncSession, *, profile: LanguageProfile, owner: User) -> Deck:
    now = datetime.now(tz=timezone.utc)
    deck = Deck(
        id=uuid.uuid4(),
        profile_id=profile.id,
        name="Starter",
        owner_id=owner.id,
        created_at=now,
        updated_at=now,
    )
    session.add(deck)
    await session.flush()
    return deck


def _card(deck: Deck, *, word: str) -> Card:
    now = datetime.now(tz=timezone.utc)
    return Card(
        id=uuid.uuid4(),
        deck_id=deck.id,
        word=word,
        translation="дом",
        example="Mi casa es tu casa",
        example_translation="Мой дом - твой дом",
        lemma=word,
        status=CardStatus.NEW,
        interval_days=0,
        next_review=now + timedelta(days=1),
        reviews_count=0,
        ease_factor=2.5,
        created_at=now,
        updated_at=now,
    )


def _service(session: AsyncSession) -> CardService:
    return CardService(CardRepository(session), DeckRepository(session))


def _service_full(session: AsyncSession) -> CardService:
    return CardService(
        CardRepository(session),
        DeckRepository(session),
        LanguageProfileRepository(session),
        CardReviewRepository(session),
    )


class _LLMStub:
    def __init__(self, *, fail_on: set[str] | None = None) -> None:
        self.generated: list[str] = []
        self.fail_on = fail_on or set()

    async def generate_card(
        self,
        *,
        word: str,
        language: str,
        language_name: str,
        level: str,
        goals: list[str],
    ) -> tuple[CardContent, SimpleNamespace]:
        if word in self.fail_on:
            raise ValueError("LLM failed")
        self.generated.append(word)
        content = CardContent(
            word=word,
            lemma=word.lower(),
            translation=f"{word}-tr",
            example=f"{word} example",
            example_translation=f"{word} example tr",
            notes=None,
        )
        usage = SimpleNamespace(
            prompt_tokens=0,
            completion_tokens=0,
            total_tokens=0,
            estimated_cost=0.0,
        )
        return content, usage

    async def track_token_usage(self, **_: object) -> None:
        return None


@pytest.mark.asyncio
async def test_list_cards_returns_paginated_results(db_session: AsyncSession) -> None:
    user = await _user(db_session, telegram_id=1)
    profile = await _profile(db_session, user=user)
    deck = await _deck(db_session, profile=profile, owner=user)

    card = _card(deck, word="casa")
    db_session.add(card)
    await db_session.flush()

    service = _service(db_session)
    cards, total = await service.list_cards(user, deck_id=deck.id, status=None, search=None)

    assert total == 1
    assert cards[0].id == card.id


@pytest.mark.asyncio
async def test_list_cards_raises_for_foreign_deck(db_session: AsyncSession) -> None:
    owner = await _user(db_session, telegram_id=1)
    other = await _user(db_session, telegram_id=2)
    owner_profile = await _profile(db_session, user=owner)
    other_profile = await _profile(db_session, user=other)
    owner_deck = await _deck(db_session, profile=owner_profile, owner=owner)
    await _deck(db_session, profile=other_profile, owner=other)

    service = _service(db_session)
    with pytest.raises(NotFoundError) as exc:
        await service.list_cards(other, deck_id=owner_deck.id)

    assert exc.value.code == ErrorCode.DECK_NOT_FOUND


@pytest.mark.asyncio
async def test_get_card_checks_ownership(db_session: AsyncSession) -> None:
    owner = await _user(db_session, telegram_id=1)
    other = await _user(db_session, telegram_id=2)
    profile = await _profile(db_session, user=owner)
    deck = await _deck(db_session, profile=profile, owner=owner)
    card = _card(deck, word="viajar")
    db_session.add(card)
    await db_session.flush()

    service = _service(db_session)
    assert await service.get_card(owner, card.id)

    with pytest.raises(NotFoundError) as exc:
        await service.get_card(other, card.id)
    assert exc.value.code == ErrorCode.CARD_NOT_FOUND


@pytest.mark.asyncio
async def test_get_next_card_prefers_due_cards(db_session: AsyncSession) -> None:
    user = await _user(db_session, telegram_id=1)
    profile = await _profile(db_session, user=user)
    deck = await _deck(db_session, profile=profile, owner=user)

    due_card = _card(deck, word="overdue")
    due_card.status = CardStatus.REVIEW
    due_card.next_review = datetime.now(tz=timezone.utc) - timedelta(days=1)

    new_card = _card(deck, word="fresh")
    new_card.status = CardStatus.NEW
    new_card.next_review = datetime.now(tz=timezone.utc) + timedelta(days=1)

    db_session.add_all([due_card, new_card])
    await db_session.flush()

    service = _service_full(db_session)
    next_card = await service.get_next_card(user, deck_id=deck.id)

    assert next_card is not None
    assert next_card.id == due_card.id


@pytest.mark.asyncio
async def test_rate_card_updates_interval_and_records_review(db_session: AsyncSession) -> None:
    user = await _user(db_session, telegram_id=1)
    profile = await _profile(db_session, user=user)
    deck = await _deck(db_session, profile=profile, owner=user)
    deck.is_active = True

    card = _card(deck, word="aprender")
    card.status = CardStatus.LEARNING
    card.interval_days = 3
    db_session.add(card)
    await db_session.flush()

    service = _service_full(db_session)
    payload = RateCardRequest(card_id=card.id, rating=CardRating.KNOW, duration_seconds=25)
    updated = await service.rate_card(user, payload)

    assert updated.reviews_count == 1
    assert updated.interval_days == round(3 * service.INTERVAL_MULTIPLIER)
    assert updated.last_rating == CardRating.KNOW

    reviews = await db_session.execute(select(CardReview).where(CardReview.card_id == card.id))
    assert len(reviews.scalars().all()) == 1


@pytest.mark.asyncio
async def test_create_cards_skips_duplicates(db_session: AsyncSession) -> None:
    user = await _user(db_session, telegram_id=1)
    profile = await _profile(db_session, user=user)
    deck = await _deck(db_session, profile=profile, owner=user)

    service = _service_full(db_session)
    llm_stub = _LLMStub()
    payload = CardCreateRequest(deck_id=deck.id, words=["casa", "casa"])

    result = await service.create_cards(user, payload, llm_service=llm_stub)

    await db_session.refresh(deck)
    assert len(result.created) == 1
    assert result.duplicates == ["casa"]
    assert deck.new_cards_count == 1


@pytest.mark.asyncio
async def test_create_cards_records_failures(db_session: AsyncSession) -> None:
    user = await _user(db_session, telegram_id=5)
    profile = await _profile(db_session, user=user)
    deck = await _deck(db_session, profile=profile, owner=user)

    service = _service_full(db_session)
    llm_stub = _LLMStub(fail_on={"fallar"})
    payload = CardCreateRequest(deck_id=deck.id, words=["bien", "fallar"])

    result = await service.create_cards(user, payload, llm_service=llm_stub)
    await db_session.refresh(deck)

    assert [card.word for card in result.created] == ["bien"]
    assert result.failed == ["fallar"]
    assert deck.cards_count == 1


@pytest.mark.asyncio
async def test_get_next_card_uses_active_profile(db_session: AsyncSession) -> None:
    user = await _user(db_session, telegram_id=6)
    profile = await _profile(db_session, user=user)
    deck = await _deck(db_session, profile=profile, owner=user)
    deck.is_active = True

    due_card = _card(deck, word="activo")
    due_card.next_review = datetime.now(tz=timezone.utc) - timedelta(minutes=1)
    db_session.add(due_card)
    await db_session.flush()

    service = _service_full(db_session)
    next_card = await service.get_next_card(user)

    assert next_card is not None
    assert next_card.id == due_card.id


@pytest.mark.asyncio
async def test_get_next_card_returns_none_without_profile_repo(db_session: AsyncSession) -> None:
    user = await _user(db_session, telegram_id=7)
    service = CardService(CardRepository(db_session), DeckRepository(db_session))
    assert await service.get_next_card(user) is None


@pytest.mark.asyncio
async def test_create_cards_requires_profile_repo(db_session: AsyncSession) -> None:
    user = await _user(db_session, telegram_id=8)
    service = CardService(CardRepository(db_session), DeckRepository(db_session))
    payload = CardCreateRequest(deck_id=uuid.uuid4(), words=["casa"])

    with pytest.raises(RuntimeError):
        await service.create_cards(user, payload, llm_service=_LLMStub())


@pytest.mark.asyncio
async def test_rate_card_requires_review_repo(db_session: AsyncSession) -> None:
    user = await _user(db_session, telegram_id=9)
    service = CardService(CardRepository(db_session), DeckRepository(db_session))
    payload = RateCardRequest(card_id=uuid.uuid4(), rating=CardRating.KNOW)

    with pytest.raises(RuntimeError):
        await service.rate_card(user, payload)
