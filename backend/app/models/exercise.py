"""Models representing generated exercise attempts."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, Text, func, text
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.models.base import GUID, Base


class ExerciseType(str, enum.Enum):
    """Supported exercise interaction modes."""

    FREE_TEXT = "free_text"
    MULTIPLE_CHOICE = "multiple_choice"


class ExerciseResultType(str, enum.Enum):
    """Result categories stored for each attempt."""

    CORRECT = "correct"
    PARTIAL = "partial"
    INCORRECT = "incorrect"


class ExerciseHistory(Base):
    """Historical record of user attempts for adaptive tracking."""

    __tablename__ = "exercise_history"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    topic_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("topics.id", ondelete="CASCADE"),
        nullable=False,
    )
    profile_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("language_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )

    type: Mapped[ExerciseType] = mapped_column(
        Enum(ExerciseType, name="exercise_type_enum", native_enum=False, validate_strings=True),
        nullable=False,
    )
    question: Mapped[str] = mapped_column(Text, nullable=False)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    correct_answer: Mapped[str] = mapped_column(Text, nullable=False)

    user_answer: Mapped[str] = mapped_column(Text, nullable=False)
    result: Mapped[ExerciseResultType] = mapped_column(
        Enum(
            ExerciseResultType,
            name="exercise_result_enum",
            native_enum=False,
            validate_strings=True,
        ),
        nullable=False,
    )
    explanation: Mapped[str | None] = mapped_column(Text)
    used_hint: Mapped[bool] = mapped_column(
        nullable=False,
        default=False,
        server_default=text("false"),
    )
    duration_seconds: Mapped[int | None] = mapped_column(Integer)

    details: Mapped[dict[str, object]] = mapped_column(
        "metadata",
        MutableDict.as_mutable(JSON()),
        default=dict,
        nullable=False,
    )

    completed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    user = relationship("User", back_populates="exercise_attempts")
    topic = relationship("Topic", back_populates="exercises")
    profile = relationship("LanguageProfile", back_populates="exercises")

    __table_args__ = (
        Index("ix_exercise_history_user_id", "user_id"),
        Index("ix_exercise_history_topic_id", "topic_id"),
        Index("ix_exercise_history_profile_id", "profile_id"),
        Index("ix_exercise_history_result", "result"),
        Index("ix_exercise_history_completed_at", "completed_at"),
    )


__all__ = ["ExerciseHistory", "ExerciseResultType", "ExerciseType"]
