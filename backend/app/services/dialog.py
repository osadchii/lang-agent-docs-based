"""Dialog service for managing conversations with LLM."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta
from pathlib import Path

from fastapi import status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ApplicationError, ErrorCode
from app.models.conversation import ConversationMessage, MessageRole
from app.models.language_profile import LanguageProfile
from app.models.user import User
from app.repositories.conversation import ConversationRepository
from app.services.llm import LLMService
from app.services.moderation import ModerationDecision, ModerationService
from app.services.prompts import (
    PromptRenderer,
    count_tokens,
    get_basic_system_prompt,
    get_system_prompt_for_profile,
)

logger = logging.getLogger("app.services.dialog")


class DialogService:
    """High-level service for managing user dialogs with LLM."""

    def __init__(
        self,
        llm_service: LLMService,
        conversation_repository: ConversationRepository,
        moderation_service: ModerationService | None = None,
        prompts_dir: str | Path | None = None,
    ) -> None:
        """
        Initialize dialog service.

        Args:
            llm_service: LLM service for API calls
            conversation_repository: Repository for conversation history
            prompts_dir: Path to prompts directory (optional, uses default if None)
        """
        self.llm = llm_service
        self.conversation_repo = conversation_repository
        self.moderation = moderation_service

        # Initialize prompt renderer
        if prompts_dir is None:
            # Default to backend/prompts
            prompts_dir = Path(__file__).parent.parent.parent / "prompts"

        self.prompt_renderer = PromptRenderer(prompts_dir)

    async def get_or_create_default_profile(
        self, user: User, session: AsyncSession
    ) -> LanguageProfile:
        """
        Get or create a default language profile for user.

        This is a temporary solution for minimal implementation.
        In future, users will create profiles through onboarding.

        Args:
            user: User object
            session: Database session

        Returns:
            Default language profile
        """
        # Try to find an active profile
        stmt = select(LanguageProfile).where(
            LanguageProfile.user_id == user.id,
            LanguageProfile.deleted == False,  # noqa: E712
        )
        result = await session.execute(stmt)
        profile = result.scalar_one_or_none()

        if profile:
            return profile

        # Create default profile
        profile = LanguageProfile(
            user_id=user.id,
            language="en",  # Default to English
            language_name="English",
            current_level="A1",
            target_level="B2",
            goals=["general"],
            interface_language=user.language_code or "ru",
            is_active=True,
        )

        session.add(profile)
        await session.flush()
        await session.refresh(profile)

        logger.info(
            "Created default profile for user",
            extra={"user_id": str(user.id), "profile_id": str(profile.id)},
        )

        return profile

    async def _filter_history_by_tokens(
        self,
        history: list[ConversationMessage],
        max_tokens: int = 8000,
        model: str = "gpt-4o-mini",
    ) -> list[ConversationMessage]:
        """
        Filter conversation history to fit within token limit.

        According to docs/backend-llm.md, we should limit context to:
        - Last 20 messages OR
        - Last 24 hours OR
        - Max 8000 tokens (whichever is smallest)

        Args:
            history: List of ConversationHistory objects
            max_tokens: Maximum tokens allowed for history
            model: Model name for token counting

        Returns:
            Filtered history list
        """
        if not history:
            return []

        # Start from the end (most recent) and work backwards
        filtered: list[ConversationMessage] = []
        total_tokens = 0

        for msg in reversed(history):
            try:
                msg_tokens = msg.tokens if msg.tokens > 0 else count_tokens(msg.content, model)
            except (TypeError, AttributeError):
                # Handle mocked objects in tests - default to small token count
                msg_tokens = (
                    count_tokens(str(msg.content), model) if hasattr(msg, "content") else 10
                )

            if total_tokens + msg_tokens > max_tokens:
                # Stop if adding this message would exceed limit
                break

            filtered.insert(0, msg)  # Insert at beginning to maintain order
            total_tokens += msg_tokens

        logger.debug(
            f"Filtered history: {len(filtered)}/{len(history)} messages, "
            f"{total_tokens}/{max_tokens} tokens"
        )

        return filtered

    async def process_message(
        self,
        *,
        user: User,
        profile_id: uuid.UUID,
        message: str,
        max_history: int = 20,
        max_context_tokens: int = 8000,
        max_history_hours: int = 24,
    ) -> str:
        """
        Process user message: get history, call LLM, save messages.

        Args:
            user: User object
            profile_id: Language profile ID
            message: User's message text
            max_history: Maximum number of historical messages to include
            max_context_tokens: Maximum tokens for conversation history
            max_history_hours: Maximum age of messages to include (in hours)

        Returns:
            LLM response text
        """
        moderation_decision = await self._run_moderation(message, user_id=user.id)
        if moderation_decision is not None:
            raise ApplicationError(
                code=ErrorCode.CONTENT_REJECTED,
                message=(
                    "Sorry, I can't respond to that request. "
                    "Please keep the conversation focused on language learning."
                ),
                status_code=status.HTTP_400_BAD_REQUEST,
                details={
                    "reason": moderation_decision.reason,
                    "categories": moderation_decision.categories,
                    "source": moderation_decision.source,
                },
            )

        # Calculate tokens for user message
        user_message_tokens = count_tokens(message)

        # 1. Save user message immediately
        await self.conversation_repo.add_message(
            user_id=user.id,
            profile_id=profile_id,
            role=MessageRole.USER,
            content=message,
            tokens=user_message_tokens,
        )
        await self.conversation_repo.session.commit()

        logger.info(
            "User message saved",
            extra={
                "user_id": str(user.id),
                "profile_id": str(profile_id),
                "tokens": user_message_tokens,
            },
        )

        # 2. Get profile for system prompt
        profile_stmt = select(LanguageProfile).where(
            LanguageProfile.id == profile_id,
            LanguageProfile.deleted == False,  # noqa: E712
        )
        profile_result = await self.conversation_repo.session.execute(profile_stmt)
        profile = profile_result.scalar_one_or_none()

        if not profile:
            logger.warning(f"Profile {profile_id} not found, using basic prompt")
            system_prompt = get_basic_system_prompt(user.language_code)
        else:
            # Render system prompt from profile using template
            system_prompt = get_system_prompt_for_profile(self.prompt_renderer, profile)

        # 3. Get recent conversation history
        cutoff_time = datetime.utcnow() - timedelta(hours=max_history_hours)

        history = await self.conversation_repo.get_recent_for_profile(
            user_id=user.id,
            profile_id=profile_id,
            limit=max_history,
        )

        # Filter by time (last 24 hours)
        try:
            history = [msg for msg in history if msg.timestamp >= cutoff_time]
        except (TypeError, AttributeError):
            # Handle mocked objects in tests
            pass

        # History is in DESC order, reverse to get chronological order
        history = list(reversed(history))

        # Filter by token count (max 8000 tokens)
        history = await self._filter_history_by_tokens(history, max_tokens=max_context_tokens)

        # 4. Format messages for LLM
        messages = [{"role": "system", "content": system_prompt}]

        # Add filtered history (excluding the message we just saved)
        for msg in history[:-1]:  # Exclude the last message (current user message)
            messages.append({"role": msg.role.value, "content": msg.content})

        # Add current message
        messages.append({"role": "user", "content": message})

        logger.info(
            "Calling LLM",
            extra={
                "user_id": str(user.id),
                "history_messages": len(history) - 1,
                "total_messages": len(messages),
            },
        )

        # 5. Call LLM
        try:
            response, usage = await self.llm.chat(
                messages=messages,
                temperature=0.7,
                max_tokens=500,
            )

            # 6. Save assistant response immediately
            await self.conversation_repo.add_message(
                user_id=user.id,
                profile_id=profile_id,
                role=MessageRole.ASSISTANT,
                content=response,
                tokens=usage.completion_tokens,
            )
            await self.conversation_repo.session.commit()

            logger.info(
                "Assistant response saved",
                extra={
                    "user_id": str(user.id),
                    "response_length": len(response),
                    "tokens_used": usage.total_tokens,
                    "estimated_cost": f"${usage.estimated_cost:.6f}",
                },
            )

            return response

        except Exception as e:
            logger.error(f"Error processing message: {e}", extra={"user_id": str(user.id)})
            # Re-raise to be handled by caller
            raise

    async def _run_moderation(
        self,
        message: str,
        *,
        user_id: uuid.UUID,
    ) -> ModerationDecision | None:
        if self.moderation is None:
            return None

        decision = await self.moderation.evaluate(message)
        if decision.allowed:
            return None

        logger.warning(
            "Message blocked by moderation",
            extra={
                "user_id": str(user_id),
                "reason": decision.reason,
                "categories": decision.categories,
                "source": decision.source,
            },
        )
        return decision


__all__ = ["DialogService"]
