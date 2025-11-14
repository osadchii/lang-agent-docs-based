"""Router aggregations for public API endpoints."""

from fastapi import APIRouter

from app.api.routes import auth, dialog, health, profiles, telegram

# Health and Telegram webhook routers (no prefix)
root_router = APIRouter()
root_router.include_router(health.router, tags=["health"])
root_router.include_router(telegram.router)

# API routers with /api prefix
api_router = APIRouter(prefix="/api")
api_router.include_router(auth.router)
api_router.include_router(dialog.router)
api_router.include_router(profiles.router)

__all__ = ["api_router", "root_router"]
