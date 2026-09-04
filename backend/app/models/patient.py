import uuid
from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.base import Base


class Patient(Base):
    """Patient entity with demographic, geographic, and user-account linking."""
    __tablename__ = "patients"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # Linked user account (if the patient has logged in via patient portal)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), unique=True, nullable=True, index=True)

    # Privacy-preserving synthetic/anonymized identifier
    pseudo_id = Column(String(50), unique=True, nullable=False, index=True)
    
    # Demographic details (synthetic data for development & evaluation)
    full_name = Column(String(150), nullable=False)
    age = Column(Integer, nullable=False)
    gender = Column(String(20), default="UNKNOWN", nullable=False)  # MALE, FEMALE, OTHER, UNKNOWN
    contact_number = Column(String(30), nullable=True)
    address = Column(String(255), nullable=True)
    
    # Geographic association
    district_name = Column(String(100), default="Central District", nullable=False, index=True)
    local_body_name = Column(String(100), default="Metropolitan Municipality", nullable=False)
    ward_number = Column(Integer, default=1, nullable=False, index=True)

    district_id = Column(UUID(as_uuid=True), ForeignKey("districts.id", ondelete="SET NULL"), nullable=True)
    local_body_id = Column(UUID(as_uuid=True), ForeignKey("local_bodies.id", ondelete="SET NULL"), nullable=True)
    ward_id = Column(UUID(as_uuid=True), ForeignKey("wards.id", ondelete="SET NULL"), nullable=True)

    # Assigned Health Worker for field case management & monitoring
    assigned_worker_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

    is_active = Column(Boolean, default=True, nullable=False)

    # Relationships
    user = relationship("User", foreign_keys=[user_id], lazy="selectin")
    assigned_worker = relationship("User", foreign_keys=[assigned_worker_id], lazy="selectin")
    disease_cases = relationship("DiseaseCase", back_populates="patient", cascade="all, delete-orphan", lazy="selectin")
    monitoring_sessions = relationship("MonitoringSession", back_populates="patient", cascade="all, delete-orphan", lazy="selectin")
    location_consents = relationship("LocationConsent", back_populates="patient", cascade="all, delete-orphan", lazy="selectin")

