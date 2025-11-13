"""Dialog service for managing conversations with LLM."""

from __future__ import annotations

import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import MessageRole
from app.models.language_profile import LanguageProfile
from app.models.user import User
from app.repositories.conversation import ConversationRepository
from app.services.llm import LLMService, get_basic_system_prompt

logger = logging.getLogger("app.services.dialog")


class DialogService:
    """High-level service for managing user dialogs with LLM."""

    def __init__(
        self,
        llm_service: LLMService,
        conversation_repository: ConversationRepository,
    ) -> None:
        """
        Initialize dialog service.

        Args:
            llm_service: LLM service for API calls
            conversation_repository: Repository for conversation history
        """
        self.llm = llm_service
        self.conversation_repo = conversation_repository

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
        from sqlalchemy import select

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

    async def process_message(
        self,
        *,
        user: User,
        profile_id: uuid.UUID,
        message: str,
        max_history: int = 20,
    ) -> str:
        """
        Process user message: get history, call LLM, save messages.

        Args:
            user: User object
            profile_id: Language profile ID
            message: User's message text
            max_history: Maximum number of historical messages to include

        Returns:
            LLM response text
        """
        # 1. Save user message immediately
        await self.conversation_repo.add_message(
            user_id=user.id,
            profile_id=profile_id,
            role=MessageRole.USER,
            content=message,
            tokens=0,  # TODO: Calculate tokens with tiktoken
        )
        await self.conversation_repo.session.commit()

        logger.info(
            "User message saved",
            extra={"user_id": str(user.id), "profile_id": str(profile_id)},
        )

        # 2. Get recent conversation history
        history = await self.conversation_repo.get_recent_for_profile(
            user_id=user.id,
            profile_id=profile_id,
            limit=max_history,
        )

        # History is in DESC order, reverse to get chronological order
        history = list(reversed(history))

        # 3. Format messages for LLM
        system_prompt = get_basic_system_prompt(user.language_code)
        messages = [{"role": "system", "content": system_prompt}]

        # Add history (excluding the message we just saved)
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

        # 4. Call LLM
        try:
            response, usage = await self.llm.chat(
                messages=messages,
                temperature=0.7,
                max_tokens=500,
            )

            # 5. Save assistant response immediately
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


__all__ = ["DialogService"]
