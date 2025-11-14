from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.card import Card, CardStatus
from app.models.deck import Deck
from app.models.language_profile import LanguageProfile
from app.models.user import User
from app.repositories.card import CardRepository


async def _create_user(session: AsyncSession, *, telegram_id: int = 100) -> User:
    now = datetime.now(tz=timezone.utc)
    instance = User(
        id=uuid.uuid4(),
        telegram_id=telegram_id,
        first_name="Tester",
        created_at=now,
        updated_at=now,
    )
    session.add(instance)
    await session.flush()
    return instance


async def _create_profile(session: AsyncSession, user: User) -> LanguageProfile:
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


async def _create_deck(session: AsyncSession, *, profile: LanguageProfile, owner: User) -> Deck:
    now = datetime.now(tz=timezone.utc)
    deck = Deck(
        id=uuid.uuid4(),
        profile_id=profile.id,
        name="Everyday",
        owner_id=owner.id,
        created_at=now,
        updated_at=now,
    )
    session.add(deck)
    await session.flush()
    return deck


def _card(deck: Deck, *, word: str, status: CardStatus) -> Card:
    now = datetime.now(tz=timezone.utc)
    return Card(
        id=uuid.uuid4(),
        deck_id=deck.id,
        word=word,
        translation="дом",
        example="Mi casa es tu casa",
        example_translation="Мой дом - твой дом",
        lemma=word,
        status=status,
        interval_days=0,
        next_review=now + timedelta(days=1),
        reviews_count=0,
        ease_factor=2.5,
        created_at=now,
        updated_at=now,
    )


@pytest.mark.asyncio
async def test_list_for_deck_supports_filters(db_session: AsyncSession) -> None:
    repo = CardRepository(db_session)
    owner = await _create_user(db_session, telegram_id=1)
    profile = await _create_profile(db_session, owner)
    deck = await _create_deck(db_session, profile=profile, owner=owner)

    new_card = _card(deck, word="casa", status=CardStatus.NEW)
    review_card = _card(deck, word="volver", status=CardStatus.REVIEW)
    db_session.add_all([new_card, review_card])
    await db_session.flush()

    cards, total = await repo.list_for_deck(deck.id, status=CardStatus.NEW)
    assert total == 1
    assert cards[0].id == new_card.id

    cards, total = await repo.list_for_deck(deck.id, search="volv")
    assert total == 1
    assert cards[0].id == review_card.id


@pytest.mark.asyncio
async def test_get_for_user_verifies_ownership(db_session: AsyncSession) -> None:
    repo = CardRepository(db_session)
    owner = await _create_user(db_session, telegram_id=1)
    outsider = await _create_user(db_session, telegram_id=2)
    profile = await _create_profile(db_session, owner)
    deck = await _create_deck(db_session, profile=profile, owner=owner)

    card = _card(deck, word="gato", status=CardStatus.NEW)
    db_session.add(card)
    await db_session.flush()

    assert await repo.get_for_user(card.id, owner.id)
    assert await repo.get_for_user(card.id, outsider.id) is None
