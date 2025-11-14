"""Router aggregations for public API endpoints."""

from fastapi import APIRouter

from app.api.routes import auth, cards, decks, dialog, exercises, health, profiles, telegram, topics

# Health and Telegram webhook routers (no prefix)
root_router = APIRouter()
root_router.include_router(health.router, tags=["health"])
root_router.include_router(telegram.router)

# API routers with /api prefix
api_router = APIRouter(prefix="/api")
api_router.include_router(auth.router)
api_router.include_router(decks.router)
api_router.include_router(cards.router)
api_router.include_router(dialog.router)
api_router.include_router(profiles.router)
api_router.include_router(topics.router)
api_router.include_router(exercises.router)

__all__ = ["api_router", "root_router"]
