"""Tests for TokenUsage repository."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.token_usage import TokenUsage
from app.models.user import User
from app.repositories.token_usage import TokenUsageRepository


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession) -> User:
    """Create test user."""
    user = User(
        id=uuid.uuid4(),
        telegram_id=123456789,
        first_name="Test",
        language_code="en",
        created_at=datetime.now(tz=timezone.utc),
        updated_at=datetime.now(tz=timezone.utc),
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.mark.asyncio
async def test_get_user_usage_by_period(db_session: AsyncSession, test_user: User) -> None:
    """Test getting user usage by period."""
    repo = TokenUsageRepository(db_session)

    # Create usage records
    now = datetime.utcnow()
    usage1 = TokenUsage(
        user_id=test_user.id,
        prompt_tokens=100,
        completion_tokens=50,
        total_tokens=150,
        estimated_cost=0.001,
        operation="chat",
        model="gpt-4o-mini",
        timestamp=now - timedelta(hours=2),
    )
    usage2 = TokenUsage(
        user_id=test_user.id,
        prompt_tokens=200,
        completion_tokens=100,
        total_tokens=300,
        estimated_cost=0.002,
        operation="chat",
        model="gpt-4o-mini",
        timestamp=now - timedelta(hours=1),
    )
    db_session.add_all([usage1, usage2])
    await db_session.commit()

    # Query period
    start_date = now - timedelta(hours=3)
    end_date = now
    records = await repo.get_user_usage_by_period(test_user.id, start_date, end_date)

    assert len(records) == 2
    assert records[0].total_tokens == 300  # DESC order
    assert records[1].total_tokens == 150


@pytest.mark.asyncio
async def test_get_total_tokens_by_user(db_session: AsyncSession, test_user: User) -> None:
    """Test getting total tokens for user."""
    repo = TokenUsageRepository(db_session)

    # Create usage records
    now = datetime.utcnow()
    usage1 = TokenUsage(
        user_id=test_user.id,
        prompt_tokens=100,
        completion_tokens=50,
        total_tokens=150,
        estimated_cost=0.001,
        timestamp=now - timedelta(hours=12),
    )
    usage2 = TokenUsage(
        user_id=test_user.id,
        prompt_tokens=200,
        completion_tokens=100,
        total_tokens=300,
        estimated_cost=0.002,
        timestamp=now - timedelta(hours=6),
    )
    db_session.add_all([usage1, usage2])
    await db_session.commit()

    # Get total for last day
    total = await repo.get_total_tokens_by_user(test_user.id, days=1)

    assert total == 450


@pytest.mark.asyncio
async def test_get_total_cost_by_user(db_session: AsyncSession, test_user: User) -> None:
    """Test getting total cost for user."""
    repo = TokenUsageRepository(db_session)

    # Create usage records
    now = datetime.utcnow()
    usage1 = TokenUsage(
        user_id=test_user.id,
        prompt_tokens=1000,
        completion_tokens=500,
        total_tokens=1500,
        estimated_cost=0.01,
        timestamp=now - timedelta(days=5),
    )
    usage2 = TokenUsage(
        user_id=test_user.id,
        prompt_tokens=2000,
        completion_tokens=1000,
        total_tokens=3000,
        estimated_cost=0.02,
        timestamp=now - timedelta(days=2),
    )
    db_session.add_all([usage1, usage2])
    await db_session.commit()

    # Get total cost for last 30 days
    total_cost = await repo.get_total_cost_by_user(test_user.id, days=30)

    assert total_cost == 0.03


@pytest.mark.asyncio
async def test_get_usage_by_operation(db_session: AsyncSession, test_user: User) -> None:
    """Test getting usage by operation type."""
    repo = TokenUsageRepository(db_session)

    # Create usage records with different operations
    now = datetime.utcnow()
    usage1 = TokenUsage(
        user_id=test_user.id,
        prompt_tokens=100,
        completion_tokens=50,
        total_tokens=150,
        estimated_cost=0.001,
        operation="chat",
        timestamp=now - timedelta(hours=1),
    )
    usage2 = TokenUsage(
        user_id=test_user.id,
        prompt_tokens=200,
        completion_tokens=100,
        total_tokens=300,
        estimated_cost=0.002,
        operation="generate_card",
        timestamp=now - timedelta(hours=1),
    )
    db_session.add_all([usage1, usage2])
    await db_session.commit()

    # Get tokens for 'chat' operation
    chat_tokens = await repo.get_usage_by_operation(test_user.id, "chat", days=1)
    assert chat_tokens == 150

    # Get tokens for 'generate_card' operation
    card_tokens = await repo.get_usage_by_operation(test_user.id, "generate_card", days=1)
    assert card_tokens == 300


@pytest.mark.asyncio
async def test_get_total_tokens_empty_result(db_session: AsyncSession, test_user: User) -> None:
    """Test that zero is returned when no usage records exist."""
    repo = TokenUsageRepository(db_session)

    total = await repo.get_total_tokens_by_user(test_user.id, days=1)

    assert total == 0
