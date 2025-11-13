"""
Repository for token usage records.

Handles database operations for LLM token usage tracking.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.token_usage import TokenUsage
from app.repositories.base import BaseRepository


class TokenUsageRepository(BaseRepository[TokenUsage]):
    """Repository for TokenUsage model."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def get_user_usage_by_period(
        self,
        user_id: UUID,
        start_date: datetime,
        end_date: datetime | None = None,
    ) -> list[TokenUsage]:
        """
        Get token usage for user within date range.

        Args:
            user_id: User ID
            start_date: Start date
            end_date: End date (default: now)

        Returns:
            List of TokenUsage records
        """
        if end_date is None:
            end_date = datetime.utcnow()

        stmt = (
            select(TokenUsage)
            .where(
                TokenUsage.user_id == user_id,
                TokenUsage.timestamp >= start_date,
                TokenUsage.timestamp <= end_date,
            )
            .order_by(TokenUsage.timestamp.desc())
        )

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_total_tokens_by_user(
        self,
        user_id: UUID,
        days: int = 1,
    ) -> int:
        """
        Get total tokens used by user in last N days.

        Args:
            user_id: User ID
            days: Number of days to look back

        Returns:
            Total token count
        """
        start_date = datetime.utcnow() - timedelta(days=days)

        stmt = select(func.sum(TokenUsage.total_tokens)).where(
            TokenUsage.user_id == user_id,
            TokenUsage.timestamp >= start_date,
        )

        result = await self.session.execute(stmt)
        total = result.scalar_one_or_none()
        return total or 0

    async def get_total_cost_by_user(
        self,
        user_id: UUID,
        days: int = 30,
    ) -> float:
        """
        Get total cost for user in last N days.

        Args:
            user_id: User ID
            days: Number of days to look back

        Returns:
            Total cost in USD
        """
        start_date = datetime.utcnow() - timedelta(days=days)

        stmt = select(func.sum(TokenUsage.estimated_cost)).where(
            TokenUsage.user_id == user_id,
            TokenUsage.timestamp >= start_date,
        )

        result = await self.session.execute(stmt)
        total = result.scalar_one_or_none()
        return float(total or 0.0)

    async def get_usage_by_operation(
        self,
        user_id: UUID,
        operation: str,
        days: int = 1,
    ) -> int:
        """
        Get token usage for specific operation.

        Args:
            user_id: User ID
            operation: Operation name
            days: Number of days to look back

        Returns:
            Total tokens for operation
        """
        start_date = datetime.utcnow() - timedelta(days=days)

        stmt = select(func.sum(TokenUsage.total_tokens)).where(
            TokenUsage.user_id == user_id,
            TokenUsage.operation == operation,
            TokenUsage.timestamp >= start_date,
        )

        result = await self.session.execute(stmt)
        total = result.scalar_one_or_none()
        return total or 0


__all__ = ["TokenUsageRepository"]
