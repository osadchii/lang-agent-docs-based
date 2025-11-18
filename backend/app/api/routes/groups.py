"""Group CRUD, membership, and material sharing endpoints."""

from __future__ import annotations

from typing import Annotated, Protocol
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.db import get_session
from app.models.group import GroupInvite, GroupMaterialType, GroupRole
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
from app.schemas.group import (
    GroupCreateRequest,
    GroupInviteAcceptResponse,
    GroupInviteListResponse,
    GroupInviteRequest,
    GroupInviteResponse,
    GroupListResponse,
    GroupMaterialAddRequest,
    GroupMaterialAddResponse,
    GroupMaterialBatchEntry,
    GroupMaterialListResponse,
    GroupMemberListResponse,
    GroupMemberResponse,
    GroupResponse,
    GroupUpdateRequest,
    SharedMaterialResponse,
)
from app.services.group import GroupListItem, GroupService, MemberInfo, SharedMaterial


async def get_group_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> GroupService:
    """Wire repositories into the group service."""
    return GroupService(
        GroupRepository(session),
        GroupMemberRepository(session),
        GroupInviteRepository(session),
        GroupMaterialRepository(session),
        UserRepository(session),
        DeckRepository(session),
        TopicRepository(session),
    )


router = APIRouter(prefix="/groups", tags=["groups"])

CurrentUser = Annotated[User, Depends(get_current_user)]
GroupServiceDep = Annotated[GroupService, Depends(get_group_service)]


def _display_name(user: User | None) -> str | None:  # pragma: no cover
    if user is None:
        return None
    for candidate in (user.username, user.first_name, user.last_name):
        if candidate:
            return candidate
    return None


def _serialize_group(item: GroupListItem) -> GroupResponse:
    group = item.group
    return GroupResponse(
        id=group.id,
        owner_id=group.owner_id,
        owner_name=_display_name(group.owner),
        name=group.name,
        description=group.description,
        role=item.role,
        members_count=group.members_count,
        max_members=group.max_members,
        materials_count=item.materials_count,
        created_at=group.created_at,
        updated_at=group.updated_at,
    )


def _serialize_member(member: MemberInfo) -> GroupMemberResponse:
    user = member.user
    return GroupMemberResponse(
        user_id=user.id,
        telegram_id=user.telegram_id,
        first_name=user.first_name,
        username=user.username,
        role=member.role,
        joined_at=member.joined_at,
    )


def _serialize_invite(invite: GroupInvite) -> GroupInviteResponse:
    invitee_name = _display_name(getattr(invite, "invitee", None))
    return GroupInviteResponse(
        invite_id=invite.id,
        group_id=invite.group_id,
        user_id=invite.invitee_id,
        user_name=invitee_name,
        status=invite.status,
        created_at=invite.created_at,
        expires_at=invite.expires_at,
    )


def _serialize_material(material: SharedMaterial) -> SharedMaterialResponse:
    return SharedMaterialResponse(
        id=material.id,
        type=material.type,
        name=material.name,
        description=material.description,
        owner_id=material.owner_id,
        owner_name=material.owner_name,
        cards_count=material.cards_count,
        exercises_count=material.exercises_count,
        shared_at=material.shared_at,
    )


class _BatchEntry(Protocol):
    id: UUID
    type: GroupMaterialType
    name: str | None
    reason: str | None


def _material_batch_entry(entry: _BatchEntry) -> GroupMaterialBatchEntry:  # pragma: no cover
    return GroupMaterialBatchEntry(
        id=entry.id,
        type=entry.type,
        name=entry.name,
        reason=entry.reason,
    )


@router.get("", response_model=GroupListResponse)
async def list_groups(
    user: CurrentUser,
    service: GroupServiceDep,
    role: Annotated[
        GroupRole | None,
        Query(description="Filter by the current user's role within the group."),
    ] = None,
) -> GroupListResponse:
    items = await service.list_groups(user, role=role)
    data = [_serialize_group(item) for item in items]
    return GroupListResponse(data=data)


@router.post("", response_model=GroupResponse, status_code=status.HTTP_201_CREATED)
async def create_group(
    payload: GroupCreateRequest,
    user: CurrentUser,
    service: GroupServiceDep,
) -> GroupResponse:
    group = await service.create_group(user, payload.name, description=payload.description)
    wrapper = GroupListItem(group=group, role=GroupRole.OWNER, materials_count=0)
    return _serialize_group(wrapper)


@router.get(
    "/{group_id}",
    response_model=GroupResponse,
)
async def get_group(
    group_id: UUID,
    user: CurrentUser,
    service: GroupServiceDep,
) -> GroupResponse:
    group, role = await service.get_group(user, group_id)
    counts = await service.count_materials([group.id])
    wrapper = GroupListItem(group=group, role=role, materials_count=counts.get(group.id, 0))
    return _serialize_group(wrapper)


@router.patch("/{group_id}", response_model=GroupResponse)
async def update_group(
    group_id: UUID,
    payload: GroupUpdateRequest,
    user: CurrentUser,
    service: GroupServiceDep,
) -> GroupResponse:
    group = await service.update_group(
        user,
        group_id,
        name=payload.name,
        description=payload.description,
    )
    counts = await service.count_materials([group.id])
    wrapper = GroupListItem(
        group=group,
        role=GroupRole.OWNER,
        materials_count=counts.get(group.id, 0),
    )
    return _serialize_group(wrapper)


@router.delete("/{group_id}")
async def delete_group(
    group_id: UUID,
    user: CurrentUser,
    service: GroupServiceDep,
) -> Response:
    await service.delete_group(user, group_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/{group_id}/members",
    response_model=GroupMemberListResponse,
)
async def list_members(
    group_id: UUID,
    user: CurrentUser,
    service: GroupServiceDep,
) -> GroupMemberListResponse:
    members = await service.list_members(user, group_id)
    return GroupMemberListResponse(data=[_serialize_member(member) for member in members])


@router.post(
    "/{group_id}/members",
    response_model=GroupInviteResponse,
    status_code=status.HTTP_201_CREATED,
)
async def invite_member(
    group_id: UUID,
    payload: GroupInviteRequest,
    user: CurrentUser,
    service: GroupServiceDep,
) -> GroupInviteResponse:
    invite = await service.invite_member(user, group_id, payload.user_identifier)
    return _serialize_invite(invite)


@router.delete("/{group_id}/members/{member_id}")
async def remove_member(
    group_id: UUID,
    member_id: UUID,
    user: CurrentUser,
    service: GroupServiceDep,
) -> Response:
    await service.remove_member(user, group_id, member_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{group_id}/leave")
async def leave_group(
    group_id: UUID,
    user: CurrentUser,
    service: GroupServiceDep,
) -> Response:
    await service.leave_group(user, group_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/{group_id}/invites",
    response_model=GroupInviteListResponse,
)
async def list_invites(
    group_id: UUID,
    user: CurrentUser,
    service: GroupServiceDep,
) -> GroupInviteListResponse:
    invites = await service.list_invites(user, group_id)
    return GroupInviteListResponse(data=[_serialize_invite(invite) for invite in invites])


@router.delete("/invites/{invite_id}")
async def cancel_invite(
    invite_id: UUID,
    user: CurrentUser,
    service: GroupServiceDep,
) -> Response:
    await service.cancel_invite(user, invite_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/invites/{invite_id}/accept",
    response_model=GroupInviteAcceptResponse,
)
async def accept_invite(
    invite_id: UUID,
    user: CurrentUser,
    service: GroupServiceDep,
) -> GroupInviteAcceptResponse:
    result = await service.accept_invite(user, invite_id)
    return GroupInviteAcceptResponse(
        group_id=result.group_id,
        group_name=result.group_name,
        role=result.role,
        joined_at=result.joined_at,
    )


@router.post("/invites/{invite_id}/decline")
async def decline_invite(
    invite_id: UUID,
    user: CurrentUser,
    service: GroupServiceDep,
) -> Response:
    await service.decline_invite(user, invite_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/{group_id}/materials",
    response_model=GroupMaterialListResponse,
)
async def list_materials(
    group_id: UUID,
    user: CurrentUser,
    service: GroupServiceDep,
    material_type: Annotated[
        GroupMaterialType | None,
        Query(description="Optional filter by material type."),
    ] = None,
) -> GroupMaterialListResponse:
    materials = await service.list_materials(
        user,
        group_id,
        material_type=material_type,
    )
    return GroupMaterialListResponse(data=[_serialize_material(item) for item in materials])


@router.post(
    "/{group_id}/materials",
    response_model=GroupMaterialAddResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_materials(
    group_id: UUID,
    payload: GroupMaterialAddRequest,
    user: CurrentUser,
    service: GroupServiceDep,
) -> GroupMaterialAddResponse:
    result = await service.add_materials(
        user,
        group_id,
        material_type=payload.type,
        material_ids=payload.material_ids,
    )
    return GroupMaterialAddResponse(
        added=[_material_batch_entry(entry) for entry in result.added],
        already_shared=[_material_batch_entry(entry) for entry in result.already_shared],
        failed=[_material_batch_entry(entry) for entry in result.failed],
    )


@router.delete("/{group_id}/materials/{material_id}")
async def remove_material(
    group_id: UUID,
    material_id: UUID,
    material_type: Annotated[
        GroupMaterialType,
        Query(description="Type of the material to remove."),
    ],
    user: CurrentUser,
    service: GroupServiceDep,
) -> Response:
    await service.remove_material(
        user,
        group_id,
        material_id=material_id,
        material_type=material_type,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
