from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ErrorCode, NotFoundError
from app.models.card import Card, CardStatus
from app.models.deck import Deck
from app.models.language_profile import LanguageProfile
from app.models.user import User
from app.repositories.card import CardRepository
from app.repositories.deck import DeckRepository
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
