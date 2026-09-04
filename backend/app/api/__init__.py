"""API package with versioned routers and top-level endpoints."""

from app.api.health import router as health_router
from app.api.auth import router as auth_router

__all__ = ["health_router", "auth_router"]
