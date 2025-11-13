"""LLM service for OpenAI integration."""

from __future__ import annotations

import logging

from openai import AsyncOpenAI, OpenAIError

logger = logging.getLogger("app.services.llm")


class LLMService:
    """Service for interacting with OpenAI API."""

    def __init__(self, api_key: str, model: str = "gpt-4o-mini") -> None:
        """
        Initialize LLM service.

        Args:
            api_key: OpenAI API key
            model: Model to use (default: gpt-4o-mini)
        """
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model
        self.default_timeout = 30.0  # 30 seconds timeout

    async def chat(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        timeout: float | None = None,
    ) -> str:
        """
        Send chat completion request to OpenAI.

        Args:
            messages: List of messages in OpenAI format
            temperature: Sampling temperature (0.0-2.0)
            max_tokens: Maximum tokens to generate
            timeout: Request timeout in seconds

        Returns:
            Generated response text

        Raises:
            OpenAIError: If API request fails
        """
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,  # type: ignore[arg-type]
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=timeout or self.default_timeout,
            )

            content = response.choices[0].message.content
            if content is None:
                logger.error("OpenAI returned null content")
                return ""

            logger.info(
                "LLM request completed",
                extra={
                    "model": self.model,
                    "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                    "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                },
            )

            return content

        except OpenAIError as e:
            logger.error(f"OpenAI API error: {e}")
            raise


def get_basic_system_prompt(language_code: str | None = None) -> str:
    """
    Get basic system prompt for language teacher.

    Args:
        language_code: User's language code from Telegram

    Returns:
        System prompt text
    """
    # Минимальная версия промпта для начала
    # В будущем будет загружаться из prompts/ и рендериться через Jinja2
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


__all__ = ["LLMService", "get_basic_system_prompt"]
