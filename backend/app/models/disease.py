import datetime
import enum
import uuid
from sqlalchemy import Boolean, Column, Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from geoalchemy2 import Geography
from app.db.base import Base


class ContagionType(str, enum.Enum):
    """Disease Contagion Classification."""
    CONTAGIOUS = "CONTAGIOUS"
    NON_CONTAGIOUS = "NON_CONTAGIOUS"


class CaseStatus(str, enum.Enum):
    """Disease Case Lifecycle Status."""
    SUSPECTED = "SUSPECTED"
    CONFIRMED = "CONFIRMED"
    RECOVERED = "RECOVERED"
    DECEASED = "DECEASED"


class Disease(Base):
    """Catalog of infectious & non-infectious diseases under active surveillance."""
    __tablename__ = "diseases"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code = Column(String(50), unique=True, nullable=False, index=True)  # e.g., DENGUE-01, COVID-19
    name = Column(String(150), nullable=False, index=True)
    contagion_type = Column(String(50), default=ContagionType.CONTAGIOUS.value, nullable=False, index=True)
    category = Column(String(100), default="Vector-Borne", nullable=False)  # Vector-Borne, Respiratory, Water-Borne
    incubation_period_days = Column(Integer, default=7, nullable=False)
    r0_estimate = Column(Float, default=1.5, nullable=True)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    # Relationships
    cases = relationship("DiseaseCase", back_populates="disease", cascade="all, delete-orphan", lazy="selectin")


class DiseaseCase(Base):
    """Reported disease case incident under surveillance with PostGIS point geography."""
    __tablename__ = "disease_cases"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patient_id = Column(UUID(as_uuid=True), ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True)
    disease_id = Column(UUID(as_uuid=True), ForeignKey("diseases.id", ondelete="CASCADE"), nullable=False, index=True)
    reported_by_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    ward_id = Column(UUID(as_uuid=True), ForeignKey("wards.id", ondelete="SET NULL"), nullable=True, index=True)

    case_status = Column(String(50), default=CaseStatus.SUSPECTED.value, nullable=False, index=True)
    severity = Column(String(50), default="MODERATE", nullable=False)  # MILD, MODERATE, SEVERE, CRITICAL
    diagnosis_date = Column(Date, default=datetime.date.today, nullable=False, index=True)
    recovery_date = Column(Date, nullable=True)
    clinical_notes = Column(Text, nullable=True)

    # PostGIS Point Geography (SRID 4326: Longitude, Latitude)
    location = Column(Geography(geometry_type="POINT", srid=4326, spatial_index=True), nullable=True)
    latitude = Column(Float, nullable=True, index=True)
    longitude = Column(Float, nullable=True, index=True)
    
    # Provenance tracking
    source = Column(String(50), default="SIMULATED", nullable=False)

    # Relationships
    patient = relationship("Patient", back_populates="disease_cases", lazy="selectin")
    disease = relationship("Disease", back_populates="cases", lazy="selectin")
    reported_by = relationship("User", foreign_keys=[reported_by_id], lazy="selectin")
    ward = relationship("Ward", foreign_keys=[ward_id], lazy="selectin")
