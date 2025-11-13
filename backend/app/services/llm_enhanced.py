"""
Enhanced LLM service with structured outputs, function calling, and caching.

Extends the basic LLM service with:
- Structured JSON outputs using Pydantic models
- Function calling (tools) for specific actions
- Redis caching for LLM responses
- Token usage tracking to database
"""

from __future__ import annotations

import json
import logging
from typing import Any, Type, TypeVar

from pydantic import BaseModel, ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import (
    TTL_1_HOUR,
    TTL_30_DAYS,
    TTL_PERMANENT,
    CacheClient,
    card_cache_key,
    lemma_cache_key,
    topics_cache_key,
)
from app.core.errors import LLMParsingError
from app.models import TokenUsage
from app.schemas.llm_responses import (
    CardContent,
    ExerciseContent,
    ExerciseResult,
    IntentDetection,
    TopicSuggestions,
)
from app.services.llm import LLMService, TokenUsage as LLMTokenUsage

logger = logging.getLogger("app.services.llm_enhanced")

T = TypeVar("T", bound=BaseModel)


class EnhancedLLMService(LLMService):
    """
    Enhanced LLM service with structured outputs, caching, and token tracking.

    Extends LLMService with:
    - Parse JSON responses into Pydantic models
    - Cache LLM responses in Redis
    - Track token usage in database
    - Support function calling (tools)
    """

    def __init__(
        self,
        api_key: str,
        cache: CacheClient,
        model: str = "gpt-4o-mini",
        temperature: float = 0.7,
        **kwargs: Any,  # noqa: ANN401
    ) -> None:
        """
        Initialize enhanced LLM service.

        Args:
            api_key: OpenAI API key
            cache: Redis cache client
            model: Model to use
            temperature: Default temperature
            **kwargs: Additional arguments for LLMService
        """
        super().__init__(api_key=api_key, model=model, temperature=temperature, **kwargs)
        self.cache = cache

    async def chat_structured(
        self,
        messages: list[dict[str, str]],
        response_model: Type[T],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
        cache_key: str | None = None,
        cache_ttl: int | None = None,
    ) -> tuple[T, LLMTokenUsage]:
        """
        Send chat request with structured JSON output.

        Args:
            messages: Chat messages
            response_model: Pydantic model for response validation
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            cache_key: Optional cache key (if None, no caching)
            cache_ttl: Cache TTL in seconds

        Returns:
            Tuple of (parsed_model, token_usage)

        Raises:
            LLMParsingError: If response cannot be parsed into model
        """
        # Check cache first
        if cache_key:
            cached = await self.cache.get(cache_key)
            if cached:
                try:
                    model = response_model.model_validate_json(cached)
                    logger.info(
                        "Cache hit for structured response",
                        extra={"cache_key": cache_key, "model": response_model.__name__},
                    )
                    # Return with zero token usage since it's cached
                    return model, LLMTokenUsage(0, 0, 0)
                except ValidationError as e:
                    logger.warning(
                        f"Cached data validation failed, regenerating: {e}",
                        extra={"cache_key": cache_key},
                    )

        # Call LLM with JSON mode
        response_text, usage = await self.chat(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format={"type": "json_object"},
        )

        # Parse and validate response
        try:
            model = response_model.model_validate_json(response_text)
        except (json.JSONDecodeError, ValidationError) as e:
            logger.error(
                "Failed to parse LLM response",
                extra={
                    "error": str(e),
                    "response_preview": response_text[:200],
                    "expected_model": response_model.__name__,
                },
            )
            raise LLMParsingError(f"Invalid JSON response: {e}") from e

        # Cache result
        if cache_key and cache_ttl:
            await self.cache.set(cache_key, model.model_dump_json(), ttl=cache_ttl)
            logger.info(
                "Cached structured response",
                extra={"cache_key": cache_key, "ttl": cache_ttl},
            )

        return model, usage

    async def generate_card(
        self,
        word: str,
        language: str,
        language_name: str,
        level: str,
        goals: list[str],
    ) -> tuple[CardContent, LLMTokenUsage]:
        """
        Generate flashcard content for a word.

        Args:
            word: Word to generate card for
            language: Target language code (e.g., 'es', 'de')
            language_name: Language name (e.g., 'Spanish', 'German')
            level: CEFR level (A1-C2)
            goals: Learning goals

        Returns:
            Tuple of (card_content, token_usage)
        """
        prompt = f"""Generate a flashcard for the word: "{word}"

Requirements:
1. Provide the word in its base form (lemma)
2. Translate to Russian
3. Create an example sentence in {language_name} (appropriate for {level} level)
4. Translate the example to Russian

Consider:
- User's level: {level}
- User's goals: {', '.join(goals)}
- The example should be practical and memorable

Respond in JSON format:
{{
  "word": "{word}",
  "lemma": "base form of the word",
  "translation": "Russian translation",
  "example": "Example sentence in {language_name}",
  "example_translation": "Example translation in Russian",
  "notes": "Optional notes or context"
}}"""

        messages = [
            {"role": "system", "content": f"You are a professional {language_name} teacher."},
            {"role": "user", "content": prompt},
        ]

        # Use lemma for cache key after generating
        card, usage = await self.chat_structured(
            messages=messages,
            response_model=CardContent,
            temperature=0.7,
        )

        # Cache with the generated lemma
        cache_key = card_cache_key(language, card.lemma)
        await self.cache.set(cache_key, card.model_dump_json(), ttl=TTL_30_DAYS)

        return card, usage

    async def get_lemma(
        self,
        word: str,
        language: str,
    ) -> tuple[str, LLMTokenUsage]:
        """
        Get base form (lemma) of a word.

        Args:
            word: Word to get lemma for
            language: Language code

        Returns:
            Tuple of (lemma, token_usage)
        """
        cache_key = lemma_cache_key(language, word)

        # Check cache (permanent TTL)
        cached = await self.cache.get(cache_key)
        if cached:
            logger.info("Cache hit for lemma", extra={"word": word, "language": language})
            return cached, LLMTokenUsage(0, 0, 0)

        prompt = f"""Determine the lemma (base form) of the word: "{word}" in {language}.

The lemma is:
- For nouns: singular form (with article if needed)
- For verbs: infinitive
- For adjectives: masculine singular (if applicable)

Examples:
- Spanish: "casas" → "casa", "comí" → "comer"
- German: "Häuser" → "das Haus", "gehst" → "gehen"
- English: "houses" → "house", "went" → "go"

Respond with only the lemma, no explanation."""

        messages = [{"role": "user", "content": prompt}]

        response, usage = await self.chat(
            messages=messages,
            temperature=0.0,
            max_tokens=20,
        )

        lemma = response.strip()

        # Cache permanently
        await self.cache.set(cache_key, lemma, ttl=TTL_PERMANENT)

        return lemma, usage

    async def generate_exercise(
        self,
        topic_name: str,
        topic_description: str,
        topic_type: str,
        level: str,
        language: str,
        exercise_type: str,
    ) -> tuple[ExerciseContent, LLMTokenUsage]:
        """
        Generate an exercise.

        Args:
            topic_name: Topic name
            topic_description: Topic description
            topic_type: Topic type (grammar/vocabulary/situation)
            level: CEFR level
            language: Language code
            exercise_type: Exercise type (free_text/multiple_choice)

        Returns:
            Tuple of (exercise, token_usage)
        """
        prompt = f"""Generate a {exercise_type} exercise for the topic: "{topic_name}"

Topic description: {topic_description}
Student level: {level}
Exercise type: {exercise_type}

Requirements:
1. Create a clear question/instruction
2. Provide a prompt (sentence to translate or complete)
3. The difficulty should match {level} level
4. Focus on {topic_type}

"""

        # Add exercise-type specific instructions
        if exercise_type == "free_text":
            prompt += "\nThe student will write their answer freely."
        else:
            prompt += """
Provide 4 options:
- 1 correct answer
- 3 plausible but incorrect options (common mistakes)"""

        prompt += "\n\nRespond in JSON format with all required fields."

        messages = [
            {"role": "system", "content": "You are a professional language teacher."},
            {"role": "user", "content": prompt},
        ]

        # Exercises are generated on the fly, no caching
        return await self.chat_structured(
            messages=messages,
            response_model=ExerciseContent,
            temperature=0.8,  # More variety for exercises
        )

    async def check_answer(
        self,
        question: str,
        prompt: str,
        correct_answer: str,
        user_answer: str,
        level: str,
    ) -> tuple[ExerciseResult, LLMTokenUsage]:
        """
        Check exercise answer.

        Args:
            question: Exercise question
            prompt: Exercise prompt
            correct_answer: Correct answer
            user_answer: User's answer
            level: User's level

        Returns:
            Tuple of (result, token_usage)
        """
        check_prompt = f"""Check the student's answer to the exercise.

Exercise:
Question: {question}
Prompt: {prompt}
Correct answer: {correct_answer}

Student's answer: {user_answer}

Evaluation criteria:
1. Grade as "correct", "partial", or "incorrect"
2. Accept synonyms and alternative correct forms
3. Ignore minor typos (1-2 characters)
4. Consider grammatically correct alternatives
5. Student level: {level} - be encouraging but honest

Provide:
- Result (correct/partial/incorrect)
- Explanation of mistakes (if any)
- Correct answer
- Alternative correct answers (if applicable)
- Encouragement and guidance

Respond in JSON format."""

        messages = [
            {"role": "system", "content": "You are a helpful language teacher."},
            {"role": "user", "content": check_prompt},
        ]

        return await self.chat_structured(
            messages=messages,
            response_model=ExerciseResult,
            temperature=0.3,  # More deterministic for grading
        )

    async def suggest_topics(
        self,
        profile_id: str,
        language: str,
        language_name: str,
        level: str,
        target_level: str,
        goals: list[str],
    ) -> tuple[TopicSuggestions, LLMTokenUsage]:
        """
        Suggest relevant topics for learning.

        Args:
            profile_id: Profile ID for caching
            language: Language code
            language_name: Language name
            level: Current CEFR level
            target_level: Target CEFR level
            goals: Learning goals

        Returns:
            Tuple of (topics, token_usage)
        """
        prompt = f"""Suggest 5-7 relevant topics for the student to study.

Student profile:
- Language: {language_name}
- Current level: {level}
- Target level: {target_level}
- Goals: {', '.join(goals)}

Consider:
- Topics appropriate for {level} level
- Progression towards {target_level}
- Alignment with goals
- Mix of grammar, vocabulary, and practical situations

For each topic provide:
- Name (concise, in Russian)
- Description (1-2 sentences)
- Type (grammar/vocabulary/situation)
- Why it's relevant
- 2-3 example exercises

Respond in JSON format."""

        messages = [
            {"role": "system", "content": "You are an expert language curriculum designer."},
            {"role": "user", "content": prompt},
        ]

        cache_key = topics_cache_key(profile_id)

        return await self.chat_structured(
            messages=messages,
            response_model=TopicSuggestions,
            temperature=0.8,
            cache_key=cache_key,
            cache_ttl=TTL_1_HOUR,
        )

    async def detect_intent(
        self,
        user_message: str,
    ) -> tuple[IntentDetection, LLMTokenUsage]:
        """
        Detect user intent from message.

        Args:
            user_message: User's message

        Returns:
            Tuple of (intent, token_usage)
        """
        prompt = f"""Analyze the user's message and determine their intent.

Message: "{user_message}"

Possible intents:
- translate: asking for translation
- explain_grammar: asking about grammar rules
- check_text: asking to check their text
- add_card: explicitly asking to add words to flashcards
- practice: asking for exercises or practice
- general: general question about the language
- off_topic: unrelated to language learning

Respond in JSON format:
{{
  "intent": "detected_intent",
  "confidence": 0.95,
  "entities": {{
    "word": "extracted word if applicable",
    "context": "additional context"
  }}
}}"""

        messages = [
            {"role": "system", "content": "You are a helpful intent classifier."},
            {"role": "user", "content": prompt},
        ]

        return await self.chat_structured(
            messages=messages,
            response_model=IntentDetection,
            temperature=0.3,
        )

    async def track_token_usage(
        self,
        db_session: AsyncSession,
        user_id: str,
        profile_id: str | None,
        usage: LLMTokenUsage,
        operation: str | None = None,
    ) -> None:
        """
        Track token usage to database.

        Args:
            db_session: Database session
            user_id: User ID
            profile_id: Profile ID (optional)
            usage: Token usage from LLM call
            operation: Operation name (e.g., 'generate_card', 'chat')
        """
        try:
            token_record = TokenUsage(
                user_id=user_id,
                profile_id=profile_id,
                prompt_tokens=usage.prompt_tokens,
                completion_tokens=usage.completion_tokens,
                total_tokens=usage.total_tokens,
                estimated_cost=usage.estimated_cost,
                operation=operation,
                model=self.model,
            )

            db_session.add(token_record)
            await db_session.commit()

            logger.info(
                "Token usage tracked",
                extra={
                    "user_id": user_id,
                    "operation": operation,
                    "total_tokens": usage.total_tokens,
                    "cost": f"${usage.estimated_cost:.6f}",
                },
            )
        except Exception as e:
            logger.error("Failed to track token usage: %s", e)
            await db_session.rollback()


__all__ = ["EnhancedLLMService", "LLMParsingError"]
