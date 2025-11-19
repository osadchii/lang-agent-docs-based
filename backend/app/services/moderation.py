"""Content moderation helpers built on top of OpenAI Moderation API."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Mapping, Sequence, cast

from openai import AsyncOpenAI, OpenAIError

logger = logging.getLogger("app.services.moderation")


@dataclass(slots=True)
class ModerationDecision:
    """Represents the moderation verdict for a given text snippet."""

    allowed: bool
    reason: str | None = None
    categories: tuple[str, ...] = ()
    source: str = "local"
    error: str | None = None


class ModerationService:
    """Thin wrapper over OpenAI Moderation API with local heuristics."""

    def __init__(
        self,
        *,
        api_key: str,
        model: str = "omni-moderation-latest",
        timeout: float = 10.0,
        client: AsyncOpenAI | None = None,
    ) -> None:
        self._client = client or AsyncOpenAI(api_key=api_key, timeout=timeout)
        self._model = model

    async def evaluate(self, text: str) -> ModerationDecision:
        """
        Run the text through local spam checks and OpenAI Moderation API.

        Returns:
            ModerationDecision describing whether the content is acceptable.
        """
        normalized = text.strip()
        if not normalized:
            return ModerationDecision(allowed=True, source="local")

        local_reason = _local_rejection_reason(normalized)
        if local_reason is not None:
            return ModerationDecision(
                allowed=False,
                reason=local_reason,
                categories=("spam",),
                source="local",
            )

        try:
            response = await self._client.moderations.create(
                model=self._model,
                input=normalized,
            )
        except OpenAIError as exc:  # pragma: no cover - defensive logging branch
            logger.error("Moderation API error: %s", exc)
            return ModerationDecision(
                allowed=True,
                error=str(exc),
                source="openai",
            )

        result = _extract_first_result(response)
        if result is None:
            return ModerationDecision(allowed=True, source="openai")

        flagged = bool(getattr(result, "flagged", False))
        if not flagged:
            return ModerationDecision(allowed=True, source="openai")

        categories = _flagged_categories(getattr(result, "categories", None))
        logger.warning(
            "Moderation flagged content",
            extra={
                "categories": categories,
                "scores": getattr(result, "category_scores", None),
            },
        )
        return ModerationDecision(
            allowed=False,
            reason="openai.flagged",
            categories=categories,
            source="openai",
        )


def _extract_first_result(response: object) -> object | None:
    results = getattr(response, "results", None)
    if not results:
        return None
    if isinstance(results, Sequence):
        return cast(object, results[0])
    return None


def _flagged_categories(categories: Mapping[str, Any] | None) -> tuple[str, ...]:
    if not categories:
        return ()

    flagged: list[str] = [
        name for name, value in categories.items() if isinstance(value, bool) and value
    ]
    return tuple(sorted(flagged))


def _local_rejection_reason(text: str) -> str | None:
    if len(text) < 2:
        return "too_short"
    if _digits_only(text):
        return "digits_only"
    if _has_long_repetition(text):
        return "repeated_characters"
    if _emoji_ratio(text) > 0.6:
        return "emoji_spam"
    return None


def _digits_only(text: str) -> bool:
    stripped = text.replace(" ", "")
    return bool(stripped) and stripped.isdigit()


def _has_long_repetition(text: str, threshold: int = 8) -> bool:
    count = 0
    previous = ""
    for char in text:
        if char == previous:
            count += 1
        else:
            count = 1
            previous = char
        if count >= threshold:
            return True
    return False


def _emoji_ratio(text: str) -> float:
    if not text:
        return 0.0
    emoji_count = sum(1 for char in text if 0x1F300 <= ord(char) <= 0x1FAFF)
    return emoji_count / len(text)


__all__ = ["ModerationDecision", "ModerationService"]
