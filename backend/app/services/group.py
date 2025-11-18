"""Domain service orchestrating group creation, invites, and materials."""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Sequence

from app.core.errors import ApplicationError, ErrorCode, NotFoundError
from app.models.deck import Deck
from app.models.group import (
    Group,
    GroupInvite,
    GroupInviteStatus,
    GroupMaterial,
    GroupMaterialType,
    GroupRole,
)
from app.models.topic import Topic
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

FREE_GROUP_LIMIT = 1
PREMIUM_GROUP_LIMIT = 100
FREE_GROUP_MEMBERS = 5
PREMIUM_GROUP_MEMBERS = 100
INVITE_TTL_DAYS = 7


@dataclass(slots=True)
class GroupListItem:
    group: Group
    role: GroupRole
    materials_count: int


@dataclass(slots=True)
class MemberInfo:
    user: User
    role: GroupRole
    joined_at: datetime


@dataclass(slots=True)
class SharedMaterial:
    id: uuid.UUID
    type: GroupMaterialType
    name: str
    description: str | None
    owner_id: uuid.UUID | None
    owner_name: str | None
    cards_count: int | None = None
    exercises_count: int | None = None
    shared_at: datetime = datetime.now(timezone.utc)


@dataclass(slots=True)
class MaterialBatchEntry:
    id: uuid.UUID
    type: GroupMaterialType
    name: str | None = None
    reason: str | None = None


@dataclass(slots=True)
class MaterialBatchResult:
    added: list[MaterialBatchEntry]
    already_shared: list[MaterialBatchEntry]
    failed: list[MaterialBatchEntry]


@dataclass(slots=True)
class InviteAcceptance:
    group_id: uuid.UUID
    group_name: str
    role: GroupRole
    joined_at: datetime


class GroupService:
    """Coordinate group, invite, and material operations."""

    def __init__(
        self,
        group_repo: GroupRepository,
        member_repo: GroupMemberRepository,
        invite_repo: GroupInviteRepository,
        material_repo: GroupMaterialRepository,
        user_repo: UserRepository,
        deck_repo: DeckRepository,
        topic_repo: TopicRepository,
    ) -> None:
        self.group_repo = group_repo
        self.member_repo = member_repo
        self.invite_repo = invite_repo
        self.material_repo = material_repo
        self.user_repo = user_repo
        self.deck_repo = deck_repo
        self.topic_repo = topic_repo

    async def list_groups(
        self,
        user: User,
        *,
        role: GroupRole | None = None,
    ) -> list[GroupListItem]:
        """Return all groups accessible to the user with role metadata."""
        pairs: list[tuple[Group, GroupRole]] = []
        if role in (None, GroupRole.OWNER):
            for group in await self.group_repo.list_owned(user.id):
                pairs.append((group, GroupRole.OWNER))
        if role in (None, GroupRole.MEMBER):
            member_groups = await self.group_repo.list_member_of(user.id)
            seen = {group.id for group, _ in pairs}
            for group in member_groups:
                if group.id not in seen:
                    pairs.append((group, GroupRole.MEMBER))

        counts = await self.material_repo.count_for_groups([group.id for group, _ in pairs])
        return [
            GroupListItem(group=group, role=group_role, materials_count=counts.get(group.id, 0))
            for group, group_role in pairs
        ]

    async def create_group(self, user: User, name: str, description: str | None = None) -> Group:
        """Create a new group respecting subscription limits."""
        limit = PREMIUM_GROUP_LIMIT if user.is_premium else FREE_GROUP_LIMIT
        current = await self.group_repo.count_owned(user.id)
        if current >= limit:
            code = ErrorCode.PAYMENT_REQUIRED if not user.is_premium else ErrorCode.LIMIT_REACHED
            raise ApplicationError(
                code=code,
                message="????????? ????? ?????? ??? ??????? ?????.",
                status_code=402 if code == ErrorCode.PAYMENT_REQUIRED else 400,
            )

        sanitized_name = self._sanitize_text(name)
        sanitized_description = self._sanitize_text(description) if description else None
        if not sanitized_name:
            raise ApplicationError(
                code=ErrorCode.VALIDATION_ERROR,
                message="???????? ??????? ?? ??????? ???? ??????.",
            )
        max_members = PREMIUM_GROUP_MEMBERS if user.is_premium else FREE_GROUP_MEMBERS

        group = await self.group_repo.create(
            owner_id=user.id,
            name=sanitized_name,
            description=sanitized_description,
            max_members=max_members,
        )
        await self.group_repo.session.refresh(group)
        group.owner = user
        return group

    async def get_group(self, user: User, group_id: uuid.UUID) -> tuple[Group, GroupRole]:
        """Fetch a group ensuring the user has access."""
        return await self._ensure_group_access(group_id, user)

    async def update_group(
        self,
        user: User,
        group_id: uuid.UUID,
        *,
        name: str | None = None,
        description: str | None = None,
    ) -> Group:
        """Update group metadata; owner only."""
        group = await self._ensure_owner(group_id, user)
        if name is not None:
            sanitized = self._sanitize_text(name)
            if not sanitized:
                raise ApplicationError(
                    code=ErrorCode.VALIDATION_ERROR,
                    message="???????? ??????? ?? ??????? ???? ??????.",
                )
            group.name = sanitized
        if description is not None:
            group.description = self._sanitize_text(description)
        await self.group_repo.session.flush()
        await self.group_repo.session.refresh(group)
        return group

    async def delete_group(self, user: User, group_id: uuid.UUID) -> None:
        """Soft delete a group."""
        group = await self._ensure_owner(group_id, user)
        await self.group_repo.soft_delete(group)

    async def list_members(self, user: User, group_id: uuid.UUID) -> list[MemberInfo]:
        """Return all members including the owner."""
        group, _ = await self._ensure_group_access(group_id, user)
        owner = MemberInfo(
            user=group.owner,
            role=GroupRole.OWNER,
            joined_at=group.created_at,
        )
        memberships = await self.member_repo.list_with_users(group_id)
        members = [
            MemberInfo(
                user=membership.user,
                role=GroupRole.MEMBER,
                joined_at=membership.joined_at,
            )
            for membership in memberships
        ]
        return [owner, *members]

    async def invite_member(self, user: User, group_id: uuid.UUID, identifier: str) -> GroupInvite:
        """Invite a new member by username or telegram id."""
        group = await self._ensure_owner(group_id, user)
        if group.members_count >= group.max_members:
            raise ApplicationError(
                code=ErrorCode.LIMIT_REACHED,
                message="????????? ????? ??????????.",
            )
        invitee = await self._resolve_identifier(identifier)
        if invitee.id == user.id or invitee.id == group.owner_id:
            raise ApplicationError(
                code=ErrorCode.INVALID_FIELD_VALUE,
                message="?????? ?? ??????? ??????? ??????? ??????.",
            )
        membership = await self.member_repo.get(group.id, invitee.id)
        if membership is not None:
            raise ApplicationError(
                code=ErrorCode.ALREADY_MEMBER,
                message="????????? ??? ???????? ??????.",
            )
        pending = await self.invite_repo.get_pending(group.id, invitee.id)
        if pending:
            return pending
        expires_at = datetime.now(tz=timezone.utc) + timedelta(days=INVITE_TTL_DAYS)
        invite = await self.invite_repo.create(
            group_id=group.id,
            inviter_id=user.id,
            invitee_id=invitee.id,
            expires_at=expires_at,
        )
        await self.invite_repo.session.refresh(invite, attribute_names=["invitee"])
        return invite

    async def list_invites(self, user: User, group_id: uuid.UUID) -> list[GroupInvite]:
        """List invites for a group (owner only)."""
        await self._ensure_owner(group_id, user)
        return await self.invite_repo.list_for_group(group_id)

    async def cancel_invite(self, user: User, invite_id: uuid.UUID) -> None:
        """Cancel a pending invite."""
        invite = await self.invite_repo.get(invite_id)
        if invite is None:
            raise NotFoundError(
                code=ErrorCode.INVITE_NOT_FOUND,
                message="?????????? ?? ???????.",
            )
        await self._ensure_owner(invite.group_id, user)
        await self.invite_repo.session.delete(invite)
        await self.invite_repo.session.flush()

    async def accept_invite(self, user: User, invite_id: uuid.UUID) -> InviteAcceptance:
        """Accept a pending invite."""
        invite = await self._ensure_invitee(invite_id, user)
        group = invite.group
        if group.members_count >= group.max_members:
            raise ApplicationError(
                code=ErrorCode.LIMIT_REACHED,
                message="????????? ????? ??????????.",
            )
        invite.status = GroupInviteStatus.ACCEPTED
        invite.responded_at = datetime.now(tz=timezone.utc)
        membership = await self.member_repo.add_member(group.id, user.id)
        group.members_count += 1
        await self.invite_repo.session.flush()
        return InviteAcceptance(
            group_id=group.id,
            group_name=group.name,
            role=GroupRole.MEMBER,
            joined_at=membership.joined_at,
        )

    async def decline_invite(self, user: User, invite_id: uuid.UUID) -> None:
        """Decline a pending invite."""
        invite = await self._ensure_invitee(invite_id, user)
        invite.status = GroupInviteStatus.DECLINED
        invite.responded_at = datetime.now(tz=timezone.utc)
        await self.invite_repo.session.flush()

    async def remove_member(self, user: User, group_id: uuid.UUID, member_id: uuid.UUID) -> None:
        """Remove a member; owner-only."""
        group = await self._ensure_owner(group_id, user)
        if member_id == group.owner_id:
            raise ApplicationError(
                code=ErrorCode.CANNOT_REMOVE_OWNER,
                message="?????? ??????? ????????? ??????.",
            )
        membership = await self.member_repo.get(group.id, member_id)
        if membership is None:
            raise NotFoundError(
                code=ErrorCode.USER_NOT_FOUND,
                message="??????????? ?? ??????? ?? ??????.",
            )
        await self.member_repo.remove(membership)
        group.members_count = max(1, group.members_count - 1)
        await self.member_repo.session.flush()

    async def leave_group(self, user: User, group_id: uuid.UUID) -> None:
        """Allow member to leave a group."""
        group, role = await self._ensure_group_access(group_id, user)
        if role == GroupRole.OWNER:
            raise ApplicationError(
                code=ErrorCode.OWNER_CANNOT_LEAVE,
                message="???????? ?? ????? ??????? ??????.",
            )
        membership = await self.member_repo.get(group.id, user.id)
        if membership is None:
            return
        await self.member_repo.remove(membership)
        group.members_count = max(1, group.members_count - 1)
        await self.member_repo.session.flush()

    async def list_materials(
        self,
        user: User,
        group_id: uuid.UUID,
        *,
        material_type: GroupMaterialType | None = None,
    ) -> list[SharedMaterial]:
        """Return shared decks/topics for a group."""
        group, _ = await self._ensure_group_access(group_id, user)
        materials = await self.material_repo.list_for_group(group.id, material_type=material_type)
        deck_ids = [
            item.material_id for item in materials if item.material_type == GroupMaterialType.DECK
        ]
        topic_ids = [
            item.material_id for item in materials if item.material_type == GroupMaterialType.TOPIC
        ]
        decks = {deck.id: deck for deck in await self.deck_repo.list_by_ids(deck_ids)}
        topics = {topic.id: topic for topic in await self.topic_repo.list_by_ids(topic_ids)}

        shared: list[SharedMaterial] = []
        for record in materials:
            if record.material_type == GroupMaterialType.DECK:
                deck = decks.get(record.material_id)
                if deck:
                    shared.append(
                        SharedMaterial(
                            id=deck.id,
                            type=GroupMaterialType.DECK,
                            name=deck.name,
                            description=deck.description,
                            owner_id=deck.owner_id,
                            owner_name=self._display_name(deck.owner),
                            cards_count=deck.cards_count,
                            shared_at=record.shared_at,
                        )
                    )
            else:
                topic = topics.get(record.material_id)
                if topic:
                    shared.append(
                        SharedMaterial(
                            id=topic.id,
                            type=GroupMaterialType.TOPIC,
                            name=topic.name,
                            description=topic.description,
                            owner_id=topic.owner_id,
                            owner_name=self._display_name(topic.owner),
                            exercises_count=topic.exercises_count,
                            shared_at=record.shared_at,
                        )
                    )
        return shared

    async def add_materials(
        self,
        user: User,
        group_id: uuid.UUID,
        *,
        material_type: GroupMaterialType,
        material_ids: Sequence[uuid.UUID],
    ) -> MaterialBatchResult:
        """Share decks or topics with the group."""
        group = await self._ensure_owner(group_id, user)
        sanitized_ids = []
        seen: set[uuid.UUID] = set()
        for material_id in material_ids:
            if material_id not in seen:
                sanitized_ids.append(material_id)
                seen.add(material_id)

        existing = {
            material.material_id
            for material in await self.material_repo.list_for_group(
                group.id,
                material_type=material_type,
            )
        }

        added: list[MaterialBatchEntry] = []
        already_shared: list[MaterialBatchEntry] = []
        failed: list[MaterialBatchEntry] = []

        for material_id in sanitized_ids:
            if material_id in existing:
                already_shared.append(MaterialBatchEntry(id=material_id, type=material_type))
                continue

            resource = await self._load_material_for_owner(material_type, material_id, user)
            if resource is None:
                failed.append(
                    MaterialBatchEntry(
                        id=material_id,
                        type=material_type,
                        reason="not_found",
                    )
                )
                continue

            entry = GroupMaterial(
                group_id=group.id,
                material_id=material_id,
                material_type=material_type,
            )
            await self.material_repo.add(entry)
            resource.is_group = True
            added.append(
                MaterialBatchEntry(
                    id=material_id,
                    type=material_type,
                    name=getattr(resource, "name", None),
                )
            )

        await self.material_repo.session.flush()
        return MaterialBatchResult(
            added=added,
            already_shared=already_shared,
            failed=failed,
        )

    async def remove_material(
        self,
        user: User,
        group_id: uuid.UUID,
        *,
        material_id: uuid.UUID,
        material_type: GroupMaterialType,
    ) -> None:
        """Remove previously shared material."""
        group = await self._ensure_owner(group_id, user)
        entry = await self.material_repo.get(group.id, material_id, material_type)
        if entry is None:
            raise NotFoundError(
                code=ErrorCode.NOT_FOUND,
                message="????????? ?? ????????.",
            )
        await self.material_repo.session.delete(entry)
        await self.material_repo.session.flush()
        await self._maybe_reset_group_flag(material_id, material_type)

    async def count_materials(self, group_ids: Sequence[uuid.UUID]) -> dict[uuid.UUID, int]:
        """Return materials_count for provided groups."""
        return await self.material_repo.count_for_groups(group_ids)

    async def _maybe_reset_group_flag(
        self,
        material_id: uuid.UUID,
        material_type: GroupMaterialType,
    ) -> None:
        still_shared = await self.material_repo.exists_for_material(material_id, material_type)
        if still_shared:
            return
        if material_type == GroupMaterialType.DECK:
            deck = await self.deck_repo.session.get(Deck, material_id)
            if deck is not None:
                deck.is_group = False
        else:
            topic = await self.topic_repo.session.get(Topic, material_id)
            if topic is not None:
                topic.is_group = False
        await self.material_repo.session.flush()

    async def _load_material_for_owner(
        self,
        material_type: GroupMaterialType,
        material_id: uuid.UUID,
        user: User,
    ) -> Deck | Topic | None:
        if material_type == GroupMaterialType.DECK:
            return await self.deck_repo.get_for_user(material_id, user.id)
        return await self.topic_repo.get_for_user(material_id, user.id)

    async def _ensure_owner(self, group_id: uuid.UUID, user: User) -> Group:
        group = await self.group_repo.get(group_id)
        if group is None:
            raise NotFoundError(
                code=ErrorCode.GROUP_NOT_FOUND,
                message="?????? ?? ???????.",
            )
        if group.owner_id != user.id:
            raise ApplicationError(
                code=ErrorCode.FORBIDDEN,
                message="????????????? ?????? ?????? ???????.",
                status_code=403,
            )
        return group

    async def _ensure_group_access(
        self,
        group_id: uuid.UUID,
        user: User,
    ) -> tuple[Group, GroupRole]:
        group = await self.group_repo.get(group_id)
        if group is None:
            raise NotFoundError(
                code=ErrorCode.GROUP_NOT_FOUND,
                message="?????? ?? ???????.",
            )
        if group.owner_id == user.id:
            return group, GroupRole.OWNER
        membership = await self.member_repo.get(group.id, user.id)
        if membership is None:
            raise ApplicationError(
                code=ErrorCode.FORBIDDEN,
                message="?????? ?????? ?? ???????? ????????.",
                status_code=403,
            )
        return group, GroupRole.MEMBER

    async def _ensure_invitee(self, invite_id: uuid.UUID, user: User) -> GroupInvite:
        invite = await self.invite_repo.get(invite_id)
        if invite is None or invite.invitee_id != user.id:
            raise NotFoundError(
                code=ErrorCode.INVITE_NOT_FOUND,
                message="?????????? ?? ???????.",
            )
        if invite.status != GroupInviteStatus.PENDING:
            raise ApplicationError(
                code=ErrorCode.INVITE_EXPIRED,
                message="?????????? ???? ????????.",
            )
        now = datetime.now(tz=timezone.utc)
        expires_at = invite.expires_at
        if expires_at is not None and now >= self._ensure_timezone(expires_at):
            invite.status = GroupInviteStatus.EXPIRED
            invite.responded_at = now
            await self.invite_repo.session.flush()
            raise ApplicationError(
                code=ErrorCode.INVITE_EXPIRED,
                message="?????????? ???????.",
            )
        return invite

    async def _resolve_identifier(self, identifier: str) -> User:
        value = identifier.strip()
        if not value:
            raise NotFoundError(
                code=ErrorCode.USER_NOT_FOUND,
                message="??????????? ?? ???????.",
            )
        username = None
        telegram_id = None
        if value.startswith("@"):
            username = value[1:]
        elif value.lower().startswith("https://t.me/") or value.lower().startswith("t.me/"):
            username = value.split("/")[-1].lstrip("@")
        elif value.isdigit():
            telegram_id = int(value)
        else:
            username = value

        user: User | None = None
        if telegram_id is not None:
            user = await self.user_repo.get_by_telegram_id(telegram_id)
        if user is None and username:
            user = await self.user_repo.get_by_username(username)
        if user is None:
            raise NotFoundError(
                code=ErrorCode.USER_NOT_FOUND,
                message="??????????? ?? ???????.",
            )
        return user

    def _sanitize_text(self, value: str) -> str:
        cleaned = re.sub(r"\s+", " ", value).strip()
        return re.sub(r"[<>]", "", cleaned)

    def _display_name(self, user: User | None) -> str | None:  # pragma: no cover
        if user is None:
            return None
        for candidate in (user.username, user.first_name, user.last_name):
            if candidate:
                return candidate
        return None

    @staticmethod
    def _ensure_timezone(value: datetime) -> datetime:  # pragma: no cover
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value


__all__ = [
    "GroupListItem",
    "GroupService",
    "InviteAcceptance",
    "MaterialBatchResult",
    "MemberInfo",
    "SharedMaterial",
]
