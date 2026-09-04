import datetime
import enum
import uuid
from sqlalchemy import Column, DateTime, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from geoalchemy2 import Geometry
from app.db.base import Base


class ExposureStatus(str, enum.Enum):
    """Lifecycle statuses for a potential spatial-temporal exposure observation."""
    POTENTIAL = "POTENTIAL"
    REVIEWED = "REVIEWED"
    DISMISSED = "DISMISSED"
    CONFIRMED_BY_AUTHORITY = "CONFIRMED_BY_AUTHORITY"


class ExposureEvent(Base):
    """
    Identified spatial-temporal exposure intersection event.
    
    IMPORTANT:
    This is strictly an epidemiological decision-support feature indicating that two recorded
    patient observations were close in both SPACE and TIME.
    It does NOT assert or establish clinical disease transmission or causality.
    """
    __tablename__ = "exposure_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Primary participants in potential exposure
    patient_a_id = Column(UUID(as_uuid=True), ForeignKey("patients.id", ondelete="CASCADE"), nullable=True, index=True)
    patient_b_id = Column(UUID(as_uuid=True), ForeignKey("patients.id", ondelete="CASCADE"), nullable=True, index=True)
    
    # Specific location observations triggering overlap
    observation_a_id = Column(UUID(as_uuid=True), ForeignKey("patient_locations.id", ondelete="SET NULL"), nullable=True)
    observation_b_id = Column(UUID(as_uuid=True), ForeignKey("patient_locations.id", ondelete="SET NULL"), nullable=True)
    observation_a_time = Column(DateTime(timezone=True), nullable=True)
    observation_b_time = Column(DateTime(timezone=True), nullable=True)

    # Spatial intersection geometry and coordinates
    location = Column(Geometry(geometry_type="POINT", srid=4326, spatial_index=True), nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    
    # Quantitative proximity metrics
    distance = Column(Float, nullable=True)  # Distance in meters between the observations
    time_difference = Column(Float, nullable=True)  # Absolute time difference in minutes
    confidence_score = Column(Float, default=0.5, nullable=False)  # Normalized metric 0.0 to 1.0
    
    detected_at = Column(DateTime(timezone=True), default=datetime.datetime.utcnow, nullable=False, index=True)
    status = Column(String(50), default=ExposureStatus.POTENTIAL.value, nullable=False, index=True)
    
    # Officer Review workflow
    review_notes = Column(Text, nullable=True)
    reviewed_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)

    # Legacy / compatibility columns for earlier migrations
    source_patient_id = Column(UUID(as_uuid=True), ForeignKey("patients.id", ondelete="CASCADE"), nullable=True)
    exposed_entity_token = Column(String(100), nullable=True)
    distance_meters = Column(Float, nullable=True)
    duration_minutes = Column(Float, nullable=True)
    risk_score = Column(Float, nullable=True)

    # Relationships
    patient_a = relationship("Patient", foreign_keys=[patient_a_id], lazy="selectin")
    patient_b = relationship("Patient", foreign_keys=[patient_b_id], lazy="selectin")
    reviewed_by = relationship("User", foreign_keys=[reviewed_by_id], lazy="selectin")

    @property
    def exposure_id(self) -> uuid.UUID:
        """Alias for primary key identifier."""
        return self.id
