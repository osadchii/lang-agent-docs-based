"""Business logic for deck listing and retrieval."""

from __future__ import annotations

import uuid

from app.core.errors import ErrorCode, NotFoundError
from app.models.deck import Deck
from app.models.user import User
from app.repositories.deck import DeckRepository
from app.repositories.group import GroupMaterialRepository
from app.repositories.language_profile import LanguageProfileRepository


class DeckService:
    """High-level operations for deck management."""

    def __init__(self, repository: DeckRepository) -> None:
        self.repository = repository
        self.group_material_repo: GroupMaterialRepository | None = None
        self.profile_repo: LanguageProfileRepository | None = None

    def with_group_access(
        self,
        group_material_repo: GroupMaterialRepository,
        profile_repo: LanguageProfileRepository,
    ) -> DeckService:
        """Attach optional dependencies for group-aware listing."""
        self.group_material_repo = group_material_repo
        self.profile_repo = profile_repo
        return self

    async def list_decks(
        self,
        user: User,
        *,
        profile_id: uuid.UUID | None = None,
        include_group: bool = True,
    ) -> list[Deck]:
        """Return decks belonging to the provided user."""
        decks = await self.repository.list_for_user(
            user.id,
            profile_id=profile_id,
            include_group=include_group,
        )
        if not include_group or self.group_material_repo is None:
            return decks

        language_filter = None
        if profile_id is not None and self.profile_repo is not None:
            profile = await self.profile_repo.get_by_id_for_user(profile_id, user.id)
            if profile is not None:
                language_filter = profile.language

        shared = await self.group_material_repo.list_shared_decks_for_user(
            user.id,
            language=language_filter,
        )
        return decks + shared

    async def get_user_deck(self, user: User, deck_id: uuid.UUID) -> Deck:
        """Fetch a single deck ensuring it belongs to the current user."""
        deck = await self.repository.get_for_user(deck_id, user.id)
        if deck is None:
            raise NotFoundError(
                code=ErrorCode.DECK_NOT_FOUND,
                message="?????? ?? ??????.",
            )
        return deck


__all__ = ["DeckService"]
