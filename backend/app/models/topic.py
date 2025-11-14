"""Topic model describing thematic exercise groups."""

from __future__ import annotations

import enum
import uuid

from sqlalchemy import Boolean, Enum, ForeignKey, Index, Integer, Numeric, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import GUID, Base, SoftDeleteMixin, TimestampMixin


class TopicType(str, enum.Enum):
    """Supported topic categories."""

    GRAMMAR = "grammar"
    VOCABULARY = "vocabulary"
    SITUATION = "situation"


class Topic(SoftDeleteMixin, TimestampMixin, Base):
    """Learning topic tied to a specific language profile."""

    __tablename__ = "topics"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    profile_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("language_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    type: Mapped[TopicType] = mapped_column(
        Enum(TopicType, name="topic_type_enum", native_enum=False, validate_strings=True),
        nullable=False,
    )

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

    exercises_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
    )
    correct_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
    )
    partial_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
    )
    incorrect_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
    )
    accuracy: Mapped[float] = mapped_column(
        Numeric(5, 2),
        nullable=False,
        default=0.0,
        server_default=text("0.00"),
    )

    profile = relationship(
        "LanguageProfile",
        back_populates="topics",
        innerjoin=True,
    )
    owner = relationship("User", back_populates="owned_topics")
    exercises = relationship(
        "ExerciseHistory",
        back_populates="topic",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index(
            "ix_topics_profile_id_active",
            "profile_id",
            postgresql_where=text("deleted = FALSE"),
        ),
        Index(
            "ix_topics_profile_active_flag",
            "profile_id",
            "is_active",
            postgresql_where=text("deleted = FALSE"),
        ),
        Index(
            "ix_topics_type_active",
            "type",
            postgresql_where=text("deleted = FALSE"),
        ),
        Index(
            "ix_topics_is_group_active",
            "is_group",
            postgresql_where=text("deleted = FALSE"),
        ),
        Index(
            "ux_topics_active_per_profile",
            "profile_id",
            unique=True,
            postgresql_where=text("is_active = TRUE AND deleted = FALSE"),
            sqlite_where=text("is_active = 1 AND deleted = 0"),
        ),
    )


__all__ = ["Topic", "TopicType"]
