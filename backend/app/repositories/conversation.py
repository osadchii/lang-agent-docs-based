"""Conversation history repository."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import delete, select

from app.models.conversation import ConversationMessage, MessageRole
from app.repositories.base import BaseRepository


class ConversationRepository(BaseRepository[ConversationMessage]):
    """Persistence logic for conversation history."""

    async def add_message(
        self,
        *,
        user_id: uuid.UUID,
        profile_id: uuid.UUID,
        role: MessageRole,
        content: str,
        tokens: int = 0,
    ) -> ConversationMessage:
        message = ConversationMessage(
            user_id=user_id,
            profile_id=profile_id,
            role=role,
            content=content,
            tokens=tokens,
            timestamp=datetime.now(tz=timezone.utc),
        )
        await self.add(message)
        await self.session.refresh(message)
        return message

    async def get_recent_for_profile(
        self,
        *,
        user_id: uuid.UUID,
        profile_id: uuid.UUID,
        limit: int = 20,
    ) -> list[ConversationMessage]:
        stmt = (
            select(ConversationMessage)
            .where(
                ConversationMessage.user_id == user_id,
                ConversationMessage.profile_id == profile_id,
            )
            .order_by(
                ConversationMessage.timestamp.desc(),
                ConversationMessage.id.desc(),
            )
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars())

    async def delete_for_user(self, user_id: uuid.UUID) -> int:
        stmt = delete(ConversationMessage).where(ConversationMessage.user_id == user_id)
        result = await self.session.execute(stmt)
        rowcount = getattr(result, "rowcount", 0)
        return int(rowcount or 0)


__all__ = ["ConversationRepository"]
