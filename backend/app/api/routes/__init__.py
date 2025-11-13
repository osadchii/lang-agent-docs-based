"""Router aggregations for public API endpoints."""

from fastapi import APIRouter

from app.api.routes import health, telegram

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(telegram.router)

__all__ = ["api_router"]
