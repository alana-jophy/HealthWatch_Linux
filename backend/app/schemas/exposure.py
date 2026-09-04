import datetime
import enum
import uuid
from typing import Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class ExposureStatusEnum(str, enum.Enum):
    """Lifecycle statuses for a potential spatial-temporal exposure observation."""
    POTENTIAL = "POTENTIAL"
    REVIEWED = "REVIEWED"
    DISMISSED = "DISMISSED"
    CONFIRMED_BY_AUTHORITY = "CONFIRMED_BY_AUTHORITY"


class ExposureAnalysisRequest(BaseModel):
    """Configurable parameters for spatial-temporal overlap detection."""
    spatial_distance_threshold_meters: float = Field(
        default=50.0,
        ge=1.0,
        le=5000.0,
        description="Configurable spatial distance threshold (meters)",
    )
    temporal_difference_threshold_minutes: float = Field(
        default=15.0,
        ge=0.5,
        le=2880.0,
        description="Configurable temporal difference threshold (minutes)",
    )
    start_date: Optional[datetime.date] = Field(None, description="Filter observations on or after date")
    end_date: Optional[datetime.date] = Field(None, description="Filter observations on or before date")
    district_id: Optional[uuid.UUID] = Field(None, description="Filter to specific district")


class ExposureEventResponse(BaseModel):
    """Detailed potential spatial-temporal exposure event for officer decision-support."""
    id: uuid.UUID
    exposure_id: uuid.UUID
    patient_a_id: Optional[uuid.UUID] = None
    patient_b_id: Optional[uuid.UUID] = None
    patient_a_pseudo_id: str
    patient_b_pseudo_id: str
    patient_a_disease: Optional[str] = None
    patient_b_disease: Optional[str] = None
    observation_a_time: Optional[datetime.datetime] = None
    observation_b_time: Optional[datetime.datetime] = None
    latitude: float
    longitude: float
    approximate_location: str
    distance: float = Field(description="Distance in meters between recorded points")
    time_difference: float = Field(description="Absolute time difference in minutes")
    confidence_score: float = Field(description="Normalized heuristic score 0.0 to 1.0")
    status: ExposureStatusEnum
    review_notes: Optional[str] = None
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime.datetime] = None
    detected_at: datetime.datetime
    disclaimer: str = (
        "Potential Exposure / Spatial-Temporal Overlap Analysis. "
        "This is a decision-support heuristic and does NOT establish clinical disease transmission between individuals."
    )

    model_config = ConfigDict(from_attributes=True)


class ExposureEventUpdateRequest(BaseModel):
    """Officer action payload to update exposure event status and clinical notes."""
    status: ExposureStatusEnum
    review_notes: Optional[str] = Field(None, max_length=1000)


class ExposureAnalysisSummaryResponse(BaseModel):
    """Result of executing the spatial-temporal overlap detection algorithm."""
    status: str = "success"
    spatial_threshold_meters: float
    temporal_threshold_minutes: float
    candidate_pairs_evaluated: int
    potential_overlaps_detected: int
    newly_created_events: int
    existing_events_retained: int
    disclaimer: str = (
        "HealthWatch potential exposure analysis is an epidemiological decision-support feature. "
        "It evaluates proximity in space and time between recorded observations. It does NOT establish transmission."
    )
    events: List[ExposureEventResponse] = Field(default_factory=list)


class ExposureListResponse(BaseModel):
    """Paginated collection of exposure events with status metrics."""
    total: int
    items: List[ExposureEventResponse]
    summary_by_status: Dict[str, int]
    disclaimer: str = (
        "Decision-support telemetry. Identifies situations where two patients recorded observations "
        "close in space and time. Does not assert causality."
    )
