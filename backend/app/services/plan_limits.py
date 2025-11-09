"""Helpers for determining plan limits."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from app.models.user import User


@dataclass(frozen=True)
class PlanLimits:
    """Set of quotas for a plan."""

    profiles: Optional[int]
    messages: Optional[int]
    exercises: Optional[int]
    cards: Optional[int]
    groups: Optional[int]


FREE_LIMITS = PlanLimits(
    profiles=1,
    messages=50,
    exercises=10,
    cards=200,
    groups=1,
)

PREMIUM_LIMITS = PlanLimits(
    profiles=10,
    messages=500,
    exercises=None,
    cards=None,
    groups=None,
)


def is_effectively_premium(user: User) -> bool:
    """Return True if user has active premium or trial."""

    if user.is_premium:
        return True

    if user.trial_ends_at and user.trial_ends_at > datetime.now(timezone.utc):
        return True

    return False


def get_plan_limits(user: User) -> PlanLimits:
    """Return plan limits for the given user."""

    return PREMIUM_LIMITS if is_effectively_premium(user) else FREE_LIMITS
