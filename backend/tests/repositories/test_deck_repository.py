from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.deck import Deck
from app.models.language_profile import LanguageProfile
from app.models.user import User
from app.repositories.deck import DeckRepository


async def _create_user(session: AsyncSession, *, telegram_id: int = 100) -> User:
    now = datetime.now(tz=timezone.utc)
    user = User(
        id=uuid.uuid4(),
        telegram_id=telegram_id,
        first_name="Test",
        created_at=now,
        updated_at=now,
    )
    session.add(user)
    await session.flush()
    return user


async def _create_profile(
    session: AsyncSession,
    *,
    user: User,
    language: str = "es",
) -> LanguageProfile:
    now = datetime.now(tz=timezone.utc)
    profile = LanguageProfile(
        id=uuid.uuid4(),
        user_id=user.id,
        language=language,
        language_name="Test Language",
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


def _deck(
    *,
    profile: LanguageProfile,
    owner: User,
    name: str,
    is_group: bool = False,
) -> Deck:
    now = datetime.now(tz=timezone.utc)
    return Deck(
        id=uuid.uuid4(),
        profile_id=profile.id,
        name=name,
        description=None,
        is_group=is_group,
        owner_id=owner.id,
        created_at=now,
        updated_at=now,
    )


@pytest.mark.asyncio
async def test_list_for_user_filters_by_profile(db_session: AsyncSession) -> None:
    repo = DeckRepository(db_session)
    user = await _create_user(db_session, telegram_id=1)
    other_user = await _create_user(db_session, telegram_id=2)
    profile = await _create_profile(db_session, user=user, language="es")
    other_profile = await _create_profile(db_session, user=other_user, language="de")

    deck = _deck(profile=profile, owner=user, name="Spanish A1")
    foreign = _deck(profile=other_profile, owner=other_user, name="German")
    db_session.add_all([deck, foreign])
    await db_session.flush()

    decks = await repo.list_for_user(user.id, profile_id=profile.id)

    assert [item.id for item in decks] == [deck.id]


@pytest.mark.asyncio
async def test_list_for_user_can_exclude_group_decks(db_session: AsyncSession) -> None:
    repo = DeckRepository(db_session)
    user = await _create_user(db_session, telegram_id=1)
    profile = await _create_profile(db_session, user=user)

    solo = _deck(profile=profile, owner=user, name="Solo deck", is_group=False)
    shared = _deck(profile=profile, owner=user, name="Group deck", is_group=True)
    db_session.add_all([solo, shared])
    await db_session.flush()

    decks = await repo.list_for_user(user.id, include_group=False)

    assert len(decks) == 1
    assert decks[0].id == solo.id


@pytest.mark.asyncio
async def test_get_for_user_returns_none_for_foreign_deck(db_session: AsyncSession) -> None:
    repo = DeckRepository(db_session)
    owner = await _create_user(db_session, telegram_id=1)
    outsider = await _create_user(db_session, telegram_id=2)
    profile = await _create_profile(db_session, user=owner)
    deck = _deck(profile=profile, owner=owner, name="Spanish A2")
    db_session.add(deck)
    await db_session.flush()

    assert await repo.get_for_user(deck.id, owner.id)
    assert await repo.get_for_user(deck.id, outsider.id) is None
