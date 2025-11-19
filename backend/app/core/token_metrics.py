"""Prometheus metrics for tracking LLM token consumption and costs."""

from __future__ import annotations

from prometheus_client import Counter

OPERATION_LABEL = "operation"
MODEL_LABEL = "model"

LLM_PROMPT_TOKENS_TOTAL = Counter(
    "app_llm_prompt_tokens_total",
    "Total number of prompt tokens consumed by LLM requests.",
    labelnames=(OPERATION_LABEL, MODEL_LABEL),
)

LLM_COMPLETION_TOKENS_TOTAL = Counter(
    "app_llm_completion_tokens_total",
    "Total number of completion tokens produced by LLM responses.",
    labelnames=(OPERATION_LABEL, MODEL_LABEL),
)

LLM_TOTAL_TOKENS_TOTAL = Counter(
    "app_llm_total_tokens_total",
    "Total tokens (prompt + completion) consumed by LLM interactions.",
    labelnames=(OPERATION_LABEL, MODEL_LABEL),
)

LLM_ESTIMATED_COST_USD_TOTAL = Counter(
    "app_llm_estimated_cost_usd_total",
    "Estimated USD spent on LLM usage.",
    labelnames=(OPERATION_LABEL, MODEL_LABEL),
)


def _normalize_label(value: str | None, fallback: str) -> str:
    normalized = (value or "").strip().lower()
    return normalized or fallback


def _labels(operation: str | None, model: str | None) -> dict[str, str]:
    return {
        OPERATION_LABEL: _normalize_label(operation, "unspecified"),
        MODEL_LABEL: (model or "unknown").strip() or "unknown",
    }


def record_llm_usage_metrics(
    *,
    operation: str | None,
    model: str | None,
    prompt_tokens: int,
    completion_tokens: int,
    total_tokens: int,
    estimated_cost: float,
) -> None:
    """Increment Prometheus counters for the provided LLM usage snapshot."""
    labels = _labels(operation, model)

    LLM_PROMPT_TOKENS_TOTAL.labels(**labels).inc(max(prompt_tokens, 0))
    LLM_COMPLETION_TOKENS_TOTAL.labels(**labels).inc(max(completion_tokens, 0))
    LLM_TOTAL_TOKENS_TOTAL.labels(**labels).inc(max(total_tokens, 0))
    LLM_ESTIMATED_COST_USD_TOTAL.labels(**labels).inc(max(float(estimated_cost), 0.0))


__all__ = [
    "LLM_PROMPT_TOKENS_TOTAL",
    "LLM_COMPLETION_TOKENS_TOTAL",
    "LLM_TOTAL_TOKENS_TOTAL",
    "LLM_ESTIMATED_COST_USD_TOTAL",
    "record_llm_usage_metrics",
]
