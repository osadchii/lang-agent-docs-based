from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.card import Card, CardRating, CardReview, CardStatus
from app.models.conversation import ConversationMessage, MessageRole
from app.models.deck import Deck
from app.models.exercise import ExerciseHistory, ExerciseResultType, ExerciseType
from app.models.group import Group
from app.models.language_profile import LanguageProfile
from app.models.topic import Topic, TopicType
from app.models.user import User
from app.repositories.admin import AdminRepository
from app.services.admin import (
    AdminMetricsPeriod,
    AdminService,
    AdminUserActivity,
    AdminUserSort,
    AdminUserStatus,
)


async def _seed_data(session: AsyncSession) -> tuple[AdminService, User, User, User]:
    now = datetime.now(tz=timezone.utc)
    admin_user = User(
        id=uuid.uuid4(),
        telegram_id=1,
        first_name="Admin",
        is_premium=True,
        is_admin=True,
    )
    premium_user = User(
        id=uuid.uuid4(),
        telegram_id=2,
        first_name="Premium",
        is_premium=True,
        is_admin=False,
        last_activity=now - timedelta(days=1),
    )
    free_user = User(
        id=uuid.uuid4(),
        telegram_id=3,
        first_name="Free",
        is_premium=False,
        is_admin=False,
        last_activity=now - timedelta(days=90),
    )
    session.add_all([admin_user, premium_user, free_user])
    await session.flush()

    profile = LanguageProfile(
        id=uuid.uuid4(),
        user_id=premium_user.id,
        language="es",
        language_name="Spanish",
        current_level="A2",
        target_level="B1",
        goals=["travel"],
        interface_language="ru",
        is_active=True,
        streak=5,
    )
    deck = Deck(
        id=uuid.uuid4(),
        profile_id=profile.id,
        owner_id=premium_user.id,
        name="Everyday phrases",
        cards_count=20,
        new_cards_count=5,
        due_cards_count=2,
        is_active=True,
    )
    card = Card(
        id=uuid.uuid4(),
        deck_id=deck.id,
        word="hola",
        translation="hello",
        example="hola amigo",
        example_translation="hello friend",
        lemma="hola",
        status=CardStatus.NEW,
    )
    topic = Topic(
        id=uuid.uuid4(),
        profile_id=profile.id,
        name="Greetings",
        type=TopicType.GRAMMAR,
        description="Basic greetings",
    )

    exercise_entry = ExerciseHistory(
        id=uuid.uuid4(),
        user_id=premium_user.id,
        profile_id=profile.id,
        topic_id=topic.id,
        type=ExerciseType.FREE_TEXT,
        question="How to greet?",
        prompt="Greet someone",
        correct_answer="hola",
        user_answer="hola",
        result=ExerciseResultType.CORRECT,
        explanation=None,
        used_hint=False,
        duration_seconds=45,
        details={},
        completed_at=now,
    )
    review = CardReview(
        id=uuid.uuid4(),
        card_id=card.id,
        user_id=premium_user.id,
        rating=CardRating.KNOW,
        interval_before=0,
        interval_after=1,
        duration_seconds=30,
        reviewed_at=now,
    )
    conversation = ConversationMessage(
        id=uuid.uuid4(),
        user_id=premium_user.id,
        profile_id=profile.id,
        role=MessageRole.USER,
        content="Hola!",
        tokens=5,
        timestamp=now,
    )
    group = Group(
        id=uuid.uuid4(),
        owner_id=premium_user.id,
        name="Learners",
        description="Practice group",
        members_count=1,
        max_members=5,
    )

    session.add_all(
        [
            profile,
            deck,
            card,
            topic,
            exercise_entry,
            review,
            conversation,
            group,
        ]
    )
    await session.commit()
    service = AdminService(AdminRepository(session))
    return service, admin_user, premium_user, free_user


@pytest.mark.asyncio
async def test_list_users_applies_filters(db_session: AsyncSession) -> None:
    service, _, premium_user, _ = await _seed_data(db_session)

    result = await service.list_users(
        status=AdminUserStatus.PREMIUM,
        activity=AdminUserActivity.ACTIVE_30D,
        language="es",
        sort=AdminUserSort.CARDS_COUNT,
        limit=10,
        offset=0,
    )

    assert result.total == 1
    assert len(result.users) == 1
    entry = result.users[0]
    assert entry.id == premium_user.id
    assert entry.languages == ["es"]
    assert entry.cards_count == 20
    assert entry.exercises_count == 1
    assert entry.streak == 5


@pytest.mark.asyncio
async def test_grant_manual_premium_updates_user(db_session: AsyncSession) -> None:
    service, admin_user, _, free_user = await _seed_data(db_session)

    grant = await service.grant_manual_premium(
        admin=admin_user,
        user_id=free_user.id,
        duration_days=30,
        reason="Bug compensation",
    )
    await service.session.commit()

    await db_session.refresh(free_user)

    assert grant.user_id == free_user.id
    assert grant.is_premium is True
    assert grant.reason == "Bug compensation"
    assert free_user.is_premium is True
    assert free_user.premium_expires_at is not None


@pytest.mark.asyncio
async def test_get_metrics_returns_snapshot(db_session: AsyncSession) -> None:
    service, _, _, _ = await _seed_data(db_session)

    metrics = await service.get_metrics(AdminMetricsPeriod.DAYS_30)

    assert metrics.users.total >= 2
    assert metrics.users.premium >= 1
    assert metrics.activity.cards_studied == 1
    assert metrics.activity.exercises_completed == 1
    assert metrics.activity.average_session_minutes > 0
