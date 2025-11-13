from __future__ import annotations

import json
from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient

from app.core.config import settings
from app.main import app
from app.telegram import telegram_bot


@pytest.mark.asyncio
async def test_webhook_rejects_invalid_token(monkeypatch: pytest.MonkeyPatch) -> None:
    spy = AsyncMock()
    monkeypatch.setattr(telegram_bot, "process_payload", spy)

    async with AsyncClient(app=app, base_url="http://testserver") as client:
        response = await client.post(
            "/telegram-webhook/invalid",
            content=json.dumps({"update_id": 1}),
            headers={"Content-Type": "application/json"},
        )

    assert response.status_code == 403
    payload = response.json()
    assert payload["error"]["code"] == "FORBIDDEN"
    spy.assert_not_called()


@pytest.mark.asyncio
async def test_webhook_dispatches_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = {"update_id": 42, "message": {"text": "/start"}}
    async_spy = AsyncMock()
    monkeypatch.setattr(telegram_bot, "process_payload", async_spy)
    token = settings.telegram_bot_token.get_secret_value()

    async with AsyncClient(app=app, base_url="http://testserver") as client:
        response = await client.post(
            f"/telegram-webhook/{token}",
            content=json.dumps(payload),
            headers={"Content-Type": "application/json"},
        )

    assert response.status_code == 200
    assert response.json() == {"ok": True}
    async_spy.assert_awaited_once_with(payload)
