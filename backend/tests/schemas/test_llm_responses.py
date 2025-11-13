"""Tests for LLM response schemas."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.schemas.llm_responses import (
    CardContent,
    ExerciseContent,
    ExerciseResult,
    IntentDetection,
    Mistake,
    TopicSuggestion,
    TopicSuggestions,
    WordSuggestion,
    WordSuggestions,
)


class TestCardContent:
    """Tests for CardContent model."""

    def test_valid_card_content(self) -> None:
        """Test valid card content parsing."""
        data = {
            "word": "casa",
            "lemma": "casa",
            "translation": "дом",
            "example": "Mi casa es tu casa",
            "example_translation": "Мой дом - твой дом",
            "notes": "Common expression",
        }

        card = CardContent(**data)

        assert card.word == "casa"
        assert card.lemma == "casa"
        assert card.translation == "дом"
        assert card.example == "Mi casa es tu casa"
        assert card.notes == "Common expression"

    def test_card_content_without_notes(self) -> None:
        """Test card content without optional notes field."""
        data = {
            "word": "perro",
            "lemma": "perro",
            "translation": "собака",
            "example": "El perro es mi amigo",
            "example_translation": "Собака - мой друг",
        }

        card = CardContent(**data)

        assert card.notes is None

    def test_card_content_from_json(self) -> None:
        """Test parsing card content from JSON string."""
        json_str = """
        {
            "word": "gato",
            "lemma": "gato",
            "translation": "кот",
            "example": "El gato negro",
            "example_translation": "Черный кот"
        }
        """

        card = CardContent.model_validate_json(json_str)

        assert card.word == "gato"
        assert card.lemma == "gato"

    def test_card_content_missing_required_field(self) -> None:
        """Test that missing required fields raise validation error."""
        data = {
            "word": "casa",
            "lemma": "casa",
            # Missing translation
            "example": "Mi casa",
            "example_translation": "Мой дом",
        }

        with pytest.raises(ValidationError):
            CardContent(**data)


class TestExerciseContent:
    """Tests for ExerciseContent model."""

    def test_free_text_exercise(self) -> None:
        """Test free text exercise content."""
        data = {
            "question": "Переведите на испанский:",
            "prompt": "Я работал в этой компании два года",
            "correct_answer": "He trabajado en esta empresa dos años",
            "hint": "Think about present perfect",
            "explanation": "Use Pretérito Perfecto because...",
            "alternatives": ["Trabajé en esta empresa dos años"],
        }

        exercise = ExerciseContent(**data)

        assert exercise.question == "Переведите на испанский:"
        assert exercise.options is None
        assert exercise.correct_index is None
        assert len(exercise.alternatives) == 1

    def test_multiple_choice_exercise(self) -> None:
        """Test multiple choice exercise content."""
        data = {
            "question": "Выберите правильный вариант:",
            "prompt": "Yo ___ español",
            "correct_answer": "hablo",
            "explanation": "Present tense conjugation",
            "alternatives": [],
            "options": ["hablo", "hablas", "habla", "hablamos"],
            "correct_index": 0,
        }

        exercise = ExerciseContent(**data)

        assert len(exercise.options) == 4
        assert exercise.correct_index == 0
        assert exercise.options[exercise.correct_index] == "hablo"


class TestExerciseResult:
    """Tests for ExerciseResult model."""

    def test_correct_result(self) -> None:
        """Test correct exercise result."""
        data = {
            "result": "correct",
            "explanation": "Правильно! Вы использовали правильное время.",
            "correct_answer": "He trabajado",
            "alternatives": ["Trabajé"],
            "feedback": "Отлично! Продолжайте практиковаться.",
            "mistakes": [],
        }

        result = ExerciseResult(**data)

        assert result.result == "correct"
        assert len(result.mistakes) == 0

    def test_incorrect_result_with_mistakes(self) -> None:
        """Test incorrect result with detailed mistakes."""
        mistake1 = Mistake(
            type="grammar",
            description="Wrong tense used",
            suggestion="Use Pretérito Perfecto instead of Presente",
        )

        data = {
            "result": "incorrect",
            "explanation": "Неправильное время глагола",
            "correct_answer": "He trabajado",
            "alternatives": [],
            "feedback": "Попробуйте еще раз!",
            "mistakes": [mistake1.model_dump()],
        }

        result = ExerciseResult(**data)

        assert result.result == "incorrect"
        assert len(result.mistakes) == 1
        assert result.mistakes[0].type == "grammar"

    def test_result_literal_validation(self) -> None:
        """Test that only valid result values are accepted."""
        data = {
            "result": "invalid_result",  # Invalid value
            "explanation": "Test",
            "correct_answer": "Test",
            "alternatives": [],
            "feedback": "Test",
            "mistakes": [],
        }

        with pytest.raises(ValidationError):
            ExerciseResult(**data)


class TestIntentDetection:
    """Tests for IntentDetection model."""

    def test_translate_intent(self) -> None:
        """Test translation intent detection."""
        data = {
            "intent": "translate",
            "confidence": 0.95,
            "entities": {"word": "casa", "context": "asking for translation"},
        }

        intent = IntentDetection(**data)

        assert intent.intent == "translate"
        assert intent.confidence == 0.95
        assert intent.entities["word"] == "casa"

    def test_confidence_bounds(self) -> None:
        """Test confidence score validation (0.0-1.0)."""
        # Valid confidence
        IntentDetection(intent="general", confidence=0.5, entities={})

        # Invalid confidence > 1.0
        with pytest.raises(ValidationError):
            IntentDetection(intent="general", confidence=1.5, entities={})

        # Invalid confidence < 0.0
        with pytest.raises(ValidationError):
            IntentDetection(intent="general", confidence=-0.1, entities={})


class TestTopicSuggestion:
    """Tests for TopicSuggestion models."""

    def test_single_topic_suggestion(self) -> None:
        """Test single topic suggestion."""
        data = {
            "name": "Pretérito Perfecto",
            "description": "Прошедшее время для недавних действий",
            "type": "grammar",
            "reason": "Essential for B1 level",
            "examples": ["He trabajado", "Has comido", "Hemos viajado"],
        }

        topic = TopicSuggestion(**data)

        assert topic.name == "Pretérito Perfecto"
        assert topic.type == "grammar"
        assert len(topic.examples) == 3

    def test_topic_suggestions_list(self) -> None:
        """Test list of topic suggestions."""
        data = {
            "topics": [
                {
                    "name": "Irregular verbs",
                    "description": "Common irregular verbs",
                    "type": "vocabulary",
                    "reason": "Foundation for conversation",
                    "examples": ["ser", "estar", "ir"],
                },
                {
                    "name": "Restaurant situations",
                    "description": "Ordering food",
                    "type": "situation",
                    "reason": "Practical for travel",
                    "examples": ["menu", "bill", "table"],
                },
            ]
        }

        suggestions = TopicSuggestions(**data)

        assert len(suggestions.topics) == 2
        assert suggestions.topics[0].type == "vocabulary"
        assert suggestions.topics[1].type == "situation"


class TestWordSuggestion:
    """Tests for WordSuggestion models."""

    def test_word_suggestion(self) -> None:
        """Test word suggestion from text analysis."""
        data = {
            "word": "empezar",
            "type": "verb",
            "reason": "High-frequency verb for A2",
            "priority": 1,
        }

        suggestion = WordSuggestion(**data)

        assert suggestion.word == "empezar"
        assert suggestion.type == "verb"
        assert suggestion.priority == 1

    def test_priority_bounds(self) -> None:
        """Test priority validation (1-10)."""
        # Valid priority
        WordSuggestion(word="test", type="noun", reason="test", priority=5)

        # Invalid priority > 10
        with pytest.raises(ValidationError):
            WordSuggestion(word="test", type="noun", reason="test", priority=11)

        # Invalid priority < 1
        with pytest.raises(ValidationError):
            WordSuggestion(word="test", type="noun", reason="test", priority=0)

    def test_word_suggestions_list(self) -> None:
        """Test list of word suggestions."""
        data = {
            "suggestions": [
                {
                    "word": "casa",
                    "type": "noun",
                    "reason": "Basic vocabulary",
                    "priority": 1,
                },
                {
                    "word": "muy importante",
                    "type": "phrase",
                    "reason": "Useful phrase",
                    "priority": 2,
                },
            ]
        }

        suggestions = WordSuggestions(**data)

        assert len(suggestions.suggestions) == 2
        assert suggestions.suggestions[0].type == "noun"
        assert suggestions.suggestions[1].type == "phrase"


class TestSerializationDeserialization:
    """Tests for JSON serialization and deserialization."""

    def test_card_content_round_trip(self) -> None:
        """Test card content serialization and deserialization."""
        original = CardContent(
            word="test",
            lemma="test",
            translation="тест",
            example="Test example",
            example_translation="Тестовый пример",
        )

        # Serialize
        json_str = original.model_dump_json()

        # Deserialize
        deserialized = CardContent.model_validate_json(json_str)

        assert deserialized.word == original.word
        assert deserialized.lemma == original.lemma
        assert deserialized.translation == original.translation

    def test_exercise_result_round_trip(self) -> None:
        """Test exercise result serialization and deserialization."""
        original = ExerciseResult(
            result="partial",
            explanation="Almost correct",
            correct_answer="Correct answer",
            alternatives=["Alt 1", "Alt 2"],
            feedback="Good try!",
            mistakes=[
                Mistake(type="spelling", description="Minor typo", suggestion="Fix spelling")
            ],
        )

        # Serialize
        json_str = original.model_dump_json()

        # Deserialize
        deserialized = ExerciseResult.model_validate_json(json_str)

        assert deserialized.result == original.result
        assert len(deserialized.mistakes) == 1
        assert deserialized.mistakes[0].type == "spelling"
