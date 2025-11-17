"""FastAPI application factory and entrypoint."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import api_router, root_router
from app.core.config import settings
from app.core.errors import register_exception_handlers
from app.core.logging import configure_logging
from app.core.metrics import setup_metrics
from app.core.middleware import (
    AccessLogMiddleware,
    RateLimitMiddleware,
    RequestIDMiddleware,
    RequestSizeLimitMiddleware,
    SecurityHeadersMiddleware,
)
from app.core.version import APP_VERSION
from app.services.notification_worker import notification_worker
from app.services.rate_limit import rate_limit_service
from app.services.rate_limit_worker import rate_limit_worker
from app.telegram import telegram_bot

ALLOWED_METHODS = ["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"]
ALLOWED_HEADERS = ["Authorization", "Content-Type", "Accept", "X-Requested-With"]

configure_logging(settings.log_level)


def create_app() -> FastAPI:
    """Build and configure the FastAPI application."""

    application = FastAPI(
        title=settings.project_name,
        debug=settings.debug,
        version=APP_VERSION,
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
    )

    register_exception_handlers(application)

    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=ALLOWED_METHODS,
        allow_headers=ALLOWED_HEADERS,
        max_age=86400,
    )

    setup_metrics(application)

    application.add_middleware(
        SecurityHeadersMiddleware,
        enable_hsts=settings.environment in {"staging", "production"},
    )
    application.add_middleware(AccessLogMiddleware)
    application.add_middleware(
        RequestSizeLimitMiddleware,
        max_request_bytes=settings.max_request_bytes,
    )
    application.add_middleware(
        RateLimitMiddleware,
        service=rate_limit_service,
    )
    application.add_middleware(RequestIDMiddleware)

    application.include_router(root_router)
    application.include_router(api_router)

    @application.on_event("startup")
    async def _configure_telegram_webhook() -> None:
        await telegram_bot.sync_webhook(settings.telegram_webhook_base_url)
        if settings.notifications_worker_enabled:
            notification_worker.start()
        if settings.rate_limit_worker_enabled and rate_limit_service.enabled:
            rate_limit_worker.start()

    @application.on_event("shutdown")
    async def _shutdown_telegram_bot() -> None:
        await telegram_bot.shutdown()
        if settings.notifications_worker_enabled:
            await notification_worker.shutdown()
        if settings.rate_limit_worker_enabled and rate_limit_service.enabled:
            await rate_limit_worker.shutdown()

    return application


app = create_app()

__all__ = ["app", "create_app"]
