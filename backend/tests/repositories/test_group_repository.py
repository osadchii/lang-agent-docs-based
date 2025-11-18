from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.group import (
    Group,
    GroupInvite,
    GroupInviteStatus,
    GroupMaterial,
    GroupMaterialType,
    GroupMember,
)
from app.models.user import User
from app.repositories.group import GroupInviteRepository, GroupMaterialRepository, GroupRepository


def _user(telegram_id: int) -> User:
    now = datetime.now(tz=timezone.utc)
    return User(
        id=uuid.uuid4(),
        telegram_id=telegram_id,
        first_name=f"user-{telegram_id}",
        created_at=now,
        updated_at=now,
    )


@pytest.mark.asyncio
async def test_group_repository_lists_owner_and_members(db_session: AsyncSession) -> None:
    owner = _user(1001)
    member = _user(1002)
    group = Group(owner_id=owner.id, name="RepoGroup")
    db_session.add_all([owner, member, group])
    await db_session.flush()

    membership = GroupMember(group_id=group.id, user_id=member.id)
    db_session.add(membership)
    await db_session.flush()

    repo = GroupRepository(db_session)
    owner_groups = await repo.list_owned(owner.id)
    member_groups = await repo.list_member_of(member.id)

    assert owner_groups and owner_groups[0].id == group.id
    assert member_groups and member_groups[0].id == group.id


@pytest.mark.asyncio
async def test_group_material_repository_counts_and_exists(db_session: AsyncSession) -> None:
    owner = _user(1101)
    group = Group(owner_id=owner.id, name="Materials")
    db_session.add_all([owner, group])
    await db_session.flush()

    material = GroupMaterial(
        group_id=group.id,
        material_id=uuid.uuid4(),
        material_type=GroupMaterialType.DECK,
    )
    db_session.add(material)
    await db_session.flush()

    repo = GroupMaterialRepository(db_session)
    rows = await repo.list_for_group(group.id)
    counts = await repo.count_for_groups([group.id])
    exists = await repo.exists_for_material(material.material_id, GroupMaterialType.DECK)

    assert rows and rows[0].material_id == material.material_id
    assert counts[group.id] == 1
    assert exists is True


@pytest.mark.asyncio
async def test_group_invite_repository_returns_pending(db_session: AsyncSession) -> None:
    owner = _user(1201)
    invitee = _user(1202)
    group = Group(owner_id=owner.id, name="Invites")
    db_session.add_all([owner, invitee, group])
    await db_session.flush()

    invite = GroupInvite(
        group_id=group.id,
        inviter_id=owner.id,
        invitee_id=invitee.id,
        status=GroupInviteStatus.PENDING,
        expires_at=datetime.now(tz=timezone.utc),
    )
    db_session.add(invite)
    await db_session.flush()

    repo = GroupInviteRepository(db_session)
    pending = await repo.get_pending(group.id, invitee.id)

    assert pending is not None
    assert pending.invitee_id == invitee.id
