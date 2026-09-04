from datetime import datetime
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class DatabaseHealth(BaseModel):
    """Database status detail schema."""
    status: str = Field(..., description="Status of the PostgreSQL connection ('connected' or 'disconnected')")
    postgis_installed: bool = Field(..., description="Flag indicating if PostGIS spatial extensions are enabled")
    postgis_version: Optional[str] = Field(None, description="Installed PostGIS version string")
    postgis_full_version: Optional[str] = Field(None, description="Full PostGIS and GEOS/PROJ library version details")
    latency_ms: Optional[float] = Field(None, description="Database query round-trip latency in milliseconds")
    error: Optional[str] = Field(None, description="Error message if disconnected")


class HealthResponse(BaseModel):
    """Health check response schema."""
    status: str = Field(default="ok", description="Overall service status")
    app_name: str = Field(..., description="Application name")
    version: str = Field(..., description="Application version")
    environment: str = Field(..., description="Active runtime environment")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="UTC timestamp of response")
    database: DatabaseHealth = Field(..., description="Database connection & PostGIS telemetry")
    system_info: Dict[str, Any] = Field(default_factory=dict, description="Additional subsystem information")
