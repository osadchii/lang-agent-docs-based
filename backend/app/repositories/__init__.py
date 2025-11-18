"""Data access layer abstractions and implementations."""

from app.repositories.card import CardRepository, CardReviewRepository
from app.repositories.conversation import ConversationRepository
from app.repositories.deck import DeckRepository
from app.repositories.exercise import ExerciseHistoryRepository
from app.repositories.group import (
    GroupInviteRepository,
    GroupMaterialRepository,
    GroupMemberRepository,
    GroupRepository,
)
from app.repositories.language_profile import LanguageProfileRepository
from app.repositories.notification import NotificationRepository, StreakReminderRepository
from app.repositories.stats import StatsRepository
from app.repositories.token_usage import TokenUsageRepository
from app.repositories.topic import TopicRepository
from app.repositories.user import UserRepository

__all__ = [
    "CardRepository",
    "CardReviewRepository",
    "ConversationRepository",
    "DeckRepository",
    "GroupInviteRepository",
    "GroupMaterialRepository",
    "GroupMemberRepository",
    "GroupRepository",
    "ExerciseHistoryRepository",
    "NotificationRepository",
    "StatsRepository",
    "LanguageProfileRepository",
    "StreakReminderRepository",
    "TokenUsageRepository",
    "TopicRepository",
    "UserRepository",
]
