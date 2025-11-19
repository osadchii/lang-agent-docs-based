"""Tests for Prometheus metrics helpers."""

from __future__ import annotations

from app.core.token_metrics import (
    LLM_COMPLETION_TOKENS_TOTAL,
    LLM_ESTIMATED_COST_USD_TOTAL,
    LLM_PROMPT_TOKENS_TOTAL,
    LLM_TOTAL_TOKENS_TOTAL,
    record_llm_usage_metrics,
)


def _label_tuple(labels: dict[str, str]) -> tuple[str, str]:
    return (labels["operation"], labels["model"])


def _reset_labels(labels: dict[str, str]) -> None:
    label_values = _label_tuple(labels)
    for counter in (
        LLM_PROMPT_TOKENS_TOTAL,
        LLM_COMPLETION_TOKENS_TOTAL,
        LLM_TOTAL_TOKENS_TOTAL,
        LLM_ESTIMATED_COST_USD_TOTAL,
    ):
        try:
            counter.remove(*label_values)
        except KeyError:
            continue


def test_record_llm_usage_metrics_increments_counters() -> None:
    """Ensure each counter is incremented with the provided values."""
    labels = {"operation": "unit_test_op", "model": "unit-test-model"}
    _reset_labels(labels)

    record_llm_usage_metrics(
        operation=labels["operation"],
        model=labels["model"],
        prompt_tokens=120,
        completion_tokens=80,
        total_tokens=200,
        estimated_cost=0.005,
    )

    label_values = _label_tuple(labels)
    assert (
        LLM_PROMPT_TOKENS_TOTAL.labels(*label_values)._value.get() == 120  # type: ignore[attr-defined]
    )
    assert (
        LLM_COMPLETION_TOKENS_TOTAL.labels(*label_values)._value.get()
        == 80  # type: ignore[attr-defined]
    )
    assert (
        LLM_TOTAL_TOKENS_TOTAL.labels(*label_values)._value.get() == 200  # type: ignore[attr-defined]
    )
    assert (
        LLM_ESTIMATED_COST_USD_TOTAL.labels(*label_values)._value.get()
        == 0.005  # type: ignore[attr-defined]
    )
