"""
Token usage tracking model for LLM API calls.

Tracks token consumption and estimated costs for each LLM request,
enabling cost analysis and monitoring per user/profile.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DECIMAL, BigInteger, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin


class TokenUsage(Base, TimestampMixin):
    """Records token usage for LLM API calls."""

    __tablename__ = "token_usage"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    profile_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("language_profiles.id", ondelete="SET NULL"), nullable=True
    )

    # Token counts
    prompt_tokens: Mapped[int] = mapped_column(BigInteger, nullable=False)
    completion_tokens: Mapped[int] = mapped_column(BigInteger, nullable=False)
    total_tokens: Mapped[int] = mapped_column(BigInteger, nullable=False)

    # Cost tracking (in USD)
    estimated_cost: Mapped[float] = mapped_column(DECIMAL(10, 6), nullable=False)

    # Context
    operation: Mapped[str | None] = mapped_column(
        String(100), nullable=True, comment="Operation type (e.g., 'generate_card', 'chat')"
    )
    model: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="LLM model used")

    # Timestamp is inherited from TimestampMixin (created_at, updated_at)
    # But we also want a specific timestamp for the LLM call
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="token_usage")  # type: ignore[name-defined]  # noqa: F821
    profile: Mapped["LanguageProfile | None"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "LanguageProfile", back_populates="token_usage"
    )

    def __repr__(self) -> str:
        return (
            f"<TokenUsage(id={self.id}, user_id={self.user_id}, "
            f"total_tokens={self.total_tokens}, cost=${self.estimated_cost:.6f})>"
        )


__all__ = ["TokenUsage"]
