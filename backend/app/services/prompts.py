"""
Prompt rendering utilities for LLM service.

Provides Jinja2-based template rendering for system prompts and other
LLM interactions.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

import tiktoken
from jinja2 import Environment, FileSystemLoader

if TYPE_CHECKING:
    from app.models.language_profile import LanguageProfile

logger = logging.getLogger("app.services.prompts")


def count_tokens(text: str, model: str = "gpt-4o-mini") -> int:
    """
    Count tokens in text using tiktoken.

    Args:
        text: Text to count tokens for
        model: Model name for encoding (default: gpt-4o-mini)

    Returns:
        Number of tokens in the text
    """
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        # Fallback to cl100k_base for unknown models (used by GPT-4)
        encoding = tiktoken.get_encoding("cl100k_base")

    return len(encoding.encode(text))


def count_tokens_for_messages(messages: list[dict[str, str]], model: str = "gpt-4o-mini") -> int:
    """
    Count tokens for a list of messages, accounting for OpenAI's message formatting overhead.

    Args:
        messages: List of message dicts with 'role' and 'content' keys
        model: Model name for encoding

    Returns:
        Total number of tokens including overhead
    """
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        encoding = tiktoken.get_encoding("cl100k_base")

    tokens_per_message = 3  # <|start|>role<|end|>content<|end|>
    tokens_per_name = 1  # For message with 'name' field

    num_tokens = 0

    for message in messages:
        num_tokens += tokens_per_message
        for key, value in message.items():
            num_tokens += len(encoding.encode(value))
            if key == "name":
                num_tokens += tokens_per_name

    num_tokens += 3  # Every reply is primed with <|start|>assistant<|message|>

    return num_tokens


class PromptRenderer:
    """Renders prompts from Jinja2 templates."""

    def __init__(self, prompts_dir: str | Path = "prompts") -> None:
        """
        Initialize prompt renderer.

        Args:
            prompts_dir: Path to directory containing prompt templates
        """
        self.prompts_dir = Path(prompts_dir)

        if not self.prompts_dir.exists():
            logger.warning(f"Prompts directory does not exist: {self.prompts_dir.absolute()}")

        self.jinja_env = Environment(
            loader=FileSystemLoader(str(self.prompts_dir)),
            trim_blocks=True,
            lstrip_blocks=True,
            autoescape=False,  # Prompts are plain text, not HTML  # noqa: S701
        )

        logger.info(f"Prompt renderer initialized with directory: {self.prompts_dir.absolute()}")

    def render(self, template_name: str, context: dict[str, Any]) -> str:
        """
        Render a prompt template with given context.

        Args:
            template_name: Name of template file (e.g., "system/teacher.txt")
            context: Dictionary of variables to render in template

        Returns:
            Rendered prompt text

        Raises:
            jinja2.TemplateNotFound: If template file doesn't exist
            jinja2.TemplateSyntaxError: If template has syntax errors
        """
        template = self.jinja_env.get_template(template_name)
        rendered: str = template.render(**context)

        logger.debug(
            "Rendered prompt template",
            extra={
                "template": template_name,
                "context_keys": list(context.keys()),
                "rendered_length": len(rendered),
            },
        )

        return rendered


def get_system_prompt_for_profile(renderer: PromptRenderer, profile: LanguageProfile) -> str:
    """
    Get system prompt for a language profile.

    Args:
        renderer: PromptRenderer instance
        profile: LanguageProfile instance

    Returns:
        Rendered system prompt
    """
    context = {
        "language": profile.language,
        "language_name": profile.language_name,
        "current_level": profile.current_level,
        "target_level": profile.target_level,
        "goals": profile.goals,
        "interface_language": profile.interface_language,
    }

    try:
        return renderer.render("system/teacher.txt", context)
    except Exception as e:
        logger.warning(f"Failed to render prompt from template: {e}. Falling back to basic prompt.")
        # Fallback to basic prompt if template rendering fails
        return get_basic_system_prompt(profile.interface_language)


def get_basic_system_prompt(language_code: str | None = None) -> str:
    """
    Get basic system prompt for language teacher (fallback).

    This is a fallback when prompt templates are not available.

    Args:
        language_code: User's language code from Telegram

    Returns:
        System prompt text
    """
    interface_lang = "Russian" if language_code in ("ru", None) else "English"

    return f"""You are a professional language teacher helping students learn new languages.

Your role:
- Answer questions about language learning
- Provide clear, helpful explanations
- Be encouraging and supportive
- Keep responses concise and focused

Communication:
- Respond in {interface_lang}
- Use simple, clear language
- Provide examples when helpful
- Stay on topic (language learning)

If the user asks something not related to language learning,
politely redirect them to language topics.
"""


__all__ = [
    "PromptRenderer",
    "count_tokens",
    "count_tokens_for_messages",
    "get_system_prompt_for_profile",
    "get_basic_system_prompt",
]
