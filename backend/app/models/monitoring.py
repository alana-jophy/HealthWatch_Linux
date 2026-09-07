import datetime
import enum
import uuid
from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from geoalchemy2 import Geography, Geometry
from app.db.base import Base


class ConsentStatus(str, enum.Enum):
    """Status lifecycle of a Patient Location Consent agreement."""
    ACTIVE = "ACTIVE"
    REVOKED = "REVOKED"
    EXPIRED = "EXPIRED"


class SessionStatus(str, enum.Enum):
    """Status lifecycle of an authorized location monitoring session."""
    ACTIVE = "ACTIVE"
    STOPPED = "STOPPED"
    EXPIRED = "EXPIRED"


class LocationConsent(Base):
    """Explicit, privacy-preserving patient location consent record."""
    __tablename__ = "location_consents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id = Column(UUID(as_uuid=True), ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True)
    
    consent_status = Column(String(50), default=ConsentStatus.ACTIVE.value, nullable=False, index=True)
    consent_given_at = Column(DateTime(timezone=True), default=datetime.datetime.utcnow, nullable=False)
    consent_version = Column(String(20), default="v1.0", nullable=False)
    
    monitoring_start = Column(DateTime(timezone=True), nullable=False)
    monitoring_end = Column(DateTime(timezone=True), nullable=False)
    revoked_at = Column(DateTime(timezone=True), nullable=True)

    purpose = Column(
        String(255),
        default="Authorized Quarantine Compliance & Outbreak Contact Surveillance (approx. every 15 mins)",
        nullable=False,
    )

    # Relationships
    patient = relationship("Patient", back_populates="location_consents", lazy="selectin")
    sessions = relationship("MonitoringSession", back_populates="consent", cascade="all, delete-orphan", lazy="selectin")


class MonitoringSession(Base):
    """Authorized location monitoring session executing under valid consent."""
    __tablename__ = "monitoring_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id = Column(UUID(as_uuid=True), ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True)
    consent_id = Column(UUID(as_uuid=True), ForeignKey("location_consents.id", ondelete="CASCADE"), nullable=True, index=True)

    start_time = Column(DateTime(timezone=True), default=datetime.datetime.utcnow, nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=False)
    status = Column(String(50), default=SessionStatus.ACTIVE.value, nullable=False, index=True)
    stopped_at = Column(DateTime(timezone=True), nullable=True)
    sampling_interval_minutes = Column(Integer, default=15, nullable=False)

    # Relationships
    patient = relationship("Patient", back_populates="monitoring_sessions", lazy="selectin")
    consent = relationship("LocationConsent", back_populates="sessions", lazy="selectin")
    locations = relationship("PatientLocation", back_populates="session", cascade="all, delete-orphan", lazy="selectin", foreign_keys="[PatientLocation.session_id]")


class PatientLocation(Base):
    """Individual spatial-temporal location telemetry point collected with consent."""
    __tablename__ = "patient_locations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("monitoring_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    monitoring_session_id = Column(UUID(as_uuid=True), ForeignKey("monitoring_sessions.id", ondelete="CASCADE"), nullable=True, index=True)
    patient_id = Column(UUID(as_uuid=True), ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True)

    recorded_at = Column(DateTime(timezone=True), default=datetime.datetime.utcnow, nullable=False, index=True)
    
    # PostGIS Point Geometry: (Longitude, Latitude) in WGS84 EPSG:4326
    location = Column(Geometry(geometry_type="POINT", srid=4326, spatial_index=True), nullable=True)
    
    # PostGIS Geography Point: (Longitude, Latitude) in WGS84 EPSG:4326 (Preferred for accurate metric spatial ops)
    location_geography = Column(Geography(geometry_type="POINT", srid=4326), nullable=True)
    
    # Explicit numerical coordinates (WGS84 EPSG:4326)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    
    accuracy = Column(Float, nullable=True)
    accuracy_meters = Column(Float, nullable=True)
    speed_mps = Column(Float, nullable=True)
    altitude = Column(Float, nullable=True)
    is_mock_provider = Column(Boolean, default=False, nullable=False)
    source = Column(String(50), default="PATIENT_GPS", nullable=False)
    client_observation_id = Column(String(100), nullable=True, index=True)

    @property
    def location_id(self):
        return self.id

    # Relationships
    session = relationship("MonitoringSession", back_populates="locations", lazy="selectin", foreign_keys=[session_id])
