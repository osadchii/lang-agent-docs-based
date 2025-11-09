"""
Main FastAPI application entry point.

This module creates and configures the FastAPI application according to
docs/architecture.md (Backend structure).
"""

from typing import Any, Dict
from uuid import UUID

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from jose import JWTError
from redis.exceptions import RedisError

from app.api.routers import router
from app.core.config import settings
from app.core.logging import get_logger, setup_logging
from app.core.redis import redis_manager
from app.core.security import decode_access_token
from app.services.rate_limit_service import (
    RateLimitExceededError,
    RateLimitResult,
    get_rate_limit_service,
)

# Setup logging
setup_logging()
logger = get_logger(__name__)

# Create FastAPI application
app = FastAPI(
    title="Language Learning AI Assistant",
    description="Telegram bot for language learning with AI teacher",
    version=settings.APP_VERSION,
    docs_url="/api/docs" if settings.ENVIRONMENT == "development" else None,
    redoc_url="/api/redoc" if settings.ENVIRONMENT == "development" else None,
)

# Configure CORS for Telegram Mini App
# According to docs/backend-api.md, we need to allow webapp.telegram.org
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://webapp.telegram.org"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
    max_age=86400,
)

# Include API routers
app.include_router(router, prefix="/api", tags=["api"])


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """Add security headers required by docs/backend-auth.md."""

    response = await call_next(request)

    if settings.SECURITY_HEADERS_ENABLED:
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("X-XSS-Protection", "1; mode=block")
        if request.url.scheme == "https" or settings.ENVIRONMENT != "development":
            response.headers.setdefault(
                "Strict-Transport-Security",
                "max-age=31536000; includeSubDomains",
            )
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "connect-src 'self' https://api.telegram.org",
        )
        response.headers.setdefault(
            "Referrer-Policy", "strict-origin-when-cross-origin"
        )
        response.headers.setdefault(
            "Permissions-Policy", "geolocation=(), microphone=(), camera=()"
        )

    return response


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    """Global rate limiting middleware."""

    service = get_rate_limit_service()
    client_ip = request.client.host if request.client else "unknown"
    ip_result: RateLimitResult | None = None

    try:
        ip_result = await service.enforce_global_ip_limit(client_ip)

        user_id = _extract_user_id(request)
        if user_id is not None:
            await service.enforce_global_user_limit(user_id)

    except RateLimitExceededError as exc:
        return _rate_limit_error_response(exc)

    response = await call_next(request)

    if ip_result is not None:
        headers = ip_result.headers()
        for header, value in headers.items():
            response.headers.setdefault(header, value)

    return response


@app.on_event("startup")
async def startup_event() -> None:
    """
    Application startup event handler.

    Initializes connections to external services:
    - Database connection pool
    - Redis client
    - Background tasks
    """
    logger.info(
        f"Starting Language Learning AI Assistant v{settings.APP_VERSION} "
        f"in {settings.ENVIRONMENT} mode"
    )
    # TODO: Initialize database connection
    try:
        await redis_manager.connect()
    except RedisError as exc:
        logger.warning("Redis connection failed during startup: %s", exc)
    # TODO: Setup Telegram bot webhook (production) or long polling (development)


@app.on_event("shutdown")
async def shutdown_event() -> None:
    """
    Application shutdown event handler.

    Cleanly closes all connections and background tasks.
    """
    logger.info("Shutting down application")
    # TODO: Close database connections
    await redis_manager.close()
    # TODO: Stop background tasks


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.ENVIRONMENT == "development"
    )


def _extract_user_id(request: Request) -> UUID | None:
    """Return user UUID from Authorization header if present."""

    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return None

    token = auth_header.replace("Bearer ", "", 1).strip()
    if not token:
        return None

    try:
        payload = decode_access_token(token)
    except JWTError:
        return None

    user_id_str = payload.get("user_id")
    if not user_id_str:
        return None

    try:
        return UUID(user_id_str)
    except ValueError:
        return None


def _rate_limit_error_response(error: RateLimitExceededError) -> JSONResponse:
    """Format rate limit errors according to docs/backend-api.md."""

    body: Dict[str, Any] = {
        "error": {
            "code": error.error_code,
            "message": error.message,
            "details": error.details or {},
        }
    }

    if error.result.retry_after is not None:
        body["error"]["retry_after"] = error.result.retry_after

    headers = error.result.headers()
    return JSONResponse(
        status_code=429,
        content=body,
        headers=headers,
    )
