"""FastAPI application factory and entrypoint."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import api_router
from app.core.config import settings
from app.core.logging import configure_logging
from app.core.middleware import AccessLogMiddleware, RequestIDMiddleware
from app.core.version import APP_VERSION

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

    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=ALLOWED_METHODS,
        allow_headers=ALLOWED_HEADERS,
        max_age=86400,
    )

    application.add_middleware(RequestIDMiddleware)
    application.add_middleware(AccessLogMiddleware)

    application.include_router(api_router)

    return application


app = create_app()

__all__ = ["app", "create_app"]
