"""Business logic for managing language profiles."""

from __future__ import annotations

from typing import List
from uuid import UUID

from app.exceptions.domain_error import DomainError
from app.models.language_profile import CEFR_LEVELS, LanguageProfile
from app.models.user import User
from app.repositories.profile_repository import ProfileRepository, profile_repository
from app.services.plan_limits import get_plan_limits

SUPPORTED_GOALS = {
    "work",
    "travel",
    "study",
    "communication",
    "reading",
    "self_development",
    "relationships",
    "relocation",
}

LANGUAGE_NAME_MAP = {
    "en": "Английский",
    "es": "Испанский",
    "fr": "Французский",
    "de": "Немецкий",
    "it": "Итальянский",
    "pt": "Португальский",
    "ru": "Русский",
}

CEFR_ORDER = {level: index for index, level in enumerate(CEFR_LEVELS)}


class ProfileService:
    """Operations on language profiles."""

    def __init__(self, repository: ProfileRepository) -> None:
        self._repository = repository

    def list_profiles(self, user: User) -> List[LanguageProfile]:
        """Return all non-deleted profiles."""

        return self._repository.list_by_user(user.id)

    def create_profile(
        self,
        *,
        user: User,
        language: str,
        current_level: str,
        target_level: str,
        goals: List[str],
        interface_language: str,
    ) -> LanguageProfile:
        """Create a new profile for the user."""

        normalized_language = self._normalize_language(language)
        interface_language = self._normalize_language(interface_language)
        goals = self._normalize_goals(goals)
        current_level = self._normalize_level(current_level)
        target_level = self._normalize_level(target_level)
        self._validate_level_progression(current_level, target_level)
        self._validate_interface_language(normalized_language, interface_language)

        available_slots = self._available_profile_slots(user)
        if available_slots is not None and available_slots <= 0:
            raise DomainError(
                status_code=400,
                error_code="LIMIT_REACHED",
                message="Достигнут лимит профилей для текущего плана.",
                details={"limit_type": "profiles"},
            )

        if self._language_exists(user.id, normalized_language):
            raise DomainError(
                status_code=400,
                error_code="DUPLICATE_LANGUAGE",
                message="Профиль для этого языка уже существует.",
            )

        language_name = LANGUAGE_NAME_MAP.get(normalized_language, normalized_language.upper())
        should_be_active = self._repository.count_active(user.id) == 0

        return self._repository.create(
            user_id=user.id,
            language=normalized_language,
            language_name=language_name,
            current_level=current_level,
            target_level=target_level,
            goals=goals,
            interface_language=interface_language,
            is_active=should_be_active,
        )

    def get_profile(self, user: User, profile_id: UUID) -> LanguageProfile:
        """Return one profile ensuring ownership."""

        profile = self._repository.get(profile_id)
        if not profile or profile.user_id != user.id or profile.deleted:
            raise DomainError(
                status_code=404,
                error_code="PROFILE_NOT_FOUND",
                message="Профиль не найден.",
            )
        return profile

    def update_profile(
        self,
        *,
        user: User,
        profile_id: UUID,
        current_level: str | None = None,
        target_level: str | None = None,
        goals: List[str] | None = None,
        interface_language: str | None = None,
    ) -> LanguageProfile:
        """Update allowed profile fields."""

        profile = self.get_profile(user, profile_id)
        updates = {}

        if current_level is not None:
            updates["current_level"] = self._normalize_level(current_level)
        if target_level is not None:
            updates["target_level"] = self._normalize_level(target_level)
        if "current_level" in updates or "target_level" in updates:
            new_current = updates.get("current_level", profile.current_level)
            new_target = updates.get("target_level", profile.target_level)
            self._validate_level_progression(new_current, new_target)
        if goals is not None:
            updates["goals"] = self._normalize_goals(goals)
        if interface_language is not None:
            normalized_interface = self._normalize_language(interface_language)
            self._validate_interface_language(profile.language, normalized_interface)
            updates["interface_language"] = normalized_interface

        updated = self._repository.update(
            profile_id,
            current_level=updates.get("current_level"),
            target_level=updates.get("target_level"),
            goals=updates.get("goals"),
            interface_language=updates.get("interface_language"),
        )
        if not updated:
            raise DomainError(
                status_code=404,
                error_code="PROFILE_NOT_FOUND",
                message="Профиль не найден.",
            )
        return updated

    def delete_profile(self, user: User, profile_id: UUID) -> None:
        """Soft delete profile ensuring at least one remains."""

        profile = self.get_profile(user, profile_id)
        remaining = self._repository.count_active(user.id)
        if remaining <= 1:
            raise DomainError(
                status_code=400,
                error_code="LAST_PROFILE",
                message="Нельзя удалить последний профиль.",
            )

        deleted = self._repository.soft_delete(profile_id)
        if not deleted:
            raise DomainError(
                status_code=404,
                error_code="PROFILE_NOT_FOUND",
                message="Профиль не найден.",
            )

        if profile.is_active:
            candidates = self._repository.list_by_user(user.id)
            if candidates:
                self._repository.set_active(user.id, candidates[0].id)

    def activate_profile(self, user: User, profile_id: UUID) -> LanguageProfile:
        """Set the profile as active."""

        profile = self.get_profile(user, profile_id)
        activated = self._repository.set_active(user.id, profile.id)
        if not activated:
            raise DomainError(
                status_code=404,
                error_code="PROFILE_NOT_FOUND",
                message="Профиль не найден.",
            )
        return activated

    def _available_profile_slots(self, user: User) -> int | None:
        limits = get_plan_limits(user)
        if limits.profiles is None:
            return None
        used = self._repository.count_active(user.id)
        return limits.profiles - used

    def _language_exists(self, user_id: UUID, language: str) -> bool:
        return any(
            profile.language == language
            for profile in self._repository.list_by_user(user_id)
        )

    @staticmethod
    def _normalize_language(language: str) -> str:
        if not language:
            raise DomainError(
                status_code=400,
                error_code="INVALID_FIELD_VALUE",
                message="Код языка обязателен.",
            )
        code = language.strip().lower()
        if not code.isalpha() or len(code) not in (2, 3):
            raise DomainError(
                status_code=400,
                error_code="INVALID_FIELD_VALUE",
                message="Некорректный код языка. Используйте ISO 639-1.",
            )
        return code

    @staticmethod
    def _normalize_goals(goals: List[str]) -> List[str]:
        normalized: List[str] = []
        for goal in goals:
            value = goal.strip().lower()
            if value not in SUPPORTED_GOALS:
                raise DomainError(
                    status_code=400,
                    error_code="INVALID_FIELD_VALUE",
                    message=f"Цель '{goal}' не поддерживается.",
                    details={"allowed": sorted(SUPPORTED_GOALS)},
                )
            normalized.append(value)
        return normalized

    @staticmethod
    def _normalize_level(level: str) -> str:
        upper = level.strip().upper()
        if upper not in CEFR_ORDER:
            raise DomainError(
                status_code=400,
                error_code="INVALID_LEVEL",
                message="Неверный уровень CEFR.",
            )
        return upper

    @staticmethod
    def _validate_level_progression(current_level: str, target_level: str) -> None:
        if CEFR_ORDER[target_level] < CEFR_ORDER[current_level]:
            raise DomainError(
                status_code=400,
                error_code="TARGET_BELOW_CURRENT",
                message="Целевой уровень не может быть ниже текущего.",
            )

    @staticmethod
    def _validate_interface_language(language: str, interface_language: str) -> None:
        if interface_language not in {language, "ru"}:
            raise DomainError(
                status_code=400,
                error_code="INVALID_FIELD_VALUE",
                message="Язык интерфейса может быть русским или совпадать с изучаемым языком.",
            )


_profile_service: ProfileService | None = None


def get_profile_service() -> ProfileService:
    """Return singleton profile service."""

    global _profile_service
    if _profile_service is None:
        _profile_service = ProfileService(profile_repository)
    return _profile_service
