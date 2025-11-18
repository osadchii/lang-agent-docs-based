"""Group domain models for shared study materials."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import GUID, Base, SoftDeleteMixin, TimestampMixin


class GroupRole(str, enum.Enum):
    """User role within a group."""

    OWNER = "owner"
    MEMBER = "member"


class Group(SoftDeleteMixin, TimestampMixin, Base):
    """Study group used to share decks and topics."""

    __tablename__ = "groups"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)

    max_members: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=5,
        server_default=text("5"),
    )
    members_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default=text("1"),
    )

    owner = relationship("User", back_populates="owned_groups", innerjoin=True)
    members = relationship("GroupMember", back_populates="group")
    invites = relationship(
        "GroupInvite",
        back_populates="group",
        cascade="all, delete-orphan",
    )
    materials = relationship(
        "GroupMaterial",
        back_populates="group",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index(
            "ix_groups_owner_id_active",
            "owner_id",
            postgresql_where=text("deleted = FALSE"),
        ),
        CheckConstraint("members_count >= 0", name="ck_groups_members_count_positive"),
        CheckConstraint("max_members > 0", name="ck_groups_max_members_positive"),
    )


class GroupMember(Base):
    """Association table describing group participants."""

    __tablename__ = "group_members"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    group_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("groups.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    role: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default=text("'member'"),
    )
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    group = relationship("Group", back_populates="members", innerjoin=True)
    user = relationship("User", back_populates="group_memberships", innerjoin=True)

    __table_args__ = (
        UniqueConstraint("group_id", "user_id", name="ux_group_members_group_user"),
        Index("ix_group_members_group_id", "group_id"),
        Index("ix_group_members_user_id", "user_id"),
    )


class GroupInviteStatus(str, enum.Enum):
    """Lifecycle of a group invite."""

    PENDING = "pending"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    EXPIRED = "expired"


class GroupInvite(Base):
    """Pending invites sent by owners to bring new members."""

    __tablename__ = "group_invites"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    group_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("groups.id", ondelete="CASCADE"),
        nullable=False,
    )
    inviter_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    invitee_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[GroupInviteStatus] = mapped_column(
        Enum(
            GroupInviteStatus,
            name="group_invite_status_enum",
            native_enum=False,
            validate_strings=True,
        ),
        nullable=False,
        default=GroupInviteStatus.PENDING,
        server_default=text("'pending'"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    group = relationship("Group", back_populates="invites", innerjoin=True)
    inviter = relationship(
        "User",
        foreign_keys=[inviter_id],
        back_populates="sent_group_invites",
        innerjoin=True,
    )
    invitee = relationship(
        "User",
        foreign_keys=[invitee_id],
        back_populates="received_group_invites",
        innerjoin=True,
    )

    __table_args__ = (
        Index("ix_group_invites_group_id", "group_id"),
        Index("ix_group_invites_invitee_id", "invitee_id"),
        Index("ix_group_invites_status", "status"),
        Index(
            "ix_group_invites_pending_unique",
            "group_id",
            "invitee_id",
            unique=True,
            postgresql_where=text("status = 'pending'"),
            sqlite_where=text("status = 'pending'"),
        ),
    )


class GroupMaterialType(str, enum.Enum):
    """Material types that can be shared with a group."""

    DECK = "deck"
    TOPIC = "topic"


class GroupMaterial(Base):
    """Polymorphic association table linking groups and materials."""

    __tablename__ = "group_materials"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    group_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("groups.id", ondelete="CASCADE"),
        nullable=False,
    )
    material_id: Mapped[uuid.UUID] = mapped_column(GUID(), nullable=False)
    material_type: Mapped[GroupMaterialType] = mapped_column(
        Enum(
            GroupMaterialType,
            name="group_material_type_enum",
            native_enum=False,
            validate_strings=True,
        ),
        nullable=False,
    )
    shared_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    group = relationship("Group", back_populates="materials", innerjoin=True)

    __table_args__ = (
        UniqueConstraint(
            "group_id",
            "material_id",
            "material_type",
            name="ux_group_materials_unique",
        ),
        Index("ix_group_materials_group_id", "group_id"),
        Index(
            "ix_group_materials_material_type",
            "material_id",
            "material_type",
        ),
    )


__all__ = [
    "Group",
    "GroupInvite",
    "GroupInviteStatus",
    "GroupMaterial",
    "GroupMaterialType",
    "GroupMember",
    "GroupRole",
]
