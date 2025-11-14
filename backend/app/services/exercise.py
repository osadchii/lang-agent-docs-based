"""Exercise workflow orchestration: generation, submission, and history."""

from __future__ import annotations

import logging
import uuid
from copy import deepcopy

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import CacheClient, exercise_session_cache_key
from app.core.errors import ApplicationError, ErrorCode, NotFoundError
from app.models.exercise import ExerciseHistory, ExerciseResultType, ExerciseType
from app.models.topic import Topic
from app.models.user import User
from app.repositories.exercise import ExerciseHistoryRepository
from app.repositories.language_profile import LanguageProfileRepository
from app.repositories.topic import TopicRepository
from app.schemas.exercise import (
    ExerciseGenerateRequest,
    ExerciseSubmissionResponse,
    ExerciseSubmitRequest,
    GeneratedExerciseResponse,
    PendingExercise,
)
from app.services.llm import TokenUsage
from app.services.llm_enhanced import EnhancedLLMService

logger = logging.getLogger("app.services.exercises")


class ExerciseService:
    """Generate exercises with the LLM, check answers, and persist history."""

    SESSION_TTL_SECONDS = 900  # 15 minutes

    def __init__(
        self,
        history_repo: ExerciseHistoryRepository,
        topic_repo: TopicRepository,
        profile_repo: LanguageProfileRepository,
        llm_service: EnhancedLLMService,
        cache: CacheClient,
    ) -> None:
        self.history_repo = history_repo
        self.topic_repo = topic_repo
        self.profile_repo = profile_repo
        self.llm_service = llm_service
        self.cache = cache

    @property
    def session(self) -> AsyncSession:
        """Expose shared session for transaction handling."""
        return self.history_repo.session

    async def generate_exercise(
        self,
        user: User,
        request: ExerciseGenerateRequest,
    ) -> GeneratedExerciseResponse:
        """Generate an exercise for the selected topic."""
        topic = await self._get_topic_for_user(user, request.topic_id)
        profile = await self.profile_repo.get_by_id_for_user(topic.profile_id, user.id)
        if profile is None:
            raise NotFoundError(
                code=ErrorCode.PROFILE_NOT_FOUND,
                message="??????? ?? ??????.",
            )

        difficulty = await self._determine_difficulty(topic.id)
        metadata: dict[str, object] = {
            "difficulty": difficulty,
            "topic_type": topic.type.value,
        }

        exercise, usage = await self.llm_service.generate_exercise(
            topic_name=topic.name,
            topic_description=topic.description or "",
            topic_type=topic.type.value,
            level=profile.current_level,
            language=profile.language,
            exercise_type=request.type.value,
        )

        metadata.update(
            {
                "hint": exercise.hint,
                "options": exercise.options,
                "correct_index": exercise.correct_index,
            }
        )

        pending = PendingExercise(
            id=uuid.uuid4(),
            user_id=user.id,
            profile_id=profile.id,
            topic_id=topic.id,
            type=request.type,
            question=exercise.question,
            prompt=exercise.prompt,
            correct_answer=exercise.correct_answer,
            hint=exercise.hint,
            explanation=exercise.explanation,
            alternatives=exercise.alternatives,
            options=exercise.options,
            correct_index=exercise.correct_index,
            metadata=metadata,
        )

        await self._store_session(pending)
        await self.llm_service.track_token_usage(
            db_session=self.session,
            user_id=str(user.id),
            profile_id=str(profile.id),
            usage=usage,
            operation="generate_exercise",
        )

        logger.info(
            "Exercise generated",
            extra={
                "user_id": str(user.id),
                "topic_id": str(topic.id),
                "exercise_type": request.type.value,
            },
        )

        return GeneratedExerciseResponse(
            id=pending.id,
            topic_id=pending.topic_id,
            type=pending.type,
            question=pending.question,
            prompt=pending.prompt,
            hint=pending.hint,
            options=pending.options,
            correct_index=pending.correct_index,
            metadata=pending.metadata,
        )

    async def submit_answer(
        self,
        user: User,
        exercise_id: uuid.UUID,
        payload: ExerciseSubmitRequest,
    ) -> ExerciseSubmissionResponse:
        """Check the answer and persist the attempt."""
        pending = await self._load_session(exercise_id)
        if pending.user_id != user.id:
            raise NotFoundError(
                code=ErrorCode.NOT_FOUND,
                message="?????????? ?? ??????. ?????????? ??????????? ???????.",
            )

        topic = await self._get_topic_for_user(user, pending.topic_id)
        profile = await self.profile_repo.get_by_id_for_user(pending.profile_id, user.id)
        if profile is None:
            raise NotFoundError(
                code=ErrorCode.PROFILE_NOT_FOUND,
                message="??????? ?? ??????.",
            )

        if pending.type == ExerciseType.MULTIPLE_CHOICE:
            submission, user_answer_text = await self._grade_multiple_choice(pending, payload)
            usage = None
        else:
            submission, usage, user_answer_text = await self._grade_free_text(
                pending, payload, profile.current_level, user
            )

        await self._persist_attempt(
            user=user,
            pending=pending,
            topic=topic,
            submission=submission,
            user_answer=user_answer_text,
            used_hint=payload.used_hint,
            duration_seconds=payload.duration_seconds,
        )

        await self.topic_repo.update_stats(topic, submission.result)
        await self.session.flush()
        await self._delete_session(exercise_id)

        if usage is not None:
            await self.llm_service.track_token_usage(
                db_session=self.session,
                user_id=str(user.id),
                profile_id=str(profile.id),
                usage=usage,
                operation="check_exercise",
            )

        return submission

    async def get_hint(self, user: User, exercise_id: uuid.UUID) -> str:
        """Return an available hint for the pending exercise."""
        pending = await self._load_session(exercise_id)
        if pending.user_id != user.id:
            raise NotFoundError(
                code=ErrorCode.NOT_FOUND,
                message="?????????? ?? ??????.",
            )
        if pending.hint:
            return pending.hint
        return "?????????, ??????? ?? ???????? ? ????????? ?????????."

    async def _grade_multiple_choice(
        self,
        pending: PendingExercise,
        payload: ExerciseSubmitRequest,
    ) -> tuple[ExerciseSubmissionResponse, str]:
        if not isinstance(payload.answer, int):
            raise ApplicationError(
                code=ErrorCode.VALIDATION_ERROR,
                message="?????????? ???????? ??????? ?????? ??? ???????? ?????.",
            )
        if pending.options is None or pending.correct_index is None:
            raise ApplicationError(
                code=ErrorCode.INTERNAL_ERROR,
                message="????????? ???????? ????? ???????????. ?????????? ??????.",
            )

        index = payload.answer
        if not 0 <= index < len(pending.options):
            raise ApplicationError(
                code=ErrorCode.VALIDATION_ERROR,
                message="?????????? ???????? ???????? ??????? ?????? ??? ?????.",
            )

        is_correct = index == pending.correct_index
        result = ExerciseResultType.CORRECT if is_correct else ExerciseResultType.INCORRECT
        feedback = (
            "???????! ?? ?????????? ??????."
            if is_correct
            else f"???????????. ?????????? ?????: {pending.options[pending.correct_index]}"
        )

        user_answer = pending.options[index]
        submission = ExerciseSubmissionResponse(
            result=result,
            correct_answer=pending.options[pending.correct_index],
            explanation=pending.explanation,
            alternatives=[],
            feedback=feedback,
            mistakes=[],
        )
        return submission, user_answer

    async def _grade_free_text(
        self,
        pending: PendingExercise,
        payload: ExerciseSubmitRequest,
        level: str,
        user: User,
    ) -> tuple[ExerciseSubmissionResponse, TokenUsage, str]:
        if not isinstance(payload.answer, str):
            raise ApplicationError(
                code=ErrorCode.VALIDATION_ERROR,
                message="?????????? ???????? ???????? ??????? ?????? ??? ??????? ??????.",
            )
        user_answer = payload.answer.strip()

        result_data, usage = await self.llm_service.check_answer(
            question=pending.question,
            prompt=pending.prompt,
            correct_answer=pending.correct_answer,
            user_answer=user_answer,
            level=level,
        )

        submission = ExerciseSubmissionResponse(
            result=ExerciseResultType(result_data.result),
            correct_answer=result_data.correct_answer,
            explanation=result_data.explanation,
            alternatives=result_data.alternatives,
            feedback=result_data.feedback,
            mistakes=result_data.mistakes or [],
        )

        logger.info(
            "Graded free-text exercise",
            extra={"user_id": str(user.id), "result": submission.result.value},
        )

        return submission, usage, user_answer

    async def _persist_attempt(
        self,
        user: User,
        pending: PendingExercise,
        topic: Topic,
        submission: ExerciseSubmissionResponse,
        user_answer: str,
        *,
        used_hint: bool,
        duration_seconds: int | None,
    ) -> None:
        metadata = deepcopy(pending.metadata)
        metadata.update(
            {
                "alternatives": submission.alternatives,
                "feedback": submission.feedback,
                "mistakes": [mistake.model_dump() for mistake in submission.mistakes],
            }
        )

        await self.history_repo.record_attempt(
            user_id=user.id,
            profile_id=pending.profile_id,
            topic_id=topic.id,
            exercise_type=pending.type,
            question=pending.question,
            prompt=pending.prompt,
            correct_answer=pending.correct_answer,
            user_answer=user_answer,
            result=submission.result,
            explanation=submission.explanation,
            used_hint=used_hint,
            duration_seconds=duration_seconds,
            metadata=metadata,
        )

    async def _store_session(self, pending: PendingExercise) -> None:
        key = exercise_session_cache_key(str(pending.id))
        await self.cache.set(key, pending.model_dump_json(), ttl=self.SESSION_TTL_SECONDS)

    async def _load_session(self, exercise_id: uuid.UUID) -> PendingExercise:
        key = exercise_session_cache_key(str(exercise_id))
        payload = await self.cache.get(key)
        if not payload:
            raise NotFoundError(
                code=ErrorCode.NOT_FOUND,
                message="?????????? ?? ?????? ? ??????? ????????.",
            )
        return PendingExercise.model_validate_json(payload)

    async def _delete_session(self, exercise_id: uuid.UUID) -> None:
        key = exercise_session_cache_key(str(exercise_id))
        await self.cache.delete(key)

    async def _determine_difficulty(self, topic_id: uuid.UUID) -> str:
        """Infer difficulty bucket from the latest attempts."""
        recent = await self.history_repo.last_results_for_topic(topic_id, limit=10)
        if len(recent) < 3:
            return "medium"

        correct = sum(1 for attempt in recent if attempt.result == ExerciseResultType.CORRECT)
        partial = sum(1 for attempt in recent if attempt.result == ExerciseResultType.PARTIAL)
        accuracy = (correct + partial * 0.5) / len(recent)

        if accuracy < 0.4:
            return "easy"
        if accuracy > 0.85:
            return "hard"
        return "medium"

    async def _get_topic_for_user(self, user: User, topic_id: uuid.UUID) -> Topic:
        topic = await self.topic_repo.get_for_user(topic_id, user.id)
        if topic is None:
            raise NotFoundError(
                code=ErrorCode.TOPIC_NOT_FOUND,
                message="???? ?? ??????.",
            )
        return topic

    async def list_history(
        self,
        user: User,
        *,
        profile_id: uuid.UUID | None = None,
        topic_id: uuid.UUID | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[ExerciseHistory], int]:
        """Return paginated exercise history entries for the user."""
        safe_limit = max(1, min(limit, 100))
        safe_offset = max(0, offset)
        return await self.history_repo.list_for_user(
            user.id,
            profile_id=profile_id,
            topic_id=topic_id,
            limit=safe_limit,
            offset=safe_offset,
        )


__all__ = ["ExerciseService"]
