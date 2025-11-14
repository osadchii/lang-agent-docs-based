"""User ORM model."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Index, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import GUID, Base, SoftDeleteMixin, TimestampMixin


class User(SoftDeleteMixin, TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    telegram_id: Mapped[int] = mapped_column(BigInteger, nullable=False, unique=False)

    first_name: Mapped[str] = mapped_column(String(255))
    last_name: Mapped[str | None] = mapped_column(String(255))
    username: Mapped[str | None] = mapped_column(String(255))

    is_premium: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    premium_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    trial_ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    trial_used: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))

    is_admin: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))

    timezone: Mapped[str] = mapped_column(String(50), server_default=text("'UTC'"))
    language_code: Mapped[str | None] = mapped_column(String(10))

    last_activity: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    language_profiles = relationship(
        "LanguageProfile",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    conversation_messages = relationship(
        "ConversationMessage",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    token_usage = relationship(
        "TokenUsage",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    owned_decks = relationship("Deck", back_populates="owner")
    owned_topics = relationship("Topic", back_populates="owner")
    card_reviews = relationship(
        "CardReview",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    exercise_attempts = relationship(
        "ExerciseHistory",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index(
            "ux_users_telegram_id_active",
            "telegram_id",
            unique=True,
            postgresql_where=text("deleted = FALSE"),
        ),
        Index(
            "ix_users_is_premium_active",
            "is_premium",
            postgresql_where=text("deleted = FALSE"),
        ),
        Index(
            "ix_users_last_activity_active",
            "last_activity",
            postgresql_where=text("deleted = FALSE"),
        ),
        Index("ix_users_created_at", "created_at"),
    )


__all__ = ["User"]
