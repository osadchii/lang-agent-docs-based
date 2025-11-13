"""Telegram bot lifecycle management and handlers."""

from __future__ import annotations

import asyncio
import logging
import socket
from typing import Any, Sequence, TypeAlias
from urllib.parse import urlsplit

from telegram import Update as TelegramUpdate
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

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
            self._logger.info("Skipping webhook configuration: BACKEND_DOMAIN is not set")
            return

        if self._environment not in WebhookEnvironments:
            self._logger.info(
                "Skipping webhook configuration for environment; use polling in development",
                extra={"environment": self._environment},
            )
            return

        await self.ensure_started()

        normalized_base = webhook_base_url.rstrip("/")
        parsed_base = urlsplit(normalized_base)
        host = parsed_base.hostname
        if not host:
            self._logger.error(
                "Skipping webhook configuration: BACKEND_DOMAIN is invalid (missing hostname)",
                extra={"environment": self._environment, "webhook_base": normalized_base},
            )
            return

        if not self._is_hostname_resolvable(host):
            self._logger.error(
                "Skipping webhook configuration: webhook host is not resolvable",
                extra={
                    "environment": self._environment,
                    "hostname": host,
                    "webhook_base": normalized_base,
                },
            )
            return

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
        # Text message handler (excluding commands)
        self._application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_message)
        )
        # Callback query handler for inline buttons
        from app.telegram.callbacks import handle_callback_query

        self._application.add_handler(CallbackQueryHandler(handle_callback_query))
        self._application.add_error_handler(self._handle_error)

    async def _handle_start(
        self, update: TelegramUpdate, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle /start command: create or get user, update last_activity."""
        del context  # context is unused for the basic greeting
        message = update.effective_message
        user = update.effective_user

        if message is None or user is None:
            return

        # Import here to avoid circular dependencies
        from app.core.db import AsyncSessionFactory
        from app.repositories.user import UserRepository
        from app.services.user import UserService

        # Create user or update last_activity
        async with AsyncSessionFactory() as session:
            repository = UserRepository(session)
            service = UserService(repository)

            db_user = await service.get_or_create_user(
                telegram_id=user.id,
                first_name=user.first_name,
                last_name=user.last_name,
                username=user.username,
                language_code=user.language_code,
            )
            await session.commit()

            self._logger.info(
                "User processed in /start",
                extra={
                    "telegram_id": user.id,
                    "user_id": str(db_user.id),
                    "is_new": db_user.created_at == db_user.updated_at,
                },
            )

        from app.telegram.keyboards import create_mini_app_button
        from telegram import InlineKeyboardMarkup

        # Форматируем приветственное сообщение (используем Markdown legacy mode)
        text = (
            f"*Привет, {user.first_name}!*\n\n"
            "Я бот Lang Agent. Напиши мне вопрос или открой Mini App для практики."
        )

        # Добавляем кнопку открытия Mini App
        keyboard = InlineKeyboardMarkup([[create_mini_app_button()]])

        await message.reply_text(
            text=text,
            parse_mode="Markdown",
            reply_markup=keyboard,
        )

    async def _handle_message(
        self, update: TelegramUpdate, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle text messages: process through LLM and respond."""
        del context  # context is unused
        message = update.effective_message
        user = update.effective_user

        if message is None or user is None or message.text is None:
            return

        # Import here to avoid circular dependencies
        from app.core.config import settings
        from app.core.db import AsyncSessionFactory
        from app.repositories.conversation import ConversationRepository
        from app.repositories.user import UserRepository
        from app.services.dialog import DialogService
        from app.services.llm import LLMService
        from app.services.user import UserService

        try:
            async with AsyncSessionFactory() as session:
                # 1. Get or create user
                user_repo = UserRepository(session)
                user_service = UserService(user_repo)

                db_user = await user_service.get_or_create_user(
                    telegram_id=user.id,
                    first_name=user.first_name,
                    last_name=user.last_name,
                    username=user.username,
                    language_code=user.language_code,
                )
                await session.commit()

                # 2. Get or create default language profile
                conversation_repo = ConversationRepository(session)
                llm_service = LLMService(api_key=settings.openai_api_key.get_secret_value())
                dialog_service = DialogService(llm_service, conversation_repo)

                profile = await dialog_service.get_or_create_default_profile(db_user, session)
                await session.commit()

                self._logger.info(
                    "Processing message",
                    extra={
                        "user_id": str(db_user.id),
                        "profile_id": str(profile.id),
                        "message_length": len(message.text),
                    },
                )

                # 3. Process message through DialogService
                response = await dialog_service.process_message(
                    user=db_user,
                    profile_id=profile.id,
                    message=message.text,
                )

                # 4. Format and send response
                from app.telegram.formatters import split_message

                # Разбиваем ответ если слишком длинный
                # NOTE: LLM генерирует Markdown форматирование (согласно backend-bot-responses.md)
                # Используем parse_mode="Markdown" для корректного отображения
                message_parts = split_message(response)

                # Отправляем части сообщения с Markdown форматированием
                for part in message_parts:
                    await message.reply_text(part, parse_mode="Markdown")

                self._logger.info(
                    "Message processed successfully",
                    extra={
                        "user_id": str(db_user.id),
                        "response_length": len(response),
                        "parts_count": len(message_parts),
                    },
                )

        except Exception as e:
            self._logger.error(
                f"Error processing message: {e}",
                extra={"telegram_id": user.id, "exception": str(e)},
            )

            # Используем plain text для сообщений об ошибках
            error_text = (
                "❌ Произошла ошибка при обработке вашего сообщения. "
                "Попробуйте еще раз или напишите /start."
            )

            await message.reply_text(text=error_text)

    async def _handle_error(self, update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
        self._logger.error(
            "Telegram handler error",
            extra={"exception": context.error, "update": update},
        )

    @staticmethod
    def _is_hostname_resolvable(host: str) -> bool:
        try:
            socket.getaddrinfo(host, None)
        except socket.gaierror:
            return False
        return True


# Re-export Update for test monkeypatching.
Update = TelegramUpdate

__all__ = ["TelegramBot", "Update"]
