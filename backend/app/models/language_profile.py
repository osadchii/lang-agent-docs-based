"""Language profile model representing learner preferences."""

from __future__ import annotations

import uuid
from datetime import date
from typing import Callable, cast

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.mutable import MutableList
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import GUID, Base, SoftDeleteMixin, TimestampMixin


class LanguageProfile(SoftDeleteMixin, TimestampMixin, Base):
    __tablename__ = "language_profiles"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    language: Mapped[str] = mapped_column(String(10), nullable=False)
    language_name: Mapped[str] = mapped_column(String(100), nullable=False)

    current_level: Mapped[str] = mapped_column(String(2), nullable=False)
    target_level: Mapped[str] = mapped_column(String(2), nullable=False)

    _jsonb_factory: Callable[..., JSON] = cast(Callable[..., JSON], JSONB)
    JSONType = MutableList.as_mutable(
        JSON().with_variant(_jsonb_factory(astext_type=Text()), "postgresql")
    )
    goals: Mapped[list[str]] = mapped_column(JSONType, default=list, nullable=False)

    interface_language: Mapped[str] = mapped_column(
        String(10), nullable=False, server_default=text("'ru'")
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))

    streak: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    best_streak: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    total_active_days: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    last_activity_date: Mapped[date | None]

    user = relationship("User", back_populates="language_profiles")
    conversation_messages = relationship(
        "ConversationMessage",
        back_populates="profile",
        cascade="all, delete-orphan",
    )
    token_usage = relationship(
        "TokenUsage",
        back_populates="profile",
        cascade="all, delete-orphan",
    )
    decks = relationship("Deck", back_populates="profile", cascade="all, delete-orphan")
    topics = relationship("Topic", back_populates="profile", cascade="all, delete-orphan")
    exercises = relationship(
        "ExerciseHistory",
        back_populates="profile",
        cascade="all, delete-orphan",
    )
    streak_reminders = relationship(
        "StreakReminder",
        back_populates="profile",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        CheckConstraint(
            "current_level IN ('A1','A2','B1','B2','C1','C2')",
            name="ck_language_profiles_current_level",
        ),
        CheckConstraint(
            "target_level IN ('A1','A2','B1','B2','C1','C2')",
            name="ck_language_profiles_target_level",
        ),
        CheckConstraint(
            """
            CASE target_level
                WHEN 'A1' THEN current_level = 'A1'
                WHEN 'A2' THEN current_level IN ('A1','A2')
                WHEN 'B1' THEN current_level IN ('A1','A2','B1')
                WHEN 'B2' THEN current_level IN ('A1','A2','B1','B2')
                WHEN 'C1' THEN current_level IN ('A1','A2','B1','B2','C1')
                ELSE TRUE
            END
            """,
            name="ck_language_profiles_valid_target_level",
        ),
        Index(
            "ix_language_profiles_user_id_active",
            "user_id",
            postgresql_where=text("deleted = FALSE"),
        ),
        Index(
            "ix_language_profiles_user_active_flag",
            "user_id",
            "is_active",
            postgresql_where=text("deleted = FALSE"),
        ),
        Index(
            "ix_language_profiles_language_active",
            "language",
            postgresql_where=text("deleted = FALSE"),
        ),
        Index(
            "ix_language_profiles_last_activity",
            "last_activity_date",
            postgresql_where=text("deleted = FALSE"),
        ),
        Index(
            "ux_language_profiles_user_language_active",
            "user_id",
            "language",
            unique=True,
            postgresql_where=text("deleted = FALSE"),
        ),
    )


__all__ = ["LanguageProfile"]
