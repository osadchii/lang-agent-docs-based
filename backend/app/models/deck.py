"""Deck model storing spaced-repetition collections."""

from __future__ import annotations

import uuid

from sqlalchemy import Boolean, ForeignKey, Index, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import GUID, Base, SoftDeleteMixin, TimestampMixin


class Deck(SoftDeleteMixin, TimestampMixin, Base):
    """A collection of cards grouped for a specific language profile."""

    __tablename__ = "decks"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    profile_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("language_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
    )
    is_group: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
    )

    owner_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(),
        ForeignKey("users.id", ondelete="SET NULL"),
    )

    cards_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
    )
    new_cards_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
    )
    due_cards_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
    )

    profile = relationship(
        "LanguageProfile",
        back_populates="decks",
        innerjoin=True,
    )
    owner = relationship("User", back_populates="owned_decks")
    cards = relationship("Card", back_populates="deck", cascade="all, delete-orphan")

    __table_args__ = (
        Index(
            "ix_decks_profile_id_active",
            "profile_id",
            postgresql_where=text("deleted = FALSE"),
        ),
        Index(
            "ix_decks_profile_active_flag",
            "profile_id",
            "is_active",
            postgresql_where=text("deleted = FALSE"),
        ),
        Index(
            "ix_decks_is_group_active",
            "is_group",
            postgresql_where=text("deleted = FALSE"),
        ),
        Index(
            "ix_decks_owner_id_active",
            "owner_id",
            postgresql_where=text("deleted = FALSE"),
        ),
        Index(
            "ux_decks_active_per_profile",
            "profile_id",
            unique=True,
            postgresql_where=text("is_active = TRUE AND deleted = FALSE"),
            sqlite_where=text("is_active = 1 AND deleted = 0"),
        ),
    )


__all__ = ["Deck"]
