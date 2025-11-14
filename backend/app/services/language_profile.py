"""Business logic for managing user language profiles."""

from __future__ import annotations

import logging
import uuid
from typing import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ApplicationError, ErrorCode, NotFoundError
from app.models.language_profile import LanguageProfile
from app.models.user import User
from app.repositories.language_profile import LanguageProfileRepository
from app.schemas.profile import LanguageProfileCreate, LanguageProfileUpdate

logger = logging.getLogger("app.services.language_profiles")

CEFR_LEVELS = ("A1", "A2", "B1", "B2", "C1", "C2")
LEVEL_ORDER = {level: index for index, level in enumerate(CEFR_LEVELS)}


class LanguageProfileService:
    """High-level orchestration for CRUD operations on LanguageProfile entities."""

    SUPPORTED_LANGUAGES: dict[str, str] = {
        "en": "Английский",
        "es": "Испанский",
        "de": "Немецкий",
        "fr": "Французский",
        "it": "Итальянский",
        "pt": "Португальский",
        "tr": "Турецкий",
        "zh": "Китайский",
    }
    ALLOWED_GOALS: set[str] = {
        "work",
        "travel",
        "study",
        "communication",
        "reading",
        "self_development",
        "relationships",
        "relocation",
    }

    def __init__(
        self,
        repository: LanguageProfileRepository,
        *,
        max_free_profiles: int = 1,
    ) -> None:
        self.repository = repository
        self.max_free_profiles = max_free_profiles

    @property
    def session(self) -> AsyncSession:
        """Expose the underlying AsyncSession for transaction control."""
        return self.repository.session

    async def list_profiles(self, user: User) -> list[LanguageProfile]:
        """Return all non-deleted profiles for the user ordered by activity."""
        return await self.repository.list_for_user(user.id)

    async def create_profile(
        self,
        user: User,
        payload: LanguageProfileCreate,
    ) -> LanguageProfile:
        """Create a new language profile enforcing plan limits and validation rules."""
        language_code = payload.language.lower()
        language_name = self._resolve_language_name(language_code)
        self._validate_levels(payload.current_level, payload.target_level)
        goals = self._validate_goals(payload.goals)

        if not user.is_premium:
            count = await self.repository.count_for_user(user.id)
            if count >= self.max_free_profiles:
                raise ApplicationError(
                    code=ErrorCode.LIMIT_REACHED,
                    message="На бесплатном тарифе доступен только один профиль.",
                )

        duplicate = await self.repository.get_by_language(user.id, language_code)
        if duplicate:
            raise ApplicationError(
                code=ErrorCode.DUPLICATE_LANGUAGE,
                message="Профиль для этого языка уже существует.",
            )

        active_profile = await self.repository.get_active_for_user(user.id)

        profile = LanguageProfile(
            user_id=user.id,
            language=language_code,
            language_name=language_name,
            current_level=payload.current_level,
            target_level=payload.target_level,
            goals=goals,
            interface_language=payload.interface_language or user.language_code or "ru",
            is_active=active_profile is None,
        )
        await self.repository.add(profile)
        await self.session.refresh(profile)

        logger.info(
            "Language profile created",
            extra={"user_id": str(user.id), "profile_id": str(profile.id)},
        )
        return profile

    async def get_profile(self, user: User, profile_id: uuid.UUID) -> LanguageProfile:
        """Fetch a profile or raise PROFILE_NOT_FOUND."""
        profile = await self.repository.get_by_id_for_user(profile_id, user.id)
        if profile is None:
            raise NotFoundError(
                code=ErrorCode.PROFILE_NOT_FOUND,
                message="Профиль не найден.",
            )
        return profile

    async def update_profile(
        self,
        user: User,
        profile_id: uuid.UUID,
        payload: LanguageProfileUpdate,
    ) -> LanguageProfile:
        """Update mutable attributes of a profile."""
        profile = await self.get_profile(user, profile_id)

        new_current = payload.current_level or profile.current_level
        new_target = payload.target_level or profile.target_level
        if payload.current_level or payload.target_level:
            self._validate_levels(new_current, new_target)
            profile.current_level = new_current
            profile.target_level = new_target

        if payload.goals is not None:
            profile.goals = self._validate_goals(payload.goals)

        if payload.interface_language is not None:
            profile.interface_language = payload.interface_language

        await self.session.flush()
        await self.session.refresh(profile)
        return profile

    async def delete_profile(self, user: User, profile_id: uuid.UUID) -> None:
        """Soft delete a profile ensuring at least one profile remains."""
        profile = await self.get_profile(user, profile_id)
        remaining = await self.repository.count_for_user(user.id)
        if remaining <= 1:
            raise ApplicationError(
                code=ErrorCode.LAST_PROFILE,
                message="Нельзя удалить единственный профиль.",
            )

        was_active = profile.is_active
        await self.repository.soft_delete(profile)

        if was_active:
            replacement = await self.repository.get_alternate_profile(
                user.id,
                exclude_id=profile.id,
            )
            if replacement:
                replacement.is_active = True

        await self.session.flush()

    async def activate_profile(self, user: User, profile_id: uuid.UUID) -> LanguageProfile:
        """Mark a profile as active and deactivate the rest."""
        profile = await self.get_profile(user, profile_id)
        await self.repository.deactivate_user_profiles(user.id, exclude=profile.id)
        profile.is_active = True
        await self.session.flush()
        await self.session.refresh(profile)
        return profile

    def _resolve_language_name(self, language: str) -> str:
        try:
            return self.SUPPORTED_LANGUAGES[language]
        except KeyError as exc:
            raise ApplicationError(
                code=ErrorCode.INVALID_FIELD_VALUE,
                message="Язык не поддерживается.",
                details={"language": language},
            ) from exc

    def _validate_levels(self, current: str, target: str) -> None:
        try:
            current_rank = LEVEL_ORDER[current]
            target_rank = LEVEL_ORDER[target]
        except KeyError as exc:
            raise ApplicationError(
                code=ErrorCode.INVALID_LEVEL,
                message="Неверный уровень CEFR.",
            ) from exc

        if target_rank < current_rank:
            raise ApplicationError(
                code=ErrorCode.TARGET_BELOW_CURRENT,
                message="Целевой уровень не может быть ниже текущего.",
            )

    def _validate_goals(self, goals: Sequence[str]) -> list[str]:
        cleaned = [goal for goal in goals if goal]
        if not cleaned:
            raise ApplicationError(
                code=ErrorCode.VALIDATION_ERROR,
                message="Нужно выбрать хотя бы одну цель обучения.",
            )

        invalid = sorted({goal for goal in cleaned if goal not in self.ALLOWED_GOALS})
        if invalid:
            raise ApplicationError(
                code=ErrorCode.INVALID_FIELD_VALUE,
                message="Обнаружены неподдерживаемые цели.",
                details={"invalid": invalid},
            )

        unique = []
        for goal in cleaned:
            if goal not in unique:
                unique.append(goal)
        return unique


__all__ = ["LanguageProfileService", "CEFR_LEVELS"]
