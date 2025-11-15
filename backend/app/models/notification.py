"""Notification entities and streak reminder audit trail models."""

from __future__ import annotations

import enum
import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Index, String, Text, func, text
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.models.base import GUID, Base


class NotificationType(str, enum.Enum):
    """Supported notification categories."""

    STREAK_REMINDER = "streak_reminder"
    GROUP_INVITE = "group_invite"
    GROUP_MATERIAL_ADDED = "group_material_added"
    SUBSCRIPTION_EXPIRING = "subscription_expiring"
    ACHIEVEMENT_UNLOCKED = "achievement_unlocked"


class Notification(Base):
    """Persisted notification shown inside the Mini App."""

    __tablename__ = "notifications"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    type: Mapped[NotificationType] = mapped_column(
        String(50),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    data: Mapped[dict[str, object]] = mapped_column(
        MutableDict.as_mutable(JSON()),
        default=dict,
        nullable=False,
    )

    is_read: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("false"),
    )
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    user = relationship("User", back_populates="notifications")

    __table_args__ = (
        Index("ix_notifications_user_id", "user_id"),
        Index("ix_notifications_is_read", "is_read"),
        Index("ix_notifications_created_at", "created_at"),
        Index("ix_notifications_type", "type"),
    )


class StreakReminder(Base):
    """Audit table tracking sent streak reminders per profile/day."""

    __tablename__ = "streak_reminders"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    profile_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("language_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )

    sent_date: Mapped[date] = mapped_column(Date, nullable=False)
    sent_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    user = relationship("User", back_populates="streak_reminders")
    profile = relationship("LanguageProfile", back_populates="streak_reminders")

    __table_args__ = (
        Index("ix_streak_reminders_user_profile", "user_id", "profile_id"),
        Index("ix_streak_reminders_sent_date", "sent_date"),
        Index(
            "ux_streak_reminders_unique_per_day",
            "user_id",
            "profile_id",
            "sent_date",
            unique=True,
        ),
    )


__all__ = ["Notification", "NotificationType", "StreakReminder"]
