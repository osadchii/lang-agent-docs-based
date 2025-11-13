"""Telegram bot bindings used across the backend."""

from __future__ import annotations

from app.core.config import settings
from app.telegram.bot import TelegramBot

telegram_bot = TelegramBot(
    token=settings.telegram_bot_token.get_secret_value(),
    environment=settings.environment,
)

__all__ = ["telegram_bot", "TelegramBot"]
