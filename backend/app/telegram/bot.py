"""Telegram bot lifecycle management and handlers."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Sequence, TypeAlias

from telegram import Update as TelegramUpdate
from telegram.ext import Application, ApplicationBuilder, CommandHandler, ContextTypes

BotApplication: TypeAlias = Application[Any, Any, Any, Any, Any, Any]

WebhookEnvironments = frozenset({"staging", "production"})


class TelegramBot:
    """Encapsulates the python-telegram-bot application for reuse."""

    def __init__(
        self,
        *,
        token: str,
        environment: str,
        allowed_updates: Sequence[str] | None = None,
    ) -> None:
        self._token = token
        self._environment = environment
        self._allowed_updates: tuple[str, ...] = tuple(
            allowed_updates or ("message", "callback_query")
        )
        self._application: BotApplication = ApplicationBuilder().token(token).build()
        self._lifecycle_lock = asyncio.Lock()
        self._started = False
        self._logger = logging.getLogger("app.telegram.bot")

        self._register_handlers()

    @property
    def application(self) -> BotApplication:
        """Return the underlying Application instance."""
        return self._application

    @property
    def allowed_updates(self) -> tuple[str, ...]:
        """Return the configured list of allowed updates."""
        return self._allowed_updates

    async def start(self) -> None:
        """Initialize the telegram application lazily."""
        async with self._lifecycle_lock:
            if self._started:
                return

            await self._application.initialize()
            await self._application.start()
            self._started = True
            self._logger.info("Telegram application initialized")

    async def shutdown(self) -> None:
        """Stop and shutdown the telegram application."""
        async with self._lifecycle_lock:
            if not self._started:
                return

            await self._application.stop()
            await self._application.shutdown()
            self._started = False
            self._logger.info("Telegram application shut down")

    async def ensure_started(self) -> None:
        """Guarantee that the bot application is running."""
        if not self._started:
            await self.start()

    async def sync_webhook(self, webhook_base_url: str | None) -> None:
        """
        Configure Telegram webhook for production/staging environments.

        Local and test environments rely on polling via app.telegram.polling.
        """
        if not webhook_base_url:
            self._logger.info("Skipping webhook configuration: TELEGRAM_WEBHOOK_URL is not set")
            return

        if self._environment not in WebhookEnvironments:
            self._logger.info(
                "Skipping webhook configuration for environment; use polling in development",
                extra={"environment": self._environment},
            )
            return

        await self.ensure_started()

        normalized_base = webhook_base_url.rstrip("/")
        webhook_url = f"{normalized_base}/telegram-webhook/{{token}}"
        await self._application.bot.set_webhook(
            url=webhook_url.format(token=self._token),
            drop_pending_updates=True,
            allowed_updates=list(self._allowed_updates),
        )
        self._logger.info(
            "Telegram webhook configured",
            extra={"environment": self._environment, "webhook_base": normalized_base},
        )

    async def process_payload(self, payload: dict[str, Any]) -> None:
        """Deserialize a Telegram update and dispatch it into the application."""
        await self.ensure_started()
        update = Update.de_json(payload, self._application.bot)
        await self._application.process_update(update)

    def _register_handlers(self) -> None:
        self._application.add_handler(CommandHandler("start", self._handle_start))
        self._application.add_error_handler(self._handle_error)

    async def _handle_start(
        self, update: TelegramUpdate, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        del context  # context is unused for the basic greeting
        message = update.effective_message
        if message is None:
            return

        first_name = update.effective_user.first_name if update.effective_user else None
        greeting = f"Привет, {first_name}!" if first_name else "Привет!"
        await message.reply_text(
            f"{greeting} Я бот Lang Agent. Напиши мне вопрос или открой Mini App для практики."
        )

    async def _handle_error(self, update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
        self._logger.error(
            "Telegram handler error",
            extra={"exception": context.error, "update": update},
        )


# Re-export Update for test monkeypatching.
Update = TelegramUpdate

__all__ = ["TelegramBot", "Update"]
