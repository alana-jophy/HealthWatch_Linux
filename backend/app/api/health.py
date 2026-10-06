from datetime import datetime
from fastapi import APIRouter, Response, status
from loguru import logger
from app.core.config import settings
from app.db.session import check_db_connection
from app.schemas.health import HealthResponse, DatabaseHealth

router = APIRouter(tags=["Health & Telemetry"])


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Application Health Check",
    description="Returns service status, environment, version, and database/PostGIS availability.",
)
def get_health(response: Response) -> HealthResponse:
    """Perform a health check on the backend and underlying database connection."""
    db_status = check_db_connection()
    is_connected = db_status.get("status") == "connected"

    if not is_connected:
        db_err = db_status.get("error", "Unknown database error")
        logger.error(f"[HEALTH CHECK FAILED] Database disconnected: {db_err}")
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    db_health = DatabaseHealth(
        status=db_status.get("status", "disconnected"),
        postgis_installed=db_status.get("postgis_installed", False),
        postgis_version=db_status.get("postgis_version"),
        postgis_full_version=db_status.get("postgis_full_version"),
        latency_ms=db_status.get("latency_ms"),
        error=db_status.get("error"),
    )

    return HealthResponse(
        status="ok" if is_connected else "degraded",
        app_name=settings.APP_NAME,
        version=settings.APP_VERSION,
        environment=settings.ENVIRONMENT,
        timestamp=datetime.utcnow(),
        database=db_health,
        system_info={
            "debug": settings.DEBUG,
            "api_version": settings.API_V1_STR,
        },
    )
