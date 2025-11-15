from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ApplicationError, NotFoundError
from app.models.language_profile import LanguageProfile
from app.models.topic import Topic, TopicType
from app.models.user import User
from app.repositories.language_profile import LanguageProfileRepository
from app.repositories.topic import TopicRepository
from app.schemas.llm_responses import TopicSuggestion, TopicSuggestions
from app.schemas.topic import TopicCreateRequest, TopicSuggestRequest, TopicUpdateRequest
from app.services.llm import TokenUsage
from app.services.topic import TopicService


def _build_user() -> User:
    return User(
        id=uuid.uuid4(),
        telegram_id=987654,
        first_name="Service",
        last_name=None,
        username="svc",
        is_premium=False,
        is_admin=False,
    )


def _build_profile(user: User) -> LanguageProfile:
    now = datetime.now(tz=timezone.utc)
    return LanguageProfile(
        id=uuid.uuid4(),
        user_id=user.id,
        language="es",
        language_name="?????????",
        current_level="A2",
        target_level="B1",
        goals=["travel"],
        interface_language="ru",
        is_active=True,
        created_at=now,
        updated_at=now,
    )


def _create_topic(profile: LanguageProfile, owner: User, *, name: str = "Basics") -> Topic:
    now = datetime.now(tz=timezone.utc)
    return Topic(
        id=uuid.uuid4(),
        profile_id=profile.id,
        name=name,
        description=None,
        type=TopicType.GRAMMAR,
        owner_id=owner.id,
        is_active=False,
        created_at=now,
        updated_at=now,
    )


class LLMStub:
    def __init__(self) -> None:
        self.tracked: list[str] = []

    async def suggest_topics(
        self,
        *,
        profile_id: str,
        language: str,
        language_name: str,
        level: str,
        target_level: str,
        goals: list[str],
    ) -> tuple[TopicSuggestions, TokenUsage]:
        suggestion = TopicSuggestion(
            name="Travel",
            description="Travel basics",
            type="situation",
            reason="User wants to travel",
            examples=["Airport check-in"],
        )
        return TopicSuggestions(topics=[suggestion]), TokenUsage(10, 5, 15)

    async def track_token_usage(
        self,
        *,
        db_session: AsyncSession,
        user_id: str,
        profile_id: str | None,
        usage: TokenUsage,
        operation: str | None = None,
    ) -> None:
        self.tracked.append(operation or "unknown")


@pytest.mark.asyncio
async def test_first_topic_becomes_active(db_session: AsyncSession) -> None:
    user = _build_user()
    profile = _build_profile(user)
    db_session.add_all([user, profile])
    await db_session.commit()

    topic_repo = TopicRepository(db_session)
    profile_repo = LanguageProfileRepository(db_session)
    service = TopicService(topic_repo, profile_repo, llm_service=None)

    payload = TopicCreateRequest(
        profile_id=profile.id, name="Basics", description=None, type=TopicType.GRAMMAR
    )
    first = await service.create_topic(user, payload)
    assert first.is_active is True
    await service.session.commit()

    second_payload = TopicCreateRequest(
        profile_id=profile.id,
        name="Advanced",
        description=None,
        type=TopicType.GRAMMAR,
    )
    second = await service.create_topic(user, second_payload)
    assert second.is_active is False


@pytest.mark.asyncio
async def test_get_topic_raises_for_missing_resource(db_session: AsyncSession) -> None:
    user = _build_user()
    db_session.add(user)
    await db_session.commit()

    service = TopicService(TopicRepository(db_session), LanguageProfileRepository(db_session))

    with pytest.raises(NotFoundError):
        await service.get_topic(user, uuid.uuid4())


@pytest.mark.asyncio
async def test_update_topic_changes_fields(db_session: AsyncSession) -> None:
    user = _build_user()
    profile = _build_profile(user)
    topic = _create_topic(profile, user, name="Old")
    db_session.add_all([user, profile, topic])
    await db_session.commit()

    service = TopicService(TopicRepository(db_session), LanguageProfileRepository(db_session))
    updated = await service.update_topic(
        user,
        topic.id,
        TopicUpdateRequest(name="New", description="Updated"),
    )

    assert updated.name == "New"
    assert updated.description == "Updated"


@pytest.mark.asyncio
async def test_delete_topic_marks_entity_deleted(db_session: AsyncSession) -> None:
    user = _build_user()
    profile = _build_profile(user)
    topic = _create_topic(profile, user)
    db_session.add_all([user, profile, topic])
    await db_session.commit()

    service = TopicService(TopicRepository(db_session), LanguageProfileRepository(db_session))
    await service.delete_topic(user, topic.id)

    assert topic.deleted is True


@pytest.mark.asyncio
async def test_activate_topic_switches_flag(db_session: AsyncSession) -> None:
    user = _build_user()
    profile = _build_profile(user)
    first = _create_topic(profile, user, name="One")
    first.is_active = True
    second = _create_topic(profile, user, name="Two")
    db_session.add_all([user, profile, first, second])
    await db_session.commit()

    service = TopicService(TopicRepository(db_session), LanguageProfileRepository(db_session))
    activated = await service.activate_topic(user, second.id)

    assert activated.is_active is True
    assert first.is_active is False


@pytest.mark.asyncio
async def test_suggest_topics_requires_llm(db_session: AsyncSession) -> None:
    user = _build_user()
    profile = _build_profile(user)
    db_session.add_all([user, profile])
    await db_session.commit()

    service = TopicService(TopicRepository(db_session), LanguageProfileRepository(db_session))
    payload = TopicSuggestRequest(profile_id=profile.id)

    with pytest.raises(ApplicationError):
        await service.suggest_topics(user, payload)


@pytest.mark.asyncio
async def test_suggest_topics_returns_data_and_tracks_usage(db_session: AsyncSession) -> None:
    user = _build_user()
    profile = _build_profile(user)
    db_session.add_all([user, profile])
    await db_session.commit()

    llm_stub = LLMStub()
    service = TopicService(
        TopicRepository(db_session),
        LanguageProfileRepository(db_session),
        llm_service=llm_stub,
    )
    payload = TopicSuggestRequest(profile_id=profile.id)

    result = await service.suggest_topics(user, payload)

    assert result.topics[0].name == "Travel"
    assert llm_stub.tracked == ["suggest_topics"]
