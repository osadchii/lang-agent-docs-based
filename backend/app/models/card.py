"""Card models representing spaced-repetition content and review history."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import GUID, Base, SoftDeleteMixin, TimestampMixin


class CardStatus(str, enum.Enum):
    """Possible states of a card in the SRS pipeline."""

    NEW = "new"
    LEARNING = "learning"
    REVIEW = "review"


class CardRating(str, enum.Enum):
    """User feedback captured when reviewing a card."""

    KNOW = "know"
    REPEAT = "repeat"
    DONT_KNOW = "dont_know"


class Card(SoftDeleteMixin, TimestampMixin, Base):
    """Individual flashcard persisted inside a deck."""

    __tablename__ = "cards"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    deck_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("decks.id", ondelete="CASCADE"),
        nullable=False,
    )

    word: Mapped[str] = mapped_column(String(200), nullable=False)
    translation: Mapped[str] = mapped_column(String(200), nullable=False)
    example: Mapped[str] = mapped_column(Text, nullable=False)
    example_translation: Mapped[str] = mapped_column(Text, nullable=False)
    lemma: Mapped[str] = mapped_column(String(200), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)

    status: Mapped[CardStatus] = mapped_column(
        Enum(CardStatus, name="card_status_enum", native_enum=False, validate_strings=True),
        nullable=False,
        default=CardStatus.NEW,
        server_default=text("'new'"),
    )
    interval_days: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
    )
    next_review: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("timezone('utc', now())"),
    )
    reviews_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
    )
    ease_factor: Mapped[float] = mapped_column(
        Numeric(3, 2),
        nullable=False,
        default=2.5,
        server_default=text("2.50"),
    )

    last_rating: Mapped[CardRating | None] = mapped_column(
        Enum(CardRating, name="card_rating_enum", native_enum=False, validate_strings=True),
        nullable=True,
    )
    last_reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    deck = relationship("Deck", back_populates="cards")
    reviews = relationship(
        "CardReview",
        back_populates="card",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        UniqueConstraint("deck_id", "lemma", name="uq_cards_deck_lemma"),
        Index(
            "ix_cards_deck_id_active",
            "deck_id",
            postgresql_where=text("deleted = FALSE"),
        ),
        Index(
            "ix_cards_status_active",
            "status",
            postgresql_where=text("deleted = FALSE"),
        ),
        Index(
            "ix_cards_next_review_active",
            "next_review",
            postgresql_where=text("deleted = FALSE"),
        ),
        Index(
            "ix_cards_lemma_active",
            "lemma",
            postgresql_where=text("deleted = FALSE"),
        ),
    )


class CardReview(Base):
    """Historical review attempts associated with a card."""

    __tablename__ = "card_reviews"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    card_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("cards.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    rating: Mapped[CardRating] = mapped_column(
        Enum(CardRating, name="card_reviews_rating_enum", native_enum=False, validate_strings=True),
        nullable=False,
    )
    interval_before: Mapped[int] = mapped_column(Integer, nullable=False)
    interval_after: Mapped[int] = mapped_column(Integer, nullable=False)
    duration_seconds: Mapped[int | None] = mapped_column(Integer)
    reviewed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("timezone('utc', now())"),
    )

    card = relationship("Card", back_populates="reviews")
    user = relationship("User", back_populates="card_reviews")

    __table_args__ = (
        Index("ix_card_reviews_card_id", "card_id"),
        Index("ix_card_reviews_user_id", "user_id"),
        Index("ix_card_reviews_reviewed_at", "reviewed_at"),
    )


__all__ = ["Card", "CardRating", "CardReview", "CardStatus"]
