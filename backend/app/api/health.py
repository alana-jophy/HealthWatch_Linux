from datetime import datetime
from fastapi import APIRouter, status
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
def get_health() -> HealthResponse:
    """Perform a health check on the backend and underlying database connection."""
    db_status = check_db_connection()

    db_health = DatabaseHealth(
        status=db_status.get("status", "disconnected"),
        postgis_installed=db_status.get("postgis_installed", False),
        postgis_version=db_status.get("postgis_version"),
        postgis_full_version=db_status.get("postgis_full_version"),
        latency_ms=db_status.get("latency_ms"),
        error=db_status.get("error"),
    )

    return HealthResponse(
        status="ok",
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
