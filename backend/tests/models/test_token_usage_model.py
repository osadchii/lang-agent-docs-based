"""Tests for TokenUsage model."""

from __future__ import annotations

import uuid

from app.models.token_usage import TokenUsage


def test_token_usage_creation() -> None:
    """Test creating TokenUsage model."""
    user_id = uuid.uuid4()
    usage = TokenUsage(
        user_id=user_id,
        prompt_tokens=100,
        completion_tokens=50,
        total_tokens=150,
        estimated_cost=0.001,
        operation="chat",
        model="gpt-4o-mini",
    )

    assert usage.user_id == user_id
    assert usage.prompt_tokens == 100
    assert usage.completion_tokens == 50
    assert usage.total_tokens == 150
    assert usage.estimated_cost == 0.001


def test_token_usage_with_profile() -> None:
    """Test TokenUsage with profile_id."""
    user_id = uuid.uuid4()
    profile_id = uuid.uuid4()

    usage = TokenUsage(
        user_id=user_id,
        profile_id=profile_id,
        prompt_tokens=200,
        completion_tokens=100,
        total_tokens=300,
        estimated_cost=0.002,
    )

    assert usage.profile_id == profile_id


def test_token_usage_without_operation() -> None:
    """Test TokenUsage without operation field."""
    usage = TokenUsage(
        user_id=uuid.uuid4(),
        prompt_tokens=50,
        completion_tokens=25,
        total_tokens=75,
        estimated_cost=0.0005,
    )

    assert usage.operation is None


def test_token_usage_with_model() -> None:
    """Test TokenUsage with model field."""
    usage = TokenUsage(
        user_id=uuid.uuid4(),
        prompt_tokens=1000,
        completion_tokens=500,
        total_tokens=1500,
        estimated_cost=0.001,
        model="gpt-4o-mini",
    )

    assert usage.model == "gpt-4o-mini"
    assert usage.estimated_cost > 0
