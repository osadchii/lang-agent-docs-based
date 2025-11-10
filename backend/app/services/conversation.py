"""Conversation service exposing high-level history operations."""

from __future__ import annotations

import uuid
from typing import Sequence

from app.models.conversation import ConversationMessage, MessageRole
from app.repositories.conversation import ConversationRepository


class ConversationService:
    """Coordinates conversation repository methods."""

    def __init__(self, repository: ConversationRepository) -> None:
        self.repository = repository

    async def add_message(
        self,
        *,
        user_id: uuid.UUID,
        profile_id: uuid.UUID,
        role: MessageRole,
        content: str,
        tokens: int = 0,
    ) -> ConversationMessage:
        return await self.repository.add_message(
            user_id=user_id,
            profile_id=profile_id,
            role=role,
            content=content,
            tokens=tokens,
        )

    async def get_recent(
        self,
        *,
        user_id: uuid.UUID,
        profile_id: uuid.UUID,
        limit: int = 20,
    ) -> list[ConversationMessage]:
        return await self.repository.get_recent_for_profile(
            user_id=user_id,
            profile_id=profile_id,
            limit=limit,
        )


__all__ = ["ConversationService"]
