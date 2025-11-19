"""Telegram bot lifecycle management and handlers."""

from __future__ import annotations

import asyncio
import logging
import socket
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, AsyncIterator, Sequence, TypeAlias
from urllib.parse import urlsplit

from app.core.cache import CacheClient
from app.core.config import settings
from app.core.db import AsyncSessionFactory
from app.core.errors import ApplicationError
from app.repositories.card import CardRepository
from app.schemas.llm_responses import WordSuggestion
from app.services.llm import TokenUsage as LLMTokenUsage
from app.services.llm_enhanced import EnhancedLLMService
from app.services.media import ImageInput, OCRAnalysis, OCRService
from app.services.speech_to_text import SpeechToTextService
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update as TelegramUpdate
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

if TYPE_CHECKING:
    from app.models.language_profile import LanguageProfile
    from app.models.user import User
    from app.services.dialog import DialogService
    from telegram import Message as TelegramMessage, User as TelegramUser

from app.telegram.keyboards import CALLBACK_ADD_CARD

BotApplication: TypeAlias = Application[Any, Any, Any, Any, Any, Any]

WebhookEnvironments = frozenset({"staging", "production"})

GENERIC_ERROR_MESSAGE = (
    "❌ Произошла ошибка при обработке вашего сообщения. " "Попробуйте еще раз или напишите /start."
)


@dataclass(slots=True)
class _DialogContext:
    """Container that keeps user/profile/session for dialog processing."""

    user: "User"
    profile: "LanguageProfile"
    dialog_service: "DialogService"


class TelegramBot:
    """Encapsulates the python-telegram-bot application for reuse."""

    def __init__(
        self,
        *,
        token: str,
        environment: str,
        allowed_updates: Sequence[str] | None = None,
        speech_to_text_service: SpeechToTextService | None = None,
        max_voice_duration_seconds: int = 120,
        max_voice_file_size_bytes: int = 3_000_000,
        ocr_service: OCRService | None = None,
        cache_client: CacheClient | None = None,
        max_image_file_size_bytes: int | None = None,
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
        self._speech_to_text = speech_to_text_service
        self._max_voice_duration_seconds = max_voice_duration_seconds
        self._max_voice_file_size_bytes = max_voice_file_size_bytes
        self._ocr_service = ocr_service
        self._cache_client = cache_client
        self._max_image_file_size_bytes = (
            max_image_file_size_bytes
            if max_image_file_size_bytes is not None
            else (ocr_service.max_image_bytes if ocr_service is not None else None)
        )

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
        # Voice messages -> Whisper STT -> dialog flow
        self._application.add_handler(MessageHandler(filters.VOICE, self._handle_voice_message))
        # Photo messages -> OCR
        self._application.add_handler(MessageHandler(filters.PHOTO, self._handle_photo_message))
        # Callback query handler for inline buttons
        from app.telegram.callbacks import handle_callback_query

        self._application.add_handler(CallbackQueryHandler(handle_callback_query))
        self._application.add_error_handler(self._handle_error)

    @asynccontextmanager
    async def _dialog_context(
        self, *, telegram_user: "TelegramUser"
    ) -> AsyncIterator[_DialogContext]:
        """Prepare DB session, user, profile and dialog service."""
        from app.core.db import AsyncSessionFactory
        from app.repositories.conversation import ConversationRepository
        from app.repositories.user import UserRepository
        from app.services.dialog import DialogService
        from app.services.llm import LLMService
        from app.services.user import UserService

        async with AsyncSessionFactory() as session:
            user_repo = UserRepository(session)
            user_service = UserService(user_repo)

            db_user = await user_service.get_or_create_user(
                telegram_id=telegram_user.id,
                first_name=telegram_user.first_name,
                last_name=telegram_user.last_name,
                username=telegram_user.username,
                language_code=telegram_user.language_code,
            )
            await session.commit()

            conversation_repo = ConversationRepository(session)
            llm_service = LLMService(
                api_key=settings.openai_api_key.get_secret_value(),
                model=settings.llm_model,
                temperature=settings.llm_temperature,
            )
            dialog_service = DialogService(llm_service, conversation_repo)

            profile = await dialog_service.get_or_create_default_profile(db_user, session)
            await session.commit()

            yield _DialogContext(user=db_user, profile=profile, dialog_service=dialog_service)

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

        # Format welcome message (using Markdown legacy mode)
        text = (
            f"*Привет, {user.first_name}!*\n\n"
            "Я бот Lang Agent. Напиши мне вопрос или открой Mini App для практики."
        )

        # Add Mini App button
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

        text = message.text.strip()
        if not text:
            return

        try:
            async with self._dialog_context(telegram_user=user) as dialog_ctx:
                self._logger.info(
                    "Processing message",
                    extra={
                        "user_id": str(dialog_ctx.user.id),
                        "profile_id": str(dialog_ctx.profile.id),
                        "message_length": len(text),
                    },
                )

                response = await dialog_ctx.dialog_service.process_message(
                    user=dialog_ctx.user,
                    profile_id=dialog_ctx.profile.id,
                    message=text,
                )

                await self._send_dialog_response(message, response)

                self._logger.info(
                    "Message processed successfully",
                    extra={
                        "user_id": str(dialog_ctx.user.id),
                        "response_length": len(response),
                    },
                )

        except Exception as exc:
            self._logger.error(
                "Error processing text message",
                extra={"telegram_id": getattr(user, "id", None), "exception": str(exc)},
            )
            await message.reply_text(text=GENERIC_ERROR_MESSAGE)

    async def _handle_voice_message(
        self, update: TelegramUpdate, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle Telegram voice messages via Whisper transcription."""
        message = update.effective_message
        user = update.effective_user
        voice = getattr(message, "voice", None)
        speech_service = self._speech_to_text

        if message is None or user is None or voice is None:
            return

        if speech_service is None:
            await message.reply_text(
                "⚠️ Голосовые сообщения сейчас недоступны. Отправьте текст или повторите позже."
            )
            return

        duration_error = self._voice_duration_error(getattr(voice, "duration", None))
        if duration_error:
            await message.reply_text(duration_error)
            return

        declared_size_error = self._voice_size_error(getattr(voice, "file_size", None))
        if declared_size_error:
            await message.reply_text(declared_size_error)
            return

        audio_bytes = await self._download_voice_bytes(
            context=context,
            voice=voice,
            message=message,
            user_id=getattr(user, "id", None),
        )
        if audio_bytes is None:
            return

        actual_size_error = self._voice_size_error(len(audio_bytes))
        if actual_size_error:
            await message.reply_text(actual_size_error)
            return

        try:
            async with self._dialog_context(telegram_user=user) as dialog_ctx:
                transcription = await self._transcribe_voice(
                    speech_service=speech_service,
                    audio_bytes=audio_bytes,
                    profile_language=getattr(dialog_ctx.profile, "language", None),
                    message=message,
                    user_id=getattr(dialog_ctx.user, "id", None),
                )

                if transcription is None:
                    return

                text, detected_language = transcription

                response = await dialog_ctx.dialog_service.process_message(
                    user=dialog_ctx.user,
                    profile_id=dialog_ctx.profile.id,
                    message=text,
                )

                await self._send_dialog_response(message, response)

                self._logger.info(
                    "Voice message processed successfully",
                    extra={
                        "user_id": str(dialog_ctx.user.id),
                        "transcript_length": len(text),
                        "detected_language": detected_language,
                    },
                )

        except Exception as exc:
            self._logger.error(
                "Error processing voice message",
                extra={"telegram_id": getattr(user, "id", None), "exception": str(exc)},
            )
            await message.reply_text(text=GENERIC_ERROR_MESSAGE)

    async def _handle_photo_message(
        self, update: TelegramUpdate, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle Telegram photo messages by extracting text via OCR."""
        message = update.effective_message
        user = update.effective_user
        photos = getattr(message, "photo", None)
        ocr_service = self._ocr_service

        if message is None or user is None or not photos:
            return
        if ocr_service is None:
            await message.reply_text(
                "⚠️ Распознавание изображений временно недоступно. "
                "Попробуйте позже или оставьте текстовое сообщение."
            )
            return

        photo = photos[-1]
        size_error = self._image_size_error(getattr(photo, "file_size", None))
        if size_error:
            await message.reply_text(size_error)
            return

        payload = await self._download_file_bytes(
            context=context,
            file_id=getattr(photo, "file_id", None),
            message=message,
            user_id=getattr(user, "id", None),
            error_text="❌ Не удалось скачать изображение. Попробуйте ещё раз.",
        )
        if payload is None:
            return

        actual_size_error = self._image_size_error(len(payload))
        if actual_size_error:
            await message.reply_text(actual_size_error)
            return

        try:
            async with self._dialog_context(telegram_user=user) as dialog_ctx:
                profile = dialog_ctx.profile
                if profile is None:
                    await message.reply_text("⚠️ Сначала создайте языковой профиль.")
                    return

                language_code = getattr(profile, "language", "ru")
                language_name = getattr(profile, "language_name", language_code)
                interface_language = getattr(profile, "interface_language", "ru")

                analysis = await ocr_service.analyze(
                    [
                        ImageInput(
                            name="telegram-photo",
                            content_type="image/jpeg",
                            data=payload,
                        )
                    ],
                    target_language_code=language_code,
                    target_language_name=language_name,
                )

                llm_service = await self._build_enhanced_llm_service()
                suggestions: list[WordSuggestion] = []

                if llm_service is not None and analysis.combined_text:
                    session = dialog_ctx.dialog_service.conversation_repo.session
                    card_repo = CardRepository(session)
                    lemmas = await card_repo.list_lemmas_for_profile(profile.id)
                    llm_result, usage = await llm_service.suggest_words_from_text(
                        text=analysis.combined_text,
                        language=language_code,
                        interface_language=interface_language,
                        level=getattr(profile, "current_level", "A1"),
                        goals=list(getattr(profile, "goals", [])),
                        known_lemmas=lemmas,
                    )
                    suggestions = list(llm_result.suggestions[:5])
                    await self._persist_token_usage(
                        llm_service=llm_service,
                        user_id=str(dialog_ctx.user.id),
                        profile_id=str(profile.id),
                        usage=usage,
                        operation="telegram_ocr_suggestions",
                    )

                await self._send_ocr_response(
                    message=message,
                    analysis=analysis,
                    suggestions=suggestions,
                    language_name=language_name,
                )

                self._logger.info(
                    "Photo message processed",
                    extra={
                        "user_id": str(dialog_ctx.user.id),
                        "profile_id": str(profile.id),
                        "has_target_language": analysis.has_target_language,
                    },
                )
        except ApplicationError as exc:
            error_summary = f"code={exc.code}, message={exc.message}"
            self._logger.warning(
                "Photo message rejected | %s",
                error_summary,
                extra={
                    "telegram_id": getattr(user, "id", None),
                    "error_code": exc.code,
                    "details": exc.details,
                },
            )
            await message.reply_text(exc.message)
        except Exception as exc:
            self._logger.error(
                "Error processing photo message | %s",
                str(exc),
                extra={"telegram_id": getattr(user, "id", None), "exception": str(exc)},
                exc_info=True,
            )
            await message.reply_text(text=GENERIC_ERROR_MESSAGE)

    async def _send_dialog_response(self, message: "TelegramMessage", response: str) -> None:
        """Split long answers and reply with Markdown formatting."""
        from app.telegram.formatters import split_message

        message_parts = split_message(response)
        for part in message_parts:
            await message.reply_text(part, parse_mode="Markdown")

    async def _build_enhanced_llm_service(self) -> EnhancedLLMService | None:
        """Instantiate EnhancedLLMService for inline suggestions."""
        if self._cache_client is None:
            return None

        await self._cache_client.connect()
        return EnhancedLLMService(
            api_key=settings.openai_api_key.get_secret_value(),
            cache=self._cache_client,
            model=settings.llm_model,
            temperature=settings.llm_temperature,
        )

    def _voice_duration_error(self, duration: int | None) -> str | None:
        if duration and duration > self._max_voice_duration_seconds:
            return (
                f"⚠️ Голосовое сообщение слишком длинное. Максимум "
                f"{self._max_voice_duration_seconds} секунд."
            )
        return None

    def _voice_size_error(self, size_bytes: int | None) -> str | None:
        if (
            size_bytes
            and self._max_voice_file_size_bytes
            and size_bytes > self._max_voice_file_size_bytes
        ):
            return (
                "⚠️ Голосовое сообщение слишком большое. "
                "Попробуйте записать более короткий фрагмент."
            )
        return None

    def _image_size_error(self, size_bytes: int | None) -> str | None:
        if (
            size_bytes
            and self._max_image_file_size_bytes
            and size_bytes > self._max_image_file_size_bytes
        ):
            limit_mb = self._max_image_file_size_bytes // 1_000_000
            return "⚠️ Изображение слишком большое. " f"Максимальный размер: {limit_mb or 1} МБ."
        return None

    async def _send_ocr_response(
        self,
        *,
        message: "TelegramMessage",
        analysis: OCRAnalysis,
        suggestions: Sequence[WordSuggestion],
        language_name: str,
    ) -> None:
        detected_languages = sorted(
            {lang for segment in analysis.segments for lang in segment.detected_languages}
        )

        text_parts: list[str] = []
        if analysis.combined_text:
            text_parts.append(f"📄 Распознанный текст:\n\n{analysis.combined_text}")
        else:
            text_parts.append("📄 Не удалось выделить текст на выбранном языке.")

        if not analysis.has_target_language:
            if detected_languages:
                joined = ", ".join(detected_languages)
                text_parts.append(
                    f"⚠️ Текста на {language_name} не найдено. " f"Обнаруженные языки: {joined}."
                )
            else:
                text_parts.append(
                    f"⚠️ Текста на {language_name} не найдено. Попробуйте более чёткое фото."
                )

        if suggestions:
            text_parts.append("💡 Предлагаю добавить в карточки:")
            for suggestion in suggestions:
                text_parts.append(f"• {suggestion.word} — {suggestion.reason}")

        reply_markup = None
        if suggestions:
            buttons = []
            for suggestion in suggestions:
                callback_data = f"{CALLBACK_ADD_CARD}:{suggestion.word}:"
                if len(callback_data.encode("utf-8")) > 64:
                    callback_data = f"{CALLBACK_ADD_CARD}:from_message"
                buttons.append(
                    [InlineKeyboardButton(f"➕ {suggestion.word}", callback_data=callback_data)]
                )
            reply_markup = InlineKeyboardMarkup(buttons)

        await message.reply_text(
            text="\n\n".join(text_parts).strip(),
            reply_markup=reply_markup,
            disable_web_page_preview=True,
        )

    async def _persist_token_usage(
        self,
        *,
        llm_service: EnhancedLLMService,
        user_id: str,
        profile_id: str | None,
        usage: LLMTokenUsage,
        operation: str,
    ) -> None:
        try:
            async with AsyncSessionFactory() as usage_session:
                await llm_service.track_token_usage(
                    db_session=usage_session,
                    user_id=user_id,
                    profile_id=profile_id,
                    usage=usage,
                    operation=operation,
                )
        except Exception as exc:  # pragma: no cover - defensive
            self._logger.debug(
                "Token usage tracking skipped",
                extra={"error": str(exc), "operation": operation, "user_id": user_id},
            )

    async def _download_voice_bytes(
        self,
        *,
        context: ContextTypes.DEFAULT_TYPE,
        voice: object,
        message: "TelegramMessage",
        user_id: object | None,
    ) -> bytes | None:
        file_id = getattr(voice, "file_id", None)
        return await self._download_file_bytes(
            context=context,
            file_id=file_id,
            message=message,
            user_id=user_id,
            error_text="❌ Не удалось скачать голосовое сообщение. Попробуйте еще раз.",
        )

    async def _download_file_bytes(
        self,
        *,
        context: ContextTypes.DEFAULT_TYPE,
        file_id: str | None,
        message: "TelegramMessage",
        user_id: object | None,
        error_text: str,
    ) -> bytes | None:
        if context is None or context.bot is None or not file_id:
            return None

        try:
            telegram_file = await context.bot.get_file(file_id)
            payload = await telegram_file.download_as_bytearray()
            return bytes(payload)
        except Exception as exc:  # pragma: no cover - telegram internals
            self._logger.error(
                "Failed to download file",
                extra={"telegram_id": user_id, "error": str(exc)},
            )
            await message.reply_text(error_text)
        return None

    async def _transcribe_voice(
        self,
        *,
        speech_service: SpeechToTextService,
        audio_bytes: bytes,
        profile_language: str | None,
        message: "TelegramMessage",
        user_id: object | None,
    ) -> tuple[str, str | None] | None:
        try:
            transcript = await speech_service.transcribe(
                audio_bytes, language_hint=profile_language
            )
        except Exception as exc:
            self._logger.error(
                "Failed to transcribe voice message",
                extra={"telegram_id": user_id, "error": str(exc)},
            )
            await message.reply_text(
                "❌ Не удалось распознать голосовое сообщение. "
                "Попробуйте текст или повторите позже."
            )
            return None

        text = transcript.text.strip()
        if not text:
            await message.reply_text(
                "❌ Не удалось распознать речь. Попробуйте записать сообщение ещё раз."
            )
            return None

        if (
            transcript.detected_language
            and profile_language
            and transcript.detected_language != profile_language
        ):
            self._logger.info(
                "Voice language differs from profile",
                extra={
                    "expected_language": profile_language,
                    "detected_language": transcript.detected_language,
                    "transcript_length": len(text),
                    "user_id": str(user_id) if user_id is not None else None,
                },
            )

        return text, transcript.detected_language

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
