from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ErrorCode, NotFoundError
from app.models.deck import Deck
from app.models.group import Group, GroupMaterial, GroupMaterialType, GroupMember
from app.models.language_profile import LanguageProfile
from app.models.user import User
from app.repositories.deck import DeckRepository
from app.repositories.group import GroupMaterialRepository
from app.repositories.language_profile import LanguageProfileRepository
from app.services.deck import DeckService


async def _user(session: AsyncSession, *, telegram_id: int) -> User:
    now = datetime.now(tz=timezone.utc)
    user = User(
        id=uuid.uuid4(),
        telegram_id=telegram_id,
        first_name="DeckOwner",
        created_at=now,
        updated_at=now,
    )
    session.add(user)
    await session.flush()
    return user


async def _profile(session: AsyncSession, user: User) -> LanguageProfile:
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


def _deck(profile: LanguageProfile, owner: User, name: str) -> Deck:
    now = datetime.now(tz=timezone.utc)
    return Deck(
        id=uuid.uuid4(),
        profile_id=profile.id,
        name=name,
        owner_id=owner.id,
        created_at=now,
        updated_at=now,
    )


@pytest.mark.asyncio
async def test_list_decks_returns_owned_records(db_session: AsyncSession) -> None:
    user = await _user(db_session, telegram_id=111)
    profile = await _profile(db_session, user)

    deck = _deck(profile, user, "Default")
    db_session.add(deck)
    await db_session.flush()

    service = DeckService(DeckRepository(db_session))
    decks = await service.list_decks(user)
    assert len(decks) == 1
    assert decks[0].name == "Default"


@pytest.mark.asyncio
async def test_get_user_deck_raises_not_found_for_missing(db_session: AsyncSession) -> None:
    user = await _user(db_session, telegram_id=111)
    other_user = await _user(db_session, telegram_id=222)
    other_profile = await _profile(db_session, other_user)

    db_session.add(_deck(other_profile, other_user, "Foreign"))
    await db_session.flush()

    service = DeckService(DeckRepository(db_session))
    with pytest.raises(NotFoundError) as exc:
        await service.get_user_deck(user, uuid.uuid4())
    assert exc.value.code == ErrorCode.DECK_NOT_FOUND

    # Deck exists but belongs to another user
    foreign_deck = _deck(other_profile, other_user, "Group")
    db_session.add(foreign_deck)
    await db_session.flush()

    with pytest.raises(NotFoundError):
        await service.get_user_deck(user, foreign_deck.id)


@pytest.mark.asyncio
async def test_list_decks_includes_group_shared(db_session: AsyncSession) -> None:
    owner = await _user(db_session, telegram_id=333)
    member = await _user(db_session, telegram_id=444)
    owner_profile = await _profile(db_session, owner)
    await _profile(db_session, member)

    shared_deck = _deck(owner_profile, owner, "Shared")
    group = Group(owner_id=owner.id, name="Team")
    db_session.add_all([shared_deck, group])
    await db_session.flush()

    membership = GroupMember(group_id=group.id, user_id=member.id)
    material = GroupMaterial(
        group_id=group.id,
        material_id=shared_deck.id,
        material_type=GroupMaterialType.DECK,
    )
    db_session.add_all([membership, material])
    await db_session.flush()

    service = DeckService(DeckRepository(db_session)).with_group_access(
        GroupMaterialRepository(db_session),
        LanguageProfileRepository(db_session),
    )

    decks = await service.list_decks(member, include_group=True)
    assert any(deck.id == shared_deck.id for deck in decks)

    personal_only = await service.list_decks(member, include_group=False)
    assert all(deck.id != shared_deck.id for deck in personal_only)
