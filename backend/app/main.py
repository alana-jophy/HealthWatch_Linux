from contextlib import asynccontextmanager
import os
import shutil
from fastapi import FastAPI, HTTPException, status
from fastapi.responses import FileResponse, RedirectResponse
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


def cleanup_obsolete_apks() -> int:
    """Scans the backend application directory and purges any APK files
    belonging to previous/deprecated versions, preserving only the current active version."""
    base_dir = os.path.dirname(__file__)
    current_ver = settings.APP_VERSION
    active_version_file = f"HealthWatch-v{current_ver}.apk"
    canonical_file = "HealthWatch.apk"
    removed = 0

    try:
        if not os.path.exists(base_dir):
            return 0
        for fname in os.listdir(base_dir):
            if not fname.endswith(".apk"):
                continue
            # Target versioned APKs that do not match the active release
            if fname.startswith("HealthWatch-") and fname != active_version_file and fname != f"HealthWatch-{current_ver}.apk":
                full_path = os.path.join(base_dir, fname)
                try:
                    os.remove(full_path)
                    logger.warning(
                        f"[APK PURGE] Removed obsolete APK installer from server: {fname} "
                        f"(Active target: {active_version_file})"
                    )
                    removed += 1
                except Exception as err:
                    logger.error(f"[APK PURGE ERROR] Could not remove {fname}: {err}")

        # Ensure canonical HealthWatch.apk matches active version APK if present
        active_path = os.path.join(base_dir, active_version_file)
        canonical_path = os.path.join(base_dir, canonical_file)
        if os.path.exists(active_path):
            shutil.copyfile(active_path, canonical_path)
    except Exception as exc:
        logger.error(f"[APK PURGE] Error scanning APK directory: {exc}")

    return removed


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context for startup and shutdown procedures."""
    # Startup
    setup_logging()
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION} in [{settings.ENVIRONMENT}] mode")

    # Purge old APK files from server disk on application boot
    cleaned_count = cleanup_obsolete_apks()
    if cleaned_count > 0:
        logger.info(f"Purged {cleaned_count} obsolete APK release(s) on server boot")
    
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
    @application.api_route("/HealthWatch.apk", methods=["GET", "HEAD"], tags=["Mobile App"], summary="Download Native Android APK")
    @application.api_route("/HealthWatch-{version_tag}.apk", methods=["GET", "HEAD"], tags=["Mobile App"], summary="Download Versioned Native Android APK")
    def download_android_apk(version_tag: str = None):
        base_dir = os.path.dirname(__file__)
        current_version = settings.APP_VERSION
        v_name = f"HealthWatch-v{current_version}.apk"

        # Anti-stale-version redirect:
        # If the client specifies an outdated version tag (e.g. HealthWatch-v1.0.5.apk),
        # redirect immediately (307 Temporary Redirect) to the current active release.
        # This completely guarantees that no client phone downloads or installs an obsolete version.
        if version_tag:
            clean_tag = version_tag.lstrip("v")
            if clean_tag != current_version:
                logger.warning(
                    f"[APK ROUTE] Client requested obsolete version '{version_tag}'. "
                    f"Redirecting to active release 'v{current_version}'."
                )
                return RedirectResponse(
                    url=f"/HealthWatch-v{current_version}.apk",
                    status_code=status.HTTP_307_TEMPORARY_REDIRECT,
                    headers={
                        "Cache-Control": "no-store, no-cache, must-revalidate, proxy-revalidate, max-age=0",
                        "Pragma": "no-cache",
                        "Expires": "0",
                        "X-App-Version": current_version,
                        "X-Requested-Version": version_tag,
                    },
                )

        candidates = [
            os.path.join(base_dir, v_name),
            os.path.join(base_dir, f"HealthWatch-{current_version}.apk"),
            os.path.join(base_dir, "HealthWatch.apk"),
        ]

        target_path = None
        for cand in candidates:
            if os.path.exists(cand):
                target_path = cand
                break

        if not target_path:
            # Fallback: scan for any HealthWatch*.apk in base_dir
            for f in os.listdir(base_dir):
                if f.endswith(".apk") and f.startswith("HealthWatch"):
                    target_path = os.path.join(base_dir, f)
                    break

        if not target_path:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"HealthWatch APK installer (v{current_version}) not found on server",
            )

        return FileResponse(
            path=target_path,
            media_type="application/vnd.android.package-archive",
            filename=v_name,
            headers={
                "Cache-Control": "no-store, no-cache, must-revalidate, proxy-revalidate, max-age=0",
                "Pragma": "no-cache",
                "Expires": "0",
                "X-App-Version": current_version,
            },
        )

    @application.api_route("/api/apk/info", methods=["GET", "HEAD"], tags=["Mobile App"], summary="Get Current APK Release Metadata")
    def get_apk_release_info():
        base_dir = os.path.dirname(__file__)
        current_version = settings.APP_VERSION
        v_name = f"HealthWatch-v{current_version}.apk"
        apk_path = os.path.join(base_dir, v_name)
        if not os.path.exists(apk_path):
            apk_path = os.path.join(base_dir, "HealthWatch.apk")

        file_size = os.path.getsize(apk_path) if os.path.exists(apk_path) else 0
        exists = os.path.exists(apk_path)

        return {
            "app_name": settings.APP_NAME,
            "version": current_version,
            "available": exists,
            "size_bytes": file_size,
            "download_url": f"/HealthWatch-v{current_version}.apk",
            "canonical_url": "/HealthWatch.apk",
            "filename": v_name,
        }

    @application.get("/", tags=["Root"])
    def root():
        return {
            "name": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "apk_download": f"/HealthWatch-v{settings.APP_VERSION}.apk",
            "apk_filename": f"HealthWatch-v{settings.APP_VERSION}.apk",
            "apk_info": "/api/apk/info",
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
