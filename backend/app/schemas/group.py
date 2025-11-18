"""Pydantic schemas for group endpoints."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.group import GroupInviteStatus, GroupMaterialType, GroupRole


class GroupCreateRequest(BaseModel):
    """Request payload for POST /api/groups."""

    name: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)


class GroupUpdateRequest(BaseModel):
    """Patch body for updating group metadata."""

    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)


class GroupInviteRequest(BaseModel):
    """Body for POST /api/groups/{id}/members."""

    user_identifier: str = Field(min_length=1, max_length=255)


class GroupResponse(BaseModel):
    """Serialized group with role metadata."""

    id: UUID
    owner_id: UUID
    owner_name: str | None
    name: str
    description: str | None
    role: GroupRole
    members_count: int
    max_members: int
    materials_count: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class GroupListResponse(BaseModel):
    """Envelope for GET /api/groups."""

    data: list[GroupResponse]


class GroupMemberResponse(BaseModel):
    """List entry representing a group participant."""

    user_id: UUID
    telegram_id: int
    first_name: str | None
    username: str | None
    role: GroupRole
    joined_at: datetime


class GroupMemberListResponse(BaseModel):
    data: list[GroupMemberResponse]


class GroupInviteResponse(BaseModel):
    """Invite metadata shown to owners."""

    invite_id: UUID
    group_id: UUID
    user_id: UUID
    user_name: str | None
    status: GroupInviteStatus
    created_at: datetime
    expires_at: datetime


class GroupInviteListResponse(BaseModel):
    data: list[GroupInviteResponse]


class GroupInviteAcceptResponse(BaseModel):
    """Response body when invitee accepts an invite."""

    group_id: UUID
    group_name: str
    role: GroupRole
    joined_at: datetime


class SharedMaterialResponse(BaseModel):
    """Material shared within a group."""

    id: UUID
    type: GroupMaterialType
    name: str
    description: str | None
    owner_id: UUID | None
    owner_name: str | None
    cards_count: int | None = None
    exercises_count: int | None = None
    shared_at: datetime


class GroupMaterialListResponse(BaseModel):
    data: list[SharedMaterialResponse]


class GroupMaterialAddRequest(BaseModel):
    material_ids: list[UUID] = Field(min_length=1)
    type: GroupMaterialType


class GroupMaterialBatchEntry(BaseModel):
    id: UUID
    type: GroupMaterialType
    name: str | None = None
    reason: str | None = None


class GroupMaterialAddResponse(BaseModel):
    added: list[GroupMaterialBatchEntry]
    already_shared: list[GroupMaterialBatchEntry]
    failed: list[GroupMaterialBatchEntry]


__all__ = [
    "GroupCreateRequest",
    "GroupInviteRequest",
    "GroupInviteAcceptResponse",
    "GroupInviteListResponse",
    "GroupInviteResponse",
    "GroupListResponse",
    "GroupMaterialAddRequest",
    "GroupMaterialAddResponse",
    "GroupMaterialListResponse",
    "GroupMaterialBatchEntry",
    "GroupMemberListResponse",
    "GroupMemberResponse",
    "GroupResponse",
    "GroupUpdateRequest",
    "SharedMaterialResponse",
]
