"""Repositories encapsulating persistence logic for groups."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import datetime, timezone

from sqlalchemy import Select, func, select
from sqlalchemy.orm import selectinload
from sqlalchemy.sql.selectable import Subquery

from app.models.deck import Deck
from app.models.group import (
    Group,
    GroupInvite,
    GroupInviteStatus,
    GroupMaterial,
    GroupMaterialType,
    GroupMember,
)
from app.models.language_profile import LanguageProfile
from app.models.topic import Topic
from app.repositories.base import BaseRepository


class GroupRepository(BaseRepository[Group]):
    """CRUD helpers for study groups."""

    async def create(
        self,
        *,
        owner_id: uuid.UUID,
        name: str,
        description: str | None = None,
        max_members: int = 5,
    ) -> Group:
        group = Group(
            owner_id=owner_id,
            name=name,
            description=description,
            max_members=max_members,
        )
        await self.add(group)
        await self.session.refresh(group)
        return group

    async def count_owned(self, owner_id: uuid.UUID) -> int:
        stmt = select(func.count()).where(
            Group.owner_id == owner_id,
            Group.deleted.is_(False),
        )
        result = await self.session.execute(stmt)
        return int(result.scalar_one())

    async def list_owned(self, owner_id: uuid.UUID) -> list[Group]:
        stmt: Select[tuple[Group]] = (
            select(Group)
            .options(selectinload(Group.owner))
            .where(Group.owner_id == owner_id, Group.deleted.is_(False))
            .order_by(Group.created_at.asc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().unique())

    async def list_member_of(self, user_id: uuid.UUID) -> list[Group]:
        stmt: Select[tuple[Group]] = (
            select(Group)
            .join(GroupMember, GroupMember.group_id == Group.id)
            .options(selectinload(Group.owner))
            .where(
                GroupMember.user_id == user_id,
                Group.deleted.is_(False),
            )
            .order_by(Group.created_at.asc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().unique())

    async def get(self, group_id: uuid.UUID) -> Group | None:
        stmt = (
            select(Group)
            .options(selectinload(Group.owner))
            .where(Group.id == group_id, Group.deleted.is_(False))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_owned(self, group_id: uuid.UUID, owner_id: uuid.UUID) -> Group | None:
        stmt = (
            select(Group)
            .options(selectinload(Group.owner))
            .where(
                Group.id == group_id,
                Group.owner_id == owner_id,
                Group.deleted.is_(False),
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def soft_delete(self, group: Group) -> None:
        group.deleted = True
        group.deleted_at = datetime.now(tz=timezone.utc)
        await self.session.flush()


class GroupMemberRepository(BaseRepository[GroupMember]):
    """Helper methods for managing group memberships."""

    async def get(
        self,
        group_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> GroupMember | None:
        stmt = select(GroupMember).where(
            GroupMember.group_id == group_id,
            GroupMember.user_id == user_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def add_member(
        self,
        group_id: uuid.UUID,
        user_id: uuid.UUID,
        *,
        role: str = "member",
    ) -> GroupMember:
        membership = GroupMember(group_id=group_id, user_id=user_id, role=role)
        await self.add(membership)
        await self.session.refresh(membership)
        return membership

    async def remove(self, membership: GroupMember) -> None:
        await self.session.delete(membership)
        await self.session.flush()

    async def list_with_users(self, group_id: uuid.UUID) -> list[GroupMember]:
        stmt: Select[tuple[GroupMember]] = (
            select(GroupMember)
            .options(selectinload(GroupMember.user))
            .where(GroupMember.group_id == group_id)
            .order_by(GroupMember.joined_at.asc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().unique())


class GroupInviteRepository(BaseRepository[GroupInvite]):
    """Persistence helpers for invites sent to prospective members."""

    async def create(
        self,
        *,
        group_id: uuid.UUID,
        inviter_id: uuid.UUID,
        invitee_id: uuid.UUID,
        expires_at: datetime,
    ) -> GroupInvite:
        invite = GroupInvite(
            group_id=group_id,
            inviter_id=inviter_id,
            invitee_id=invitee_id,
            expires_at=expires_at,
        )
        await self.add(invite)
        await self.session.refresh(invite)
        return invite

    async def get(self, invite_id: uuid.UUID) -> GroupInvite | None:
        stmt = (
            select(GroupInvite)
            .options(
                selectinload(GroupInvite.invitee),
                selectinload(GroupInvite.group),
            )
            .where(GroupInvite.id == invite_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_pending(
        self,
        group_id: uuid.UUID,
        invitee_id: uuid.UUID,
    ) -> GroupInvite | None:
        stmt = (
            select(GroupInvite)
            .options(selectinload(GroupInvite.invitee))
            .where(
                GroupInvite.group_id == group_id,
                GroupInvite.invitee_id == invitee_id,
                GroupInvite.status == GroupInviteStatus.PENDING,
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_for_group(self, group_id: uuid.UUID) -> list[GroupInvite]:
        stmt = (
            select(GroupInvite)
            .options(
                selectinload(GroupInvite.invitee),
                selectinload(GroupInvite.inviter),
            )
            .where(GroupInvite.group_id == group_id)
            .order_by(GroupInvite.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().unique())


class GroupMaterialRepository(BaseRepository[GroupMaterial]):
    """Query helpers for materials shared via groups."""

    async def get(
        self,
        group_id: uuid.UUID,
        material_id: uuid.UUID,
        material_type: GroupMaterialType,
    ) -> GroupMaterial | None:
        stmt = select(GroupMaterial).where(
            GroupMaterial.group_id == group_id,
            GroupMaterial.material_id == material_id,
            GroupMaterial.material_type == material_type,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_for_group(
        self,
        group_id: uuid.UUID,
        *,
        material_type: GroupMaterialType | None = None,
    ) -> list[GroupMaterial]:
        stmt = select(GroupMaterial).where(GroupMaterial.group_id == group_id)
        if material_type is not None:
            stmt = stmt.where(GroupMaterial.material_type == material_type)
        stmt = stmt.order_by(GroupMaterial.shared_at.desc())
        result = await self.session.execute(stmt)
        return list(result.scalars())

    async def count_for_groups(self, group_ids: Sequence[uuid.UUID]) -> dict[uuid.UUID, int]:
        if not group_ids:
            return {}
        stmt = (
            select(GroupMaterial.group_id, func.count())
            .where(GroupMaterial.group_id.in_(group_ids))
            .group_by(GroupMaterial.group_id)
        )
        result = await self.session.execute(stmt)
        return {group_id: int(count) for group_id, count in result.all()}

    async def exists_for_material(
        self,
        material_id: uuid.UUID,
        material_type: GroupMaterialType,
    ) -> bool:
        stmt = (
            select(func.count())
            .where(
                GroupMaterial.material_id == material_id,
                GroupMaterial.material_type == material_type,
            )
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return bool(result.scalar_one())

    async def list_shared_decks_for_user(
        self,
        user_id: uuid.UUID,
        *,
        language: str | None = None,
    ) -> list[Deck]:
        group_ids = self._group_ids_subquery(user_id)
        stmt: Select[tuple[Deck]] = (
            select(Deck)
            .join(GroupMaterial, GroupMaterial.material_id == Deck.id)
            .join(group_ids, GroupMaterial.group_id == group_ids.c.group_id)
            .join(Group, GroupMaterial.group_id == Group.id)
            .join(LanguageProfile, Deck.profile_id == LanguageProfile.id)
            .options(selectinload(Deck.owner))
            .where(
                GroupMaterial.material_type == GroupMaterialType.DECK,
                Deck.deleted.is_(False),
                LanguageProfile.deleted.is_(False),
                Group.deleted.is_(False),
                LanguageProfile.user_id != user_id,
            )
            .order_by(Deck.created_at.asc())
        )
        if language:
            stmt = stmt.where(LanguageProfile.language == language)
        result = await self.session.execute(stmt)
        decks = list(result.scalars().unique())
        for deck in decks:
            deck.is_group = True
        return decks

    async def list_shared_topics_for_user(
        self,
        user_id: uuid.UUID,
        *,
        language: str | None = None,
    ) -> list[Topic]:
        group_ids = self._group_ids_subquery(user_id)
        stmt: Select[tuple[Topic]] = (
            select(Topic)
            .join(GroupMaterial, GroupMaterial.material_id == Topic.id)
            .join(group_ids, GroupMaterial.group_id == group_ids.c.group_id)
            .join(Group, GroupMaterial.group_id == Group.id)
            .join(LanguageProfile, Topic.profile_id == LanguageProfile.id)
            .options(selectinload(Topic.owner))
            .where(
                GroupMaterial.material_type == GroupMaterialType.TOPIC,
                Topic.deleted.is_(False),
                LanguageProfile.deleted.is_(False),
                Group.deleted.is_(False),
                LanguageProfile.user_id != user_id,
            )
            .order_by(Topic.created_at.asc())
        )
        if language:
            stmt = stmt.where(LanguageProfile.language == language)
        result = await self.session.execute(stmt)
        topics = list(result.scalars().unique())
        for topic in topics:
            topic.is_group = True
        return topics

    def _group_ids_subquery(self, user_id: uuid.UUID) -> Subquery:
        owned = select(Group.id.label("group_id")).where(
            Group.owner_id == user_id, Group.deleted.is_(False)
        )
        member = (
            select(GroupMember.group_id.label("group_id"))
            .join(Group, GroupMember.group_id == Group.id)
            .where(
                GroupMember.user_id == user_id,
                Group.deleted.is_(False),
            )
        )
        return owned.union(member).subquery()


__all__ = [
    "GroupInviteRepository",
    "GroupMaterialRepository",
    "GroupMemberRepository",
    "GroupRepository",
]
