"""In-memory repository for language profiles."""

from __future__ import annotations

from datetime import datetime, timezone
from threading import Lock
from typing import Dict, List, Optional
from uuid import UUID, uuid4

from app.models.language_profile import LanguageProfile


class ProfileRepository:
    """Stores language profiles for each user."""

    def __init__(self) -> None:
        self._profiles: Dict[UUID, LanguageProfile] = {}
        self._user_index: Dict[UUID, List[UUID]] = {}
        self._lock = Lock()

    def list_by_user(self, user_id: UUID, include_deleted: bool = False) -> List[LanguageProfile]:
        """Return profiles belonging to the user."""

        with self._lock:
            profile_ids = self._user_index.get(user_id, [])
            return [
                self._profiles[profile_id]
                for profile_id in profile_ids
                if include_deleted or not self._profiles[profile_id].deleted
            ]

    def count_active(self, user_id: UUID) -> int:
        """Return number of non-deleted profiles."""

        return len(self.list_by_user(user_id, include_deleted=False))

    def get(self, profile_id: UUID) -> Optional[LanguageProfile]:
        """Return profile by identifier."""

        return self._profiles.get(profile_id)

    def create(
        self,
        *,
        user_id: UUID,
        language: str,
        language_name: str,
        current_level: str,
        target_level: str,
        goals: List[str],
        interface_language: str,
        is_active: bool,
    ) -> LanguageProfile:
        """Persist new profile and return it."""

        now = datetime.now(timezone.utc)
        profile = LanguageProfile(
            id=uuid4(),
            user_id=user_id,
            language=language,
            language_name=language_name,
            current_level=current_level,
            target_level=target_level,
            goals=list(goals),
            interface_language=interface_language,
            is_active=is_active,
            created_at=now,
            updated_at=now,
            streak=0,
            best_streak=0,
            total_active_days=0,
            cards_count=0,
            exercises_count=0,
        )

        with self._lock:
            self._profiles[profile.id] = profile
            self._user_index.setdefault(user_id, []).append(profile.id)
            if is_active:
                self._deactivate_others_locked(user_id, exclude=profile.id, now=now)

            return profile

    def update(
        self,
        profile_id: UUID,
        *,
        current_level: Optional[str] = None,
        target_level: Optional[str] = None,
        goals: Optional[List[str]] = None,
        interface_language: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> Optional[LanguageProfile]:
        """Update profile fields."""

        with self._lock:
            profile = self._profiles.get(profile_id)
            if not profile:
                return None

            updates = {}
            if current_level is not None:
                updates["current_level"] = current_level
            if target_level is not None:
                updates["target_level"] = target_level
            if goals is not None:
                updates["goals"] = list(goals)
            if interface_language is not None:
                updates["interface_language"] = interface_language
            if is_active is not None:
                updates["is_active"] = is_active
            if not updates:
                return profile

            updates["updated_at"] = datetime.now(timezone.utc)
            updated = profile.model_copy(update=updates)
            self._profiles[profile_id] = updated

            if is_active:
                self._deactivate_others_locked(updated.user_id, exclude=profile_id, now=updates["updated_at"])

            return updated

    def soft_delete(self, profile_id: UUID) -> Optional[LanguageProfile]:
        """Mark profile as deleted and return it."""

        with self._lock:
            profile = self._profiles.get(profile_id)
            if not profile or profile.deleted:
                return profile

            now = datetime.now(timezone.utc)
            updated = profile.model_copy(
                update={"deleted": True, "deleted_at": now, "updated_at": now, "is_active": False}
            )
            self._profiles[profile_id] = updated
            return updated

    def set_active(self, user_id: UUID, profile_id: UUID) -> Optional[LanguageProfile]:
        """Activate the profile and deactivate others."""

        with self._lock:
            profile = self._profiles.get(profile_id)
            if not profile or profile.deleted or profile.user_id != user_id:
                return None

            now = datetime.now(timezone.utc)
            updated = profile.model_copy(update={"is_active": True, "updated_at": now})
            self._profiles[profile_id] = updated
            self._deactivate_others_locked(user_id, exclude=profile_id, now=now)
            return updated

    def reset(self) -> None:
        """Clear repository state (used by tests)."""

        with self._lock:
            self._profiles.clear()
            self._user_index.clear()

    def _deactivate_others_locked(self, user_id: UUID, *, exclude: UUID, now: datetime) -> None:
        """Deactivate other profiles for the user (expects lock held)."""

        profile_ids = self._user_index.get(user_id, [])
        for pid in profile_ids:
            if pid == exclude:
                continue
            profile = self._profiles.get(pid)
            if not profile or profile.deleted or not profile.is_active:
                continue
            self._profiles[pid] = profile.model_copy(
                update={"is_active": False, "updated_at": now}
            )


profile_repository = ProfileRepository()
