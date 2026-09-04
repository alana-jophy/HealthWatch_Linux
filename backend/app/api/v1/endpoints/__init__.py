"""API v1 Endpoints Package."""

from app.api.v1.endpoints.patients import router as patients_router
from app.api.v1.endpoints.diseases import router as diseases_router
from app.api.v1.endpoints.cases import router as cases_router
from app.api.v1.endpoints.gis import router as gis_router
from app.api.v1.endpoints.monitoring import router as monitoring_router

__all__ = ["patients_router", "diseases_router", "cases_router", "gis_router", "monitoring_router"]
