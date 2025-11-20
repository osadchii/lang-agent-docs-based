"""Card service covering listing, creation, scheduling, and review recording."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone

from app.core.errors import ErrorCode, NotFoundError
from app.models.card import Card, CardRating, CardStatus
from app.models.deck import Deck
from app.models.user import User
from app.repositories.card import CardRepository, CardReviewRepository
from app.repositories.deck import DeckRepository
from app.repositories.language_profile import LanguageProfileRepository
from app.schemas.card import CardCreateRequest, CardCreateResult, CardResponse, RateCardRequest
from app.services.llm_enhanced import EnhancedLLMService

logger = logging.getLogger("app.services.cards")


class CardService:
    """Coordinate card lifecycle operations using repositories and LLM helpers."""

    MAX_PAGE_SIZE = 100
    REPEAT_DELAY_MINUTES = 10
    INTERVAL_MULTIPLIER = 2.5

    def __init__(
        self,
        card_repo: CardRepository,
        deck_repo: DeckRepository,
        profile_repo: LanguageProfileRepository | None = None,
        review_repo: CardReviewRepository | None = None,
    ) -> None:
        self.card_repo = card_repo
        self.deck_repo = deck_repo
        self.profile_repo = profile_repo
        self.review_repo = review_repo

    #
    # Query operations
    #
    async def list_cards(
        self,
        user: User,
        *,
        deck_id: uuid.UUID,
        status: CardStatus | None = None,
        search: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[Card], int]:
        """Return paginated cards for a specific deck owned by the user."""
        deck = await self.deck_repo.get_for_user(deck_id, user.id)
        if deck is None:
            raise NotFoundError(
                code=ErrorCode.DECK_NOT_FOUND,
                message="Колода не найдена.",
            )

        safe_limit = max(1, min(limit, self.MAX_PAGE_SIZE))
        safe_offset = max(0, offset)

        return await self.card_repo.list_for_deck(
            deck.id,
            status=status,
            search=search,
            limit=safe_limit,
            offset=safe_offset,
        )

    async def get_card(self, user: User, card_id: uuid.UUID) -> Card:
        """Fetch a single card for the user."""
        card = await self.card_repo.get_for_user(card_id, user.id)
        if card is None:
            raise NotFoundError(
                code=ErrorCode.CARD_NOT_FOUND,
                message="Карточка не найдена.",
            )
        return card

    async def get_next_card(self, user: User, *, deck_id: uuid.UUID | None = None) -> Card | None:
        """Return the next card for study (due first, then new)."""
        resolved_deck = await self._resolve_deck(user, deck_id=deck_id)
        if resolved_deck is None:
            return None
        return await self.card_repo.get_next_for_deck(resolved_deck.id)

    #
    # Mutating operations
    #
    async def create_cards(
        self,
        user: User,
        payload: CardCreateRequest,
        *,
        llm_service: EnhancedLLMService,
    ) -> CardCreateResult:
        """
        Create one or more cards using LLM generation.

        Returns aggregated result with created items and skipped duplicates.
        """
        if self.profile_repo is None:
            raise RuntimeError("ProfileRepository is required for card creation.")

        deck = await self._get_deck_for_user(user, payload.deck_id)
        profile = await self.profile_repo.get_by_id_for_user(deck.profile_id, user.id)
        if profile is None:
            raise NotFoundError(
                code=ErrorCode.PROFILE_NOT_FOUND,
                message="Профиль не найден.",
            )

        result = CardCreateResult()
        for word in payload.words:
            try:
                card_content, usage = await llm_service.generate_card(
                    word=word,
                    language=profile.language,
                    language_name=profile.language_name,
                    level=profile.current_level,
                    goals=profile.goals,
                )

                duplicate = await self.card_repo.find_by_lemma(deck.id, card_content.lemma)
                if duplicate:
                    result.duplicates.append(card_content.lemma)
                    continue

                card = Card(
                    deck_id=deck.id,
                    word=card_content.word,
                    translation=card_content.translation,
                    example=card_content.example,
                    example_translation=card_content.example_translation,
                    lemma=card_content.lemma,
                    notes=card_content.notes,
                    status=CardStatus.NEW,
                    interval_days=0,
                    next_review=datetime.now(timezone.utc),
                    reviews_count=0,
                )

                await self.card_repo.add(card)
                await llm_service.track_token_usage(
                    db_session=self.card_repo.session,
                    user_id=str(user.id),
                    profile_id=str(profile.id),
                    usage=usage,
                    operation="generate_card",
                )
                result.created.append(CardResponse.model_validate(card))
                await self.card_repo.session.commit()
            except Exception:  # noqa: BLE001
                logger.exception("Failed to create card for word %s", word)
                result.failed.append(word)
                await self.card_repo.session.rollback()

        await self._update_deck_counters(deck)
        await self.card_repo.session.commit()
        return result

    async def rate_card(self, user: User, payload: RateCardRequest) -> Card:
        """Apply a spaced-repetition rating, update scheduling, and persist review."""
        if self.review_repo is None:
            raise RuntimeError("CardReviewRepository is required for rating cards.")

        card = await self.card_repo.get_for_user(payload.card_id, user.id)
        if card is None:
            raise NotFoundError(
                code=ErrorCode.CARD_NOT_FOUND,
                message="Карточка не найдена.",
            )

        interval_before = card.interval_days
        new_interval, new_status = self._calculate_next_interval(
            card.interval_days, card.status, payload.rating
        )
        now = datetime.now(timezone.utc)
        next_review = self._compute_next_review(new_interval, payload.rating, now)

        card.interval_days = new_interval
        card.status = new_status
        card.next_review = next_review
        card.reviews_count += 1
        card.last_rating = payload.rating
        card.last_reviewed_at = now

        await self.review_repo.record_review(
            card_id=card.id,
            user_id=user.id,
            rating=payload.rating,
            interval_before=interval_before,
            interval_after=new_interval,
            duration_seconds=payload.duration_seconds,
        )

        deck = await self.deck_repo.get_for_user(card.deck_id, user.id)
        if deck:
            await self._update_deck_counters(deck)

        await self.card_repo.session.commit()
        return card

    #
    # Helpers
    #
    async def _resolve_deck(self, user: User, *, deck_id: uuid.UUID | None) -> Deck | None:
        """Resolve deck by id or active deck for active profile."""
        if deck_id:
            return await self._get_deck_for_user(user, deck_id)

        if self.profile_repo is None:
            return None

        profile = await self.profile_repo.get_active_for_user(user.id)
        if profile is None:
            return None

        deck = await self.deck_repo.get_active_for_profile(profile.id, user_id=user.id)
        if deck is None:
            logger.info("No active deck found for profile %s", profile.id)
        return deck

    async def _get_deck_for_user(self, user: User, deck_id: uuid.UUID) -> Deck:
        deck = await self.deck_repo.get_for_user(deck_id, user.id)
        if deck is None:
            raise NotFoundError(
                code=ErrorCode.DECK_NOT_FOUND,
                message="Колода не найдена.",
            )
        return deck

    async def _update_deck_counters(self, deck: Deck) -> None:
        total, new_count, due_count = await self.card_repo.counters_for_deck(deck.id)
        deck.cards_count = total
        deck.new_cards_count = new_count
        deck.due_cards_count = due_count
        await self.card_repo.session.flush()

    def _calculate_next_interval(
        self,
        current_interval: int,
        current_status: CardStatus,
        rating: CardRating,
    ) -> tuple[int, CardStatus]:
        if rating == CardRating.DONT_KNOW:
            return 1, CardStatus.LEARNING

        if rating == CardRating.REPEAT:
            if current_interval == 0:
                return 0, CardStatus.NEW
            return current_interval, current_status

        # rating == KNOW
        if current_interval == 0:
            return 1, CardStatus.LEARNING

        next_interval = round(current_interval * self.INTERVAL_MULTIPLIER)
        status = CardStatus.REVIEW if next_interval >= 7 else CardStatus.LEARNING
        return next_interval, status

    def _compute_next_review(
        self,
        interval_days: int,
        rating: CardRating,
        now: datetime,
    ) -> datetime:
        if rating == CardRating.REPEAT:
            return now + timedelta(minutes=self.REPEAT_DELAY_MINUTES)
        return now + timedelta(days=interval_days)


__all__ = ["CardService"]
