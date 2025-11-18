"""Business logic around Topic CRUD and LLM suggestions."""

from __future__ import annotations

import logging
import uuid

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ApplicationError, ErrorCode, NotFoundError
from app.models.topic import Topic, TopicType
from app.models.user import User
from app.repositories.group import GroupMaterialRepository
from app.repositories.language_profile import LanguageProfileRepository
from app.repositories.topic import TopicRepository
from app.schemas.llm_responses import TopicSuggestions
from app.schemas.topic import TopicCreateRequest, TopicSuggestRequest, TopicUpdateRequest
from app.services.llm_enhanced import EnhancedLLMService

logger = logging.getLogger("app.services.topics")


class TopicService:
    """Coordinate topic CRUD and LLM-driven suggestions."""

    def __init__(
        self,
        topic_repo: TopicRepository,
        profile_repo: LanguageProfileRepository,
        group_material_repo: GroupMaterialRepository | None = None,
        llm_service: EnhancedLLMService | None = None,
    ) -> None:
        self.topic_repo = topic_repo
        self.profile_repo = profile_repo
        self.group_material_repo = group_material_repo
        self.llm_service = llm_service

    @property
    def session(self) -> AsyncSession:
        """Expose shared session for transaction control."""
        return self.topic_repo.session

    async def list_topics(
        self,
        user: User,
        *,
        profile_id: uuid.UUID | None = None,
        topic_type: TopicType | None = None,
        include_group: bool = True,
    ) -> list[Topic]:
        """Return topics belonging to the provided user."""
        topics = await self.topic_repo.list_for_user(
            user.id,
            profile_id=profile_id,
            topic_type=topic_type,
            include_group=include_group,
        )
        if not include_group or self.group_material_repo is None:
            return topics

        language_filter = None
        if profile_id is not None:
            profile = await self.profile_repo.get_by_id_for_user(profile_id, user.id)
            if profile is not None:
                language_filter = profile.language

        grouped = await self.group_material_repo.list_shared_topics_for_user(
            user.id,
            language=language_filter,
        )
        return topics + grouped

    async def create_topic(self, user: User, payload: TopicCreateRequest) -> Topic:
        """Create a topic bound to the user's profile."""
        profile = await self.profile_repo.get_by_id_for_user(payload.profile_id, user.id)
        if profile is None:
            raise NotFoundError(
                code=ErrorCode.PROFILE_NOT_FOUND,
                message="??????? ?? ??????.",
            )

        topic = Topic(
            profile_id=profile.id,
            name=payload.name,
            description=payload.description,
            type=payload.type,
            owner_id=user.id,
        )

        has_active = await self._profile_has_active_topic(profile.id)
        topic.is_active = not has_active

        await self.topic_repo.add(topic)
        await self.session.refresh(topic)
        return topic

    async def get_topic(self, user: User, topic_id: uuid.UUID) -> Topic:
        """Fetch a single topic ensuring it belongs to the user."""
        topic = await self.topic_repo.get_for_user(topic_id, user.id)
        if topic is None:
            raise NotFoundError(
                code=ErrorCode.TOPIC_NOT_FOUND,
                message="???? ?? ??????.",
            )
        return topic

    async def update_topic(
        self,
        user: User,
        topic_id: uuid.UUID,
        payload: TopicUpdateRequest,
    ) -> Topic:
        """Update topic metadata."""
        topic = await self.get_topic(user, topic_id)
        if payload.name is not None:
            topic.name = payload.name
        if payload.description is not None:
            topic.description = payload.description
        await self.session.flush()
        await self.session.refresh(topic)
        return topic

    async def delete_topic(self, user: User, topic_id: uuid.UUID) -> None:
        """Soft delete a topic."""
        topic = await self.get_topic(user, topic_id)
        await self.topic_repo.soft_delete(topic)

    async def activate_topic(self, user: User, topic_id: uuid.UUID) -> Topic:
        """Mark the topic as active and deactivate other profile topics."""
        topic = await self.get_topic(user, topic_id)
        await self.topic_repo.deactivate_profile_topics(topic.profile_id, exclude=topic.id)
        topic.is_active = True
        await self.session.flush()
        await self.session.refresh(topic)
        return topic

    async def suggest_topics(
        self,
        user: User,
        request: TopicSuggestRequest,
    ) -> TopicSuggestions:
        """Call LLM to suggest topics tailored to the profile."""
        if self.llm_service is None:
            raise ApplicationError(
                code=ErrorCode.SERVICE_UNAVAILABLE,
                message="LLM service is currently unavailable.",
            )

        profile = await self.profile_repo.get_by_id_for_user(request.profile_id, user.id)
        if profile is None:
            raise NotFoundError(
                code=ErrorCode.PROFILE_NOT_FOUND,
                message="??????? ?? ??????.",
            )

        suggestions, usage = await self.llm_service.suggest_topics(
            profile_id=str(profile.id),
            language=profile.language,
            language_name=profile.language_name,
            level=profile.current_level,
            target_level=profile.target_level,
            goals=list(profile.goals),
        )
        await self.llm_service.track_token_usage(
            db_session=self.session,
            user_id=str(user.id),
            profile_id=str(profile.id),
            usage=usage,
            operation="suggest_topics",
        )
        logger.info(
            "Generated topic suggestions",
            extra={"user_id": str(user.id), "profile_id": str(profile.id)},
        )
        return suggestions

    async def _profile_has_active_topic(self, profile_id: uuid.UUID) -> bool:
        stmt: Select[tuple[int]] = select(func.count()).where(
            Topic.profile_id == profile_id,
            Topic.deleted.is_(False),
            Topic.is_active.is_(True),
        )
        result = await self.session.execute(stmt)
        return bool(result.scalar_one())


__all__ = ["TopicService"]
