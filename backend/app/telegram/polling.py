"""Run the Telegram bot in long-polling mode for local development."""

from __future__ import annotations

from app.core.config import settings
from app.core.logging import configure_logging
from app.telegram import telegram_bot
from app.telegram.bot import BotApplication


def run() -> None:
    """Start the telegram bot using long polling."""
    configure_logging(settings.log_level)
    application: BotApplication = telegram_bot.application
    application.run_polling(
        allowed_updates=list(telegram_bot.allowed_updates),
        drop_pending_updates=True,
    )


if __name__ == "__main__":
    run()
