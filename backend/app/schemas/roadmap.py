import datetime
import uuid
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class RoadmapObservationItem(BaseModel):
    """Individual recorded location observation in the movement roadmap."""
    id: uuid.UUID
    recorded_at: datetime.datetime
    latitude: float
    longitude: float
    accuracy: Optional[float] = None
    source: str = Field("PATIENT_GPS", description="Data source: PATIENT_GPS, HEALTH_WORKER, APPROXIMATE, SIMULATED")
    session_id: Optional[uuid.UUID] = None
    district_name: Optional[str] = None
    local_body_name: Optional[str] = None
    ward_name: Optional[str] = None
    ward_number: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class RoadmapPoint(BaseModel):
    """Geographic point coordinate."""
    latitude: float
    longitude: float


class RoadmapStatistics(BaseModel):
    """Derived statistics from the recorded observations."""
    total_observations: int
    monitoring_start: Optional[datetime.datetime] = None
    monitoring_end: Optional[datetime.datetime] = None
    first_recorded_location: Optional[RoadmapPoint] = None
    last_recorded_location: Optional[RoadmapPoint] = None
    average_accuracy: Optional[float] = None


class PatientRoadmapResponse(BaseModel):
    """
    Patient Movement Roadmap Response.
    
    CRITICAL TECHNICAL LIMITATION NOTICE:
    HealthWatch is NOT performing continuous second-by-second GPS tracking.
    The collection interval is approximately 15 minutes.
    The roadmap represents discrete recorded observations, NOT continuous travel trajectory.
    Visual lines between markers do not imply verified path of travel.
    """
    patient_id: uuid.UUID
    patient_pseudo_id: str
    patient_name: Optional[str] = None
    disease_name: Optional[str] = None
    session_id: Optional[uuid.UUID] = None
    filter_date: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    disclaimer: str = (
        "HealthWatch is NOT performing continuous second-by-second GPS tracking. "
        "Observations are recorded periodically (approximately every 15 minutes). "
        "The connecting polyline represents a sequential visual timeline between discrete recorded points, "
        "NOT an exact continuous physical travel path. Do not interpret connecting lines as confirmed transit routes."
    )
    statistics: RoadmapStatistics
    observations: List[RoadmapObservationItem]

    model_config = ConfigDict(from_attributes=True)
