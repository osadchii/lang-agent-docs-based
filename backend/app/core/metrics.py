"""Prometheus instrumentation helpers for the FastAPI application."""

from __future__ import annotations

import os
from typing import Callable, cast

from fastapi import FastAPI
from fastapi.responses import Response
from prometheus_client import CollectorRegistry, Histogram, multiprocess
from prometheus_client.openmetrics.exposition import generate_latest as generate_openmetrics
from prometheus_fastapi_instrumentator import Instrumentator, metrics

REQUEST_LATENCY_BUCKETS = (
    0.01,
    0.025,
    0.05,
    0.075,
    0.1,
    0.25,
    0.5,
    0.75,
    1.0,
    2.5,
    5.0,
    7.5,
    10.0,
    15.0,
    30.0,
    60.0,
    float("inf"),
)


def setup_metrics(app: FastAPI) -> None:
    """Attach Prometheus instrumentation and expose the /metrics endpoint."""

    instrumentator = Instrumentator(
        should_group_status_codes=False,
        should_ignore_untemplated=True,
        should_round_latency_decimals=True,
        round_latency_decimals=4,
        should_respect_env_var=False,
        should_instrument_requests_inprogress=True,
        excluded_handlers=[r"/metrics"],
    )

    instrumentator.add(
        metrics.default(
            should_only_respect_2xx_for_highr=True,
            should_exclude_streaming_duration=True,
        )
    )

    instrumentator.add(_latency_with_request_id())

    instrumentator.instrument(app)
    _register_metrics_endpoint(app, instrumentator.registry)


def _latency_with_request_id() -> Callable[[metrics.Info], None] | None:
    """Record per-endpoint latency while storing request_id as exemplar."""

    try:
        latency_histogram = Histogram(
            "app_request_latency_seconds",
            "Latency distribution enriched with request_id exemplars.",
            labelnames=("handler", "method", "status"),
            buckets=REQUEST_LATENCY_BUCKETS,
        )
    except ValueError as error:  # pragma: no cover - occurs only on reload
        if "Duplicated timeseries" in str(error) or "Duplicated time series" in str(error):
            return None
        raise

    def instrumentation(info: metrics.Info) -> None:
        request_id = getattr(info.request.state, "request_id", None)
        exemplar = {"request_id": request_id} if request_id else None

        labels = (info.modified_handler, info.method, info.modified_status)

        try:
            latency_histogram.labels(*labels).observe(info.modified_duration, exemplar=exemplar)
        except TypeError:
            latency_histogram.labels(*labels).observe(info.modified_duration)

    return instrumentation


def _register_metrics_endpoint(app: FastAPI, registry: CollectorRegistry) -> None:
    """Expose /metrics in OpenMetrics format to preserve exemplars."""

    @app.get("/metrics", include_in_schema=False, tags=["observability"])
    async def metrics_endpoint() -> Response:
        active_registry = registry
        if "PROMETHEUS_MULTIPROC_DIR" in os.environ:
            active_registry = CollectorRegistry()
            collector = cast(
                Callable[[CollectorRegistry], None],
                multiprocess.MultiProcessCollector,
            )
            collector(active_registry)

        generate = cast(
            Callable[[CollectorRegistry], bytes],
            generate_openmetrics,
        )
        payload = generate(active_registry)
        media_type = "application/openmetrics-text; version=1.0.0; charset=utf-8"
        return Response(content=payload, media_type=media_type)


__all__ = ["setup_metrics"]
