"""Repositories for storing and querying exercise history."""

from __future__ import annotations

import uuid

from sqlalchemy import Select, func, select
from sqlalchemy.orm import selectinload

from app.models.exercise import ExerciseHistory, ExerciseResultType, ExerciseType
from app.repositories.base import BaseRepository


class ExerciseHistoryRepository(BaseRepository[ExerciseHistory]):
    """Persistence helpers for exercise attempts."""

    async def record_attempt(
        self,
        *,
        user_id: uuid.UUID,
        profile_id: uuid.UUID,
        topic_id: uuid.UUID,
        exercise_type: ExerciseType,
        question: str,
        prompt: str,
        correct_answer: str,
        user_answer: str,
        result: ExerciseResultType,
        explanation: str | None,
        used_hint: bool,
        duration_seconds: int | None,
        metadata: dict[str, object] | None = None,
    ) -> ExerciseHistory:
        entry = ExerciseHistory(
            user_id=user_id,
            profile_id=profile_id,
            topic_id=topic_id,
            type=exercise_type,
            question=question,
            prompt=prompt,
            correct_answer=correct_answer,
            user_answer=user_answer,
            result=result,
            explanation=explanation,
            used_hint=used_hint,
            duration_seconds=duration_seconds,
            details=metadata or {},
        )
        await self.add(entry)
        return entry

    async def list_for_user(
        self,
        user_id: uuid.UUID,
        *,
        profile_id: uuid.UUID | None = None,
        topic_id: uuid.UUID | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[ExerciseHistory], int]:
        stmt: Select[tuple[ExerciseHistory]] = (
            select(ExerciseHistory)
            .options(selectinload(ExerciseHistory.topic))
            .where(ExerciseHistory.user_id == user_id)
            .order_by(ExerciseHistory.completed_at.desc())
            .limit(limit)
            .offset(offset)
        )
        count_stmt = select(func.count()).where(ExerciseHistory.user_id == user_id)

        if profile_id is not None:
            stmt = stmt.where(ExerciseHistory.profile_id == profile_id)
            count_stmt = count_stmt.where(ExerciseHistory.profile_id == profile_id)
        if topic_id is not None:
            stmt = stmt.where(ExerciseHistory.topic_id == topic_id)
            count_stmt = count_stmt.where(ExerciseHistory.topic_id == topic_id)

        result = await self.session.execute(stmt)
        entries = list(result.scalars().unique())

        total_result = await self.session.execute(count_stmt)
        total = int(total_result.scalar_one())
        return entries, total

    async def last_results_for_topic(
        self,
        topic_id: uuid.UUID,
        *,
        limit: int = 10,
    ) -> list[ExerciseHistory]:
        stmt = (
            select(ExerciseHistory)
            .where(ExerciseHistory.topic_id == topic_id)
            .order_by(ExerciseHistory.completed_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars())


__all__ = ["ExerciseHistoryRepository"]
