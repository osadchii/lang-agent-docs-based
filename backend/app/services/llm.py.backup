"""
LLM service for OpenAI integration.

Provides a robust adapter over OpenAI API with:
- Automatic retries with exponential backoff
- Comprehensive error handling
- Token usage tracking and logging
- Timeout configuration
- Feature flag for alternative LLM providers
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any

from openai import (
    APIConnectionError,
    APIError,
    AsyncOpenAI,
    AuthenticationError,
    BadRequestError,
    OpenAIError,
    RateLimitError,
)
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

logger = logging.getLogger("app.services.llm")


class LLMProvider(str, Enum):
    """Supported LLM providers."""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"  # For future implementation


@dataclass
class TokenUsage:
    """Token usage information from LLM API response."""

    prompt_tokens: int
    completion_tokens: int
    total_tokens: int

    @property
    def estimated_cost(self) -> float:
        """
        Calculate estimated cost based on token usage.

        Using GPT-4o-mini pricing: $0.15/1M input, $0.60/1M output tokens.
        """
        input_cost = (self.prompt_tokens / 1_000_000) * 0.15
        output_cost = (self.completion_tokens / 1_000_000) * 0.60
        return input_cost + output_cost


class LLMService:
    """Service for interacting with LLM APIs (OpenAI, Anthropic)."""

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o-mini",
        temperature: float = 0.7,
        provider: LLMProvider = LLMProvider.OPENAI,
        default_timeout: float = 30.0,
    ) -> None:
        """
        Initialize LLM service.

        Args:
            api_key: API key for the LLM provider
            model: Model to use (default: gpt-4o-mini)
            temperature: Default sampling temperature (0.0-1.0)
            provider: LLM provider to use (default: OpenAI)
            default_timeout: Default request timeout in seconds
        """
        self.model = model
        self.default_temperature = temperature
        self.provider = provider
        self.default_timeout = default_timeout

        if provider == LLMProvider.OPENAI:
            self.client = AsyncOpenAI(api_key=api_key, timeout=default_timeout)
        elif provider == LLMProvider.ANTHROPIC:
            # Future implementation for Anthropic Claude
            raise NotImplementedError("Anthropic provider is not yet implemented")
        else:
            raise ValueError(f"Unsupported LLM provider: {provider}")

        logger.info(
            "LLM service initialized",
            extra={
                "provider": provider.value,
                "model": model,
                "temperature": temperature,
            },
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((RateLimitError, APIConnectionError, APIError)),
        reraise=True,
    )
    async def chat(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
        timeout: float | None = None,
        response_format: dict[str, Any] | None = None,
    ) -> tuple[str, TokenUsage]:
        """
        Send chat completion request to LLM with automatic retries.

        Args:
            messages: List of messages in OpenAI format
            temperature: Sampling temperature (0.0-1.0), uses default if None
            max_tokens: Maximum tokens to generate
            timeout: Request timeout in seconds, uses default if None
            response_format: Response format specification (e.g., {"type": "json_object"})

        Returns:
            Tuple of (response_text, token_usage)

        Raises:
            AuthenticationError: Invalid API key
            BadRequestError: Invalid request parameters
            RateLimitError: Rate limit exceeded (after retries)
            APIConnectionError: Connection error (after retries)
            OpenAIError: Other API errors
        """
        if self.provider != LLMProvider.OPENAI:
            raise NotImplementedError(f"Provider {self.provider} not yet supported")

        try:
            response = await self.client.chat.completions.create(  # type: ignore[call-overload]
                model=self.model,
                messages=messages,
                temperature=temperature if temperature is not None else self.default_temperature,
                max_tokens=max_tokens,
                timeout=timeout or self.default_timeout,
                response_format=response_format,
            )

            content = response.choices[0].message.content
            if content is None:
                logger.error("LLM returned null content")
                return "", TokenUsage(0, 0, 0)

            # Extract token usage
            usage = TokenUsage(
                prompt_tokens=response.usage.prompt_tokens if response.usage else 0,
                completion_tokens=response.usage.completion_tokens if response.usage else 0,
                total_tokens=response.usage.total_tokens if response.usage else 0,
            )

            logger.info(
                "LLM request completed successfully",
                extra={
                    "provider": self.provider.value,
                    "model": self.model,
                    "prompt_tokens": usage.prompt_tokens,
                    "completion_tokens": usage.completion_tokens,
                    "total_tokens": usage.total_tokens,
                    "estimated_cost_usd": f"{usage.estimated_cost:.6f}",
                },
            )

            return content, usage

        except AuthenticationError as e:
            logger.error("LLM authentication failed", extra={"error": str(e)})
            raise
        except BadRequestError as e:
            logger.error(
                "LLM bad request", extra={"error": str(e), "messages_count": len(messages)}
            )
            raise
        except RateLimitError as e:
            logger.warning("LLM rate limit exceeded, retrying", extra={"error": str(e)})
            raise
        except APIConnectionError as e:
            logger.warning("LLM connection error, retrying", extra={"error": str(e)})
            raise
        except OpenAIError as e:
            logger.error("LLM API error", extra={"error": str(e), "error_type": type(e).__name__})
            raise


def get_basic_system_prompt(language_code: str | None = None) -> str:
    """
    Get basic system prompt for language teacher.

    Args:
        language_code: User's language code from Telegram

    Returns:
        System prompt text
    """
    # Minimal prompt version for initial implementation
    # In the future will be loaded from prompts/ and rendered via Jinja2
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


__all__ = ["LLMService", "LLMProvider", "TokenUsage", "get_basic_system_prompt"]
