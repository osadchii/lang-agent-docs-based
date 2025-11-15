from __future__ import annotations

import uuid
from pathlib import Path

import pytest

from app.models.language_profile import LanguageProfile
from app.services.prompts import (
    PromptRenderer,
    count_tokens,
    count_tokens_for_messages,
    get_basic_system_prompt,
    get_system_prompt_for_profile,
)


def _profile() -> LanguageProfile:
    return LanguageProfile(
        user_id=uuid.uuid4(),
        language="es",
        language_name="Spanish",
        current_level="A2",
        target_level="B1",
        goals=["travel"],
        interface_language="ru",
        is_active=True,
    )


def test_count_tokens_fallback_encoding() -> None:
    tokens = count_tokens("hola, ¿qué tal?", model="unknown-model")
    assert tokens > 0


def test_count_tokens_for_messages_counts_overhead() -> None:
    messages = [
        {"role": "system", "content": "Intro", "name": "teacher"},
        {"role": "user", "content": "Hola"},
    ]
    tokens = count_tokens_for_messages(messages, model="unknown-model")
    assert tokens >= 10


def test_prompt_renderer_renders_template(tmp_path: Path) -> None:
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()
    system_dir = prompts_dir / "system"
    system_dir.mkdir()
    template_path = system_dir / "teacher.txt"
    template_path.write_text("Hola {{ name }}!", encoding="utf-8")

    renderer = PromptRenderer(prompts_dir=prompts_dir)
    rendered = renderer.render("system/teacher.txt", {"name": "Maria"})

    assert rendered == "Hola Maria!"


def test_get_system_prompt_falls_back_when_template_missing(tmp_path: Path) -> None:
    prompts_dir = tmp_path / "empty"
    prompts_dir.mkdir()
    renderer = PromptRenderer(prompts_dir=prompts_dir)
    prompt = get_system_prompt_for_profile(renderer, _profile())

    assert "language teacher" in prompt


def test_get_basic_system_prompt_uses_language_hint() -> None:
    prompt = get_basic_system_prompt(language_code="en")
    assert "Respond in English" in prompt
