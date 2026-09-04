"""API Version 1 Router Module."""

from fastapi import APIRouter
from app.api.v1.endpoints.patients import router as patients_router
from app.api.v1.endpoints.diseases import router as diseases_router
from app.api.v1.endpoints.cases import router as cases_router
from app.api.v1.endpoints.gis import router as gis_router
from app.api.v1.endpoints.monitoring import router as monitoring_router
from app.api.v1.endpoints.exposure import router as exposure_router
from app.api.v1.endpoints.surveillance import router as surveillance_router
from app.api.v1.endpoints.reports import router as reports_router
from app.api.v1.endpoints.predictions import router as predictions_router
from app.api.v1.endpoints.users import router as users_router
from app.api.locations import router as locations_router

api_v1_router = APIRouter()

# Register Resource Routers
api_v1_router.include_router(patients_router, prefix="/patients", tags=["Patient Management"])
api_v1_router.include_router(diseases_router, prefix="/diseases", tags=["Disease Catalog"])
api_v1_router.include_router(cases_router, prefix="/cases", tags=["Disease Case Surveillance"])
api_v1_router.include_router(gis_router, prefix="/gis", tags=["Geographical Information System (GIS)"])
api_v1_router.include_router(monitoring_router, prefix="/monitoring", tags=["Patient Location Consent & Monitoring"])
api_v1_router.include_router(exposure_router, prefix="/exposure", tags=["Potential Spatial-Temporal Exposure Analysis"])
api_v1_router.include_router(surveillance_router, prefix="/surveillance", tags=["Public Health Surveillance"])
api_v1_router.include_router(reports_router, prefix="/reports", tags=["Surveillance Reports & Exports"])
api_v1_router.include_router(predictions_router, prefix="/predictions", tags=["AI Outbreak Risk Prediction"])
api_v1_router.include_router(users_router, prefix="/users", tags=["User Management"])
api_v1_router.include_router(locations_router, prefix="/locations", tags=["Location Telemetry Ingestion"])


@api_v1_router.get("/", summary="API v1 Catalog")
def get_v1_info():
    return {
        "api_version": "v1",
        "description": "HealthWatch Disease Surveillance REST API",
        "endpoints": [
            "/api/health",
            "/api/auth/login",
            "/api/auth/register",
            "/api/auth/me",
            "/api/v1/patients",
            "/api/v1/diseases",
            "/api/v1/cases",
            "/api/v1/gis/districts",
            "/api/v1/gis/local-bodies",
            "/api/v1/gis/wards",
            "/api/v1/gis/cases",
            "/api/v1/monitoring/status",
            "/api/v1/monitoring/consent/grant",
            "/api/v1/monitoring/consent/revoke",
            "/api/v1/monitoring/sessions/start",
            "/api/v1/monitoring/sessions/stop",
        ],
        "modules": {
            "patients": "/api/v1/patients",
            "diseases": "/api/v1/diseases",
            "cases": "/api/v1/cases",
            "gis": "/api/v1/gis",
            "monitoring": "/api/v1/monitoring",
        },
    }
