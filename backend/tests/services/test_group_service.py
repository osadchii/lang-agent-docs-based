from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ApplicationError, ErrorCode
from app.models.deck import Deck
from app.models.group import GroupInviteStatus, GroupMaterialType, GroupRole
from app.models.language_profile import LanguageProfile
from app.models.user import User
from app.repositories.deck import DeckRepository
from app.repositories.group import (
    GroupInviteRepository,
    GroupMaterialRepository,
    GroupMemberRepository,
    GroupRepository,
)
from app.repositories.topic import TopicRepository
from app.repositories.user import UserRepository
from app.services.group import GroupService


def _user(username: str, telegram_id: int) -> User:
    return User(
        id=uuid.uuid4(),
        telegram_id=telegram_id,
        first_name=username.title(),
        username=username,
        language_code="ru",
    )


def _profile(owner: User) -> LanguageProfile:
    return LanguageProfile(
        id=uuid.uuid4(),
        user_id=owner.id,
        language="es",
        language_name="Spanish",
        current_level="A2",
        target_level="B1",
        goals=["travel"],
        interface_language="ru",
    )


def _service(db_session: AsyncSession) -> GroupService:
    return GroupService(
        GroupRepository(db_session),
        GroupMemberRepository(db_session),
        GroupInviteRepository(db_session),
        GroupMaterialRepository(db_session),
        UserRepository(db_session),
        DeckRepository(db_session),
        TopicRepository(db_session),
    )


@pytest.mark.asyncio
async def test_group_service_invite_and_share_materials(db_session: AsyncSession) -> None:
    owner = _user("sensei", 123456789)
    member = _user("learner", 987654321)
    newcomer = _user("alex", 222222222)
    profile = _profile(owner)
    deck = Deck(
        id=uuid.uuid4(),
        profile_id=profile.id,
        name="Daily practice",
        description=None,
        owner_id=owner.id,
    )

    db_session.add_all([owner, member, newcomer, profile, deck])
    await db_session.flush()

    service = _service(db_session)
    group = await service.create_group(owner, "Команда", description=None)
    invite = await service.invite_member(owner, group.id, f"@{member.username}")
    acceptance = await service.accept_invite(member, invite.id)

    assert acceptance.role == GroupRole.MEMBER
    assert group.members_count == 2

    batch = await service.add_materials(
        owner,
        group.id,
        material_type=GroupMaterialType.DECK,
        material_ids=[deck.id],
    )
    assert batch.added[0].id == deck.id

    shared_for_member = await service.list_materials(member, group.id)
    assert shared_for_member and shared_for_member[0].name == deck.name

    shared_decks = await service.material_repo.list_shared_decks_for_user(member.id)
    assert shared_decks and shared_decks[0].id == deck.id

    owner_groups = await service.list_groups(owner)
    member_groups = await service.list_groups(member)
    assert owner_groups[0].role == GroupRole.OWNER
    assert member_groups[0].role == GroupRole.MEMBER

    members = await service.list_members(owner, group.id)
    assert len(members) == 2

    pending = await service.invite_member(owner, group.id, newcomer.username)
    await service.cancel_invite(owner, pending.id)

    second_invite = await service.invite_member(owner, group.id, f"@{newcomer.username}")
    await service.decline_invite(newcomer, second_invite.id)

    await service.remove_material(
        owner,
        group.id,
        material_id=deck.id,
        material_type=GroupMaterialType.DECK,
    )
    assert await service.list_materials(member, group.id) == []
    counts = await service.count_materials([group.id])
    assert counts.get(group.id, 0) == 0

    await service.leave_group(member, group.id)
    remaining_members = await service.list_members(owner, group.id)
    assert len(remaining_members) == 1


@pytest.mark.asyncio
async def test_create_group_enforces_free_limit(db_session: AsyncSession) -> None:
    user = _user("limit", 333333333)
    db_session.add(user)
    await db_session.flush()

    service = _service(db_session)

    await service.create_group(user, "First")
    with pytest.raises(ApplicationError):
        await service.create_group(user, "Second")


@pytest.mark.asyncio
async def test_resolve_identifier_supports_multiple_formats(db_session: AsyncSession) -> None:
    user = _user("identifier", 444444444)
    db_session.add(user)
    await db_session.flush()

    service = _service(db_session)

    resolved_username = await service._resolve_identifier(f"@{user.username}")
    resolved_link = await service._resolve_identifier(f"https://t.me/{user.username}")
    resolved_id = await service._resolve_identifier(str(user.telegram_id))

    assert resolved_username.id == user.id
    assert resolved_link.id == user.id
    assert resolved_id.id == user.id


@pytest.mark.asyncio
async def test_create_group_rejects_blank_name(db_session: AsyncSession) -> None:
    user = _user("blank", 555555555)
    db_session.add(user)
    await db_session.flush()

    service = _service(db_session)

    with pytest.raises(ApplicationError) as excinfo:
        await service.create_group(user, "   ")

    assert excinfo.value.code == ErrorCode.VALIDATION_ERROR


@pytest.mark.asyncio
async def test_update_group_rejects_invalid_name(db_session: AsyncSession) -> None:
    user = _user("updater", 666666666)
    db_session.add(user)
    await db_session.flush()

    service = _service(db_session)
    group = await service.create_group(user, "Valid")

    with pytest.raises(ApplicationError):
        await service.update_group(user, group.id, name="<>")


@pytest.mark.asyncio
async def test_owner_cannot_leave_group(db_session: AsyncSession) -> None:
    owner = _user("boss", 777777777)
    db_session.add(owner)
    await db_session.flush()

    service = _service(db_session)
    group = await service.create_group(owner, "Team")

    with pytest.raises(ApplicationError) as excinfo:
        await service.leave_group(owner, group.id)

    assert excinfo.value.code == ErrorCode.OWNER_CANNOT_LEAVE


@pytest.mark.asyncio
async def test_accept_invite_marks_expired_requests(db_session: AsyncSession) -> None:
    owner = _user("sensei", 888888888)
    invitee = _user("latecomer", 999999999)
    db_session.add_all([owner, invitee])
    await db_session.flush()

    service = _service(db_session)
    group = await service.create_group(owner, "Circle")
    invite = await service.invite_member(owner, group.id, f"@{invitee.username}")
    invite.expires_at = datetime.now(tz=timezone.utc) - timedelta(days=1)
    await db_session.flush()

    with pytest.raises(ApplicationError) as excinfo:
        await service.accept_invite(invitee, invite.id)

    assert excinfo.value.code == ErrorCode.INVITE_EXPIRED
    assert invite.status == GroupInviteStatus.EXPIRED
