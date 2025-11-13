"""Endpoints handling Telegram bot webhooks."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Request, status

from app.core.config import settings
from app.core.errors import ApplicationError, ErrorCode
from app.telegram import telegram_bot

logger = logging.getLogger("app.api.telegram")
router = APIRouter()


@router.post(
    "/telegram-webhook/{bot_token}",
    status_code=status.HTTP_200_OK,
    summary="Handle Telegram webhook updates",
    tags=["telegram"],
)
async def telegram_webhook(bot_token: str, request: Request) -> dict[str, bool]:
    """Validate the incoming bot token and forward the update to the bot application."""
    expected_token = settings.telegram_bot_token.get_secret_value()
    if bot_token != expected_token:
        raise ApplicationError(
            code=ErrorCode.FORBIDDEN,
            message="Invalid Telegram bot token.",
            status_code=status.HTTP_403_FORBIDDEN,
        )

    payload = await request.json()
    await telegram_bot.process_payload(payload)

    logger.info("Telegram update processed")
    return {"ok": True}
