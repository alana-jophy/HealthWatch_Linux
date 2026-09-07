import datetime
import uuid
from enum import Enum
from typing import Any, Dict, Optional, List
from pydantic import BaseModel, ConfigDict, Field


class ConsentStatusEnum(str, Enum):
    ACTIVE = "ACTIVE"
    REVOKED = "REVOKED"
    EXPIRED = "EXPIRED"


class SessionStatusEnum(str, Enum):
    ACTIVE = "ACTIVE"
    STOPPED = "STOPPED"
    EXPIRED = "EXPIRED"


class ConsentGrantRequest(BaseModel):
    """Payload to explicitly grant location telemetry consent."""
    patient_id: Optional[uuid.UUID] = Field(None, description="Patient ID (auto-inferred for authenticated patient)")
    consent_version: str = Field(default="v1.0", description="Terms version accepted by patient")
    duration_days: int = Field(default=14, ge=1, le=90, description="Duration of authorized surveillance window in days")
    monitoring_start: Optional[datetime.datetime] = Field(None, description="Explicit start date/time")
    monitoring_end: Optional[datetime.datetime] = Field(None, description="Explicit end date/time")
    purpose: str = Field(
        default="Authorized Quarantine Compliance & Outbreak Contact Surveillance (approx. every 15 mins)",
        description="Explicit explanation of data usage",
    )


class ConsentRevokeRequest(BaseModel):
    """Payload to explicitly revoke active consent."""
    consent_id: Optional[uuid.UUID] = Field(None, description="Consent ID to revoke (or revokes all active if omitted)")
    reason: Optional[str] = Field(default="Patient opted out of active monitoring", description="Reason for revocation")


class ConsentResponse(BaseModel):
    """Response schema for location consent records."""
    id: uuid.UUID
    patient_id: uuid.UUID
    consent_status: ConsentStatusEnum
    consent_given_at: datetime.datetime
    consent_version: str
    monitoring_start: datetime.datetime
    monitoring_end: datetime.datetime
    revoked_at: Optional[datetime.datetime] = None
    purpose: str
    created_at: datetime.datetime
    updated_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)


class SessionStartRequest(BaseModel):
    """Payload to start an authorized monitoring session under active consent."""
    consent_id: Optional[uuid.UUID] = Field(None, description="Active consent ID (auto-inferred if omitted)")
    start_time: Optional[datetime.datetime] = Field(None, description="Session start date/time")
    end_time: Optional[datetime.datetime] = Field(None, description="Session end date/time")
    duration_hours: int = Field(default=24, ge=1, le=336, description="Monitoring session duration in hours")
    sampling_interval_minutes: Optional[int] = Field(default=15, description="Officer/system selected sampling cadence in minutes (1, 5, 10, 15, 30, 60)")


class SessionStopRequest(BaseModel):
    """Payload to stop a running monitoring session."""
    session_id: Optional[uuid.UUID] = Field(None, description="Session ID to terminate")


class SessionResponse(BaseModel):
    """Response schema for monitoring session records."""
    id: uuid.UUID
    patient_id: uuid.UUID
    consent_id: Optional[uuid.UUID] = None
    start_time: datetime.datetime
    end_time: datetime.datetime
    status: SessionStatusEnum
    stopped_at: Optional[datetime.datetime] = None
    sampling_interval_minutes: int = 15
    sampling_interval_seconds: int = 900
    sampling_interval_description: str = "Approximately 15 minutes"
    created_at: datetime.datetime
    updated_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)


class LocationObservationSubmit(BaseModel):
    """Payload for submitting a periodic location observation from mobile client/agent."""
    session_id: Optional[uuid.UUID] = Field(None, description="Active monitoring session ID")
    monitoring_session_id: Optional[uuid.UUID] = Field(None, description="Alias for monitoring session ID")
    patient_id: Optional[uuid.UUID] = Field(None, description="Patient ID (optional, verified against session)")
    latitude: float = Field(..., ge=-90.0, le=90.0, description="Latitude coordinate (e.g., 8.5241)")
    longitude: float = Field(..., ge=-180.0, le=180.0, description="Longitude coordinate (e.g., 76.9366)")
    recorded_at: Optional[datetime.datetime] = Field(None, description="Observation timestamp (UTC)")
    accuracy_meters: Optional[float] = Field(None, ge=0.0, description="GPS horizontal accuracy radius in meters")
    accuracy: Optional[float] = Field(None, ge=0.0, description="Alias for GPS accuracy in meters")
    speed_mps: Optional[float] = Field(None, ge=0.0, description="Speed in meters per second")
    altitude: Optional[float] = Field(None, description="Altitude in meters above sea level")
    is_mock_provider: bool = Field(default=False, description="Flag indicating simulated GPS or mock location provider")
    source: str = Field(default="PATIENT_GPS", description="Data source origin tag, e.g., PATIENT_GPS")

    @property
    def effective_session_id(self) -> uuid.UUID:
        sid = self.session_id or self.monitoring_session_id
        if not sid:
            raise ValueError("session_id or monitoring_session_id must be provided")
        return sid

    @property
    def effective_accuracy(self) -> Optional[float]:
        return self.accuracy_meters if self.accuracy_meters is not None else self.accuracy


class LocationObservationResponse(BaseModel):
    """Response returned upon successfully verifying and accepting a location observation."""
    id: uuid.UUID
    session_id: uuid.UUID
    patient_id: uuid.UUID
    recorded_at: datetime.datetime
    latitude: float
    longitude: float
    accuracy_meters: Optional[float] = None
    source: str = "PATIENT_GPS"
    status: str = "ACCEPTED"
    message: str = "Location observation verified under active consent and recorded successfully."

    model_config = ConfigDict(from_attributes=True)


class LocationObservationCreate(BaseModel):
    """Payload for POST /api/locations endpoint."""
    monitoring_session_id: uuid.UUID = Field(..., description="Active monitoring session ID")
    latitude: float = Field(..., ge=-90.0, le=90.0, description="Latitude in degrees (-90 to +90)")
    longitude: float = Field(..., ge=-180.0, le=180.0, description="Longitude in degrees (-180 to +180)")
    accuracy: Optional[float] = Field(None, ge=0.0, le=5000.0, description="Accuracy in meters (reasonable range)")
    recorded_at: datetime.datetime = Field(..., description="Actual device GPS recorded timestamp")
    source: Optional[str] = Field(default="PATIENT_GPS", description="Source tag, strictly PATIENT_GPS")
    client_observation_id: Optional[str] = Field(None, description="Optional idempotency/observation identifier to avoid duplication")


class LocationObservationDetailResponse(BaseModel):
    """Comprehensive location observation response including location_id and status."""
    location_id: uuid.UUID
    patient_id: uuid.UUID
    monitoring_session_id: uuid.UUID
    latitude: float
    longitude: float
    accuracy: Optional[float] = None
    recorded_at: datetime.datetime
    source: str = "PATIENT_GPS"
    created_at: datetime.datetime
    status: str = "ACCEPTED"
    message: str = "Location observation verified and recorded successfully."
    is_duplicate: bool = False

    model_config = ConfigDict(from_attributes=True)


class PatientMonitoringStatusResponse(BaseModel):
    """Comprehensive monitoring and consent status for a patient."""
    patient_id: uuid.UUID
    patient_pseudo_id: str
    has_active_consent: bool
    active_consent: Optional[ConsentResponse] = None
    latest_consent: Optional[ConsentResponse] = None
    has_active_session: bool
    active_session: Optional[SessionResponse] = None
    latest_session: Optional[SessionResponse] = None
    can_collect_location: bool
    sampling_interval_minutes: int = 15
    sampling_interval_seconds: int = 900
    sampling_interval_description: str = "Approximately 15 minutes"
    explanation_notice: str


class AuditLogResponse(BaseModel):
    """System audit record for compliance and security traceability."""
    id: uuid.UUID
    user_id: Optional[uuid.UUID] = None
    action: str
    entity_name: Optional[str] = None
    entity_id: Optional[str] = None
    ip_address: Optional[str] = None
    metadata_json: Optional[Dict[str, Any]] = None
    recorded_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True)


class LocationHistoryItem(BaseModel):
    """Schema for tabular display of patient location observation history."""
    id: uuid.UUID
    recorded_at: datetime.datetime = Field(..., description="Timestamp of observation")
    latitude: float
    longitude: float
    accuracy: Optional[float] = Field(None, description="GPS accuracy in meters")
    source: str = Field(default="PATIENT_GPS", description="Source of telemetry")
    session_id: Optional[uuid.UUID] = None

    model_config = ConfigDict(from_attributes=True)


class LocationHistoryListResponse(BaseModel):
    """Paginated collection of patient location observation records."""
    total: int
    items: List[LocationHistoryItem]
    patient_id: uuid.UUID
    patient_pseudo_id: str

