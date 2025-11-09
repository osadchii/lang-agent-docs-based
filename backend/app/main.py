"""
Main FastAPI application entry point.

This module creates and configures the FastAPI application according to
docs/architecture.md (Backend structure).
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routers import router
from app.core.config import settings
from app.core.logging import setup_logging, get_logger

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
    # TODO: Initialize Redis client
    # TODO: Setup Telegram bot webhook (production) or long polling (development)


@app.on_event("shutdown")
async def shutdown_event() -> None:
    """
    Application shutdown event handler.

    Cleanly closes all connections and background tasks.
    """
    logger.info("Shutting down application")
    # TODO: Close database connections
    # TODO: Close Redis client
    # TODO: Stop background tasks


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.ENVIRONMENT == "development"
    )
