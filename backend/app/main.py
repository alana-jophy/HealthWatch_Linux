from contextlib import asynccontextmanager
import os
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.api.auth import router as auth_router
from app.api.health import router as health_router
from app.api.locations import router as locations_router
from app.api.v1.router import api_v1_router
from app.core.config import settings
from app.core.exceptions import (
    HealthWatchException,
    generic_http_exception_handler,
    global_exception_handler,
    healthwatch_exception_handler,
    validation_exception_handler,
)
from app.core.logging import setup_logging
from app.db.init_db import init_db
from app.db.session import check_db_connection


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context for startup and shutdown procedures."""
    # Startup
    setup_logging()
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION} in [{settings.ENVIRONMENT}] mode")
    
    logger.info("Verifying database connectivity...")
    db_check = check_db_connection()
    if db_check.get("status") == "connected":
        logger.info(f"Database connected successfully. PostGIS: {db_check.get('postgis_version')}")
        # Initialize tables, default roles, and synthetic test users
        try:
            init_db()
        except Exception as exc:
            logger.error(f"Database initialization failed: {exc}")
    else:
        logger.error(f"CRITICAL: Database startup check failed: {db_check.get('status')} - {db_check.get('error')}")

    yield

    # Shutdown
    logger.info(f"Shutting down {settings.APP_NAME} gracefully...")


def create_application() -> FastAPI:
    """FastAPI Application Factory."""
    application = FastAPI(
        title=settings.APP_NAME,
        description="Intelligent Disease Surveillance & Outbreak Monitoring API",
        version=settings.APP_VERSION,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # Configure CORS Middleware (Permit localhost and private LAN RFC 1918 addresses for mobile testing)
    cors_origins = [str(origin) for origin in settings.BACKEND_CORS_ORIGINS] if settings.BACKEND_CORS_ORIGINS else ["*"]
    application.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_origin_regex=r"^http:\/\/(localhost|127\.0\.0\.1|192\.168\.\d+\.\d+|10\.\d+\.\d+\.\d+|172\.(1[6-9]|2\d|3[0-1])\.\d+\.\d+)(:\d+)?$",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register Exception Handlers
    application.add_exception_handler(HealthWatchException, healthwatch_exception_handler)
    application.add_exception_handler(RequestValidationError, validation_exception_handler)
    application.add_exception_handler(HTTPException, generic_http_exception_handler)
    application.add_exception_handler(Exception, global_exception_handler)

    # Register Top-level Routers
    # Serves GET /api/health
    application.include_router(health_router, prefix="/api")

    # Serves POST /api/auth/register, POST /api/auth/login, GET /api/auth/me, etc.
    application.include_router(auth_router, prefix="/api")

    # Serves POST /api/locations (Android client location telemetry ingestion)
    application.include_router(locations_router, prefix="/api/locations", tags=["Location Telemetry Ingestion"])

    # Serves /api/v1/*
    application.include_router(api_v1_router, prefix=settings.API_V1_STR)

    @application.get("/download/app", tags=["Mobile App"], summary="Download Native Android APK")
    @application.get("/download/healthwatch.apk", tags=["Mobile App"], summary="Download Native Android APK")
    @application.get("/HealthWatch.apk", tags=["Mobile App"], summary="Download Native Android APK")
    def download_android_apk():
        apk_path = os.path.join(os.path.dirname(__file__), "HealthWatch.apk")
        if not os.path.exists(apk_path):
            raise HTTPException(status_code=404, detail="HealthWatch.apk not found on server")
        return FileResponse(
            path=apk_path,
            media_type="application/vnd.android.package-archive",
            filename="HealthWatch.apk"
        )

    @application.get("/", tags=["Root"])
    def root():
        return {
            "name": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "status": "online",
            "docs": "/docs",
            "health": "/api/health",
            "auth": {
                "login": "/api/auth/login",
                "register": "/api/auth/register",
                "me": "/api/auth/me",
            },
        }

    return application


app = create_application()
