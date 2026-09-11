import datetime
import uuid
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class RoadmapObservationItem(BaseModel):
    """Individual recorded location observation in the movement roadmap."""
    id: uuid.UUID
    observation_number: int = Field(1, description="Sequential 1-based observation index")
    recorded_at: datetime.datetime
    latitude: float
    longitude: float
    accuracy: Optional[float] = None
    source: str = Field("PATIENT_GPS", description="Data source: PATIENT_GPS, STATIC_ADMIN_LOCATION, SIMULATED")
    session_id: Optional[uuid.UUID] = None
    district_name: Optional[str] = None
    local_body_name: Optional[str] = None
    ward_name: Optional[str] = None
    ward_number: Optional[int] = None

    # Movement interpretation (preserving raw GPS observations for audit/history)
    movement_status: str = Field("INITIAL", description="INITIAL, STATIONARY_DRIFT, CONFIRMED_MOVEMENT")
    is_stationary_drift: bool = Field(False, description="True if displacement is within GPS uncertainty/noise margin")
    displacement_from_prev_meters: Optional[float] = Field(None, description="Geodesic distance from previous observation in meters")
    anchor_latitude: Optional[float] = Field(None, description="Anchor latitude for stationary cluster")
    anchor_longitude: Optional[float] = Field(None, description="Anchor longitude for stationary cluster")

    model_config = ConfigDict(from_attributes=True)


class RoadmapPoint(BaseModel):
    """Geographic point coordinate."""
    latitude: float
    longitude: float


class RoadmapStatistics(BaseModel):
    """Derived statistics from the recorded observations."""
    total_observations: int
    stationary_count: int = 0
    confirmed_movement_count: int = 0
    monitoring_start: Optional[datetime.datetime] = None
    monitoring_end: Optional[datetime.datetime] = None
    first_recorded_location: Optional[RoadmapPoint] = None
    last_recorded_location: Optional[RoadmapPoint] = None
    average_accuracy: Optional[float] = None


class PatientRoadmapResponse(BaseModel):
    """
    Patient Movement Roadmap Response.
    
    CRITICAL TECHNICAL LIMITATION NOTICE:
    Recorded GPS observations.
    The connecting line represents the connection between recorded observations and does not represent continuous GPS tracking.
    """
    patient_id: uuid.UUID
    patient_pseudo_id: str
    patient_name: Optional[str] = None
    disease_name: Optional[str] = None
    has_phone: bool = True
    is_static_admin_location: bool = False
    tracking_interval_minutes: int = 15
    tracking_days: Optional[str] = None
    session_id: Optional[uuid.UUID] = None
    filter_date: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    disclaimer_title: str = "Recorded GPS observations"
    disclaimer: str = (
        "The connecting line represents the connection between recorded observations and does not represent continuous GPS tracking. "
        "Observations within GPS accuracy margins represent stationary location / GPS drift."
    )
    statistics: RoadmapStatistics
    observations: List[RoadmapObservationItem]

    model_config = ConfigDict(from_attributes=True)
