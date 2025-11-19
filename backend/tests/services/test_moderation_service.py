"""Tests for ModerationService heuristics and OpenAI integration."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from openai import OpenAIError

from app.services.moderation import ModerationService


@pytest.mark.asyncio
async def test_moderation_service_allows_clean_text() -> None:
    client = MagicMock()
    client.moderations = SimpleNamespace(
        create=AsyncMock(return_value=SimpleNamespace(results=[SimpleNamespace(flagged=False)]))
    )

    service = ModerationService(api_key="test", client=client)

    decision = await service.evaluate("Tell me about basic verbs")

    assert decision.allowed is True
    assert decision.reason is None
    assert decision.categories == ()
    client.moderations.create.assert_awaited_once()


@pytest.mark.asyncio
async def test_moderation_service_blocks_local_spam_without_api_call() -> None:
    client = MagicMock()
    client.moderations = SimpleNamespace(create=AsyncMock())

    service = ModerationService(api_key="test", client=client)

    decision = await service.evaluate("!!!!!!!!!!!!!!")

    assert decision.allowed is False
    assert decision.source == "local"
    client.moderations.create.assert_not_called()


@pytest.mark.asyncio
async def test_moderation_service_blocks_flagged_categories() -> None:
    flagged = SimpleNamespace(
        flagged=True,
        categories={"hate": True, "self-harm": False},
        category_scores={"hate": 0.98, "self-harm": 0.01},
    )
    client = MagicMock()
    client.moderations = SimpleNamespace(
        create=AsyncMock(return_value=SimpleNamespace(results=[flagged]))
    )

    service = ModerationService(api_key="test", client=client)

    decision = await service.evaluate("bad request")

    assert decision.allowed is False
    assert decision.source == "openai"
    assert decision.categories == ("hate",)


@pytest.mark.asyncio
async def test_moderation_service_fail_open_on_api_error() -> None:
    client = MagicMock()
    client.moderations = SimpleNamespace(
        create=AsyncMock(side_effect=OpenAIError("temporary moderation failure"))
    )

    service = ModerationService(api_key="test", client=client)

    decision = await service.evaluate("normal request")

    assert decision.allowed is True
    assert decision.error is not None
