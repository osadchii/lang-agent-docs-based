"""Repositories encapsulating Topic persistence logic."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import datetime, timezone

from sqlalchemy import Select, select, update
from sqlalchemy.orm import selectinload

from app.models.exercise import ExerciseResultType
from app.models.language_profile import LanguageProfile
from app.models.topic import Topic, TopicType
from app.repositories.base import BaseRepository


class TopicRepository(BaseRepository[Topic]):
    """Query helpers for Topic entities scoped to a user."""

    async def list_for_user(
        self,
        user_id: uuid.UUID,
        *,
        profile_id: uuid.UUID | None = None,
        topic_type: TopicType | None = None,
        include_group: bool = True,
    ) -> list[Topic]:
        stmt: Select[tuple[Topic]] = (
            select(Topic)
            .join(LanguageProfile, Topic.profile_id == LanguageProfile.id)
            .options(selectinload(Topic.owner))
            .where(
                Topic.deleted.is_(False),
                LanguageProfile.deleted.is_(False),
                LanguageProfile.user_id == user_id,
            )
            .order_by(Topic.is_active.desc(), Topic.created_at.asc())
        )

        if profile_id is not None:
            stmt = stmt.where(Topic.profile_id == profile_id)
        if topic_type is not None:
            stmt = stmt.where(Topic.type == topic_type)
        if not include_group:
            stmt = stmt.where(Topic.is_group.is_(False))

        result = await self.session.execute(stmt)
        return list(result.scalars().unique())

    async def get_for_user(
        self,
        topic_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> Topic | None:
        stmt = (
            select(Topic)
            .join(LanguageProfile, Topic.profile_id == LanguageProfile.id)
            .options(selectinload(Topic.owner))
            .where(
                Topic.id == topic_id,
                Topic.deleted.is_(False),
                LanguageProfile.deleted.is_(False),
                LanguageProfile.user_id == user_id,
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_ids(self, topic_ids: Sequence[uuid.UUID]) -> list[Topic]:
        if not topic_ids:
            return []
        stmt = (
            select(Topic)
            .options(selectinload(Topic.owner))
            .where(Topic.id.in_(topic_ids), Topic.deleted.is_(False))
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().unique())

    async def deactivate_profile_topics(
        self,
        profile_id: uuid.UUID,
        *,
        exclude: uuid.UUID | None = None,
    ) -> None:
        stmt = update(Topic).where(
            Topic.profile_id == profile_id,
            Topic.deleted.is_(False),
        )
        if exclude is not None:
            stmt = stmt.where(Topic.id != exclude)
        await self.session.execute(stmt.values(is_active=False))

    async def soft_delete(self, topic: Topic) -> None:
        topic.deleted = True
        topic.deleted_at = datetime.now(tz=timezone.utc)
        topic.is_active = False
        await self.session.flush()

    async def update_stats(self, topic: Topic, result: ExerciseResultType) -> Topic:
        topic.exercises_count += 1
        if result == ExerciseResultType.CORRECT:
            topic.correct_count += 1
        elif result == ExerciseResultType.PARTIAL:
            topic.partial_count += 1
        else:
            topic.incorrect_count += 1

        numerator = topic.correct_count + topic.partial_count * 0.5
        accuracy = numerator / topic.exercises_count if topic.exercises_count else 0.0
        topic.accuracy = min(max(round(accuracy, 4), 0.0), 1.0)
        await self.session.flush()
        return topic


__all__ = ["TopicRepository"]
