import uuid
from sqlalchemy import Column, Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from geoalchemy2 import Geometry
from app.db.base import Base


class District(Base):
    """District administrative spatial entity (State of Kerala hierarchy)."""
    __tablename__ = "districts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code = Column(String(20), unique=True, nullable=False, index=True)  # e.g., KL-TVM, KL-EKM, KL-KKD
    name = Column(String(100), nullable=False, index=True)
    state = Column(String(100), default="Kerala", nullable=False)
    
    center_latitude = Column(Float, nullable=True)
    center_longitude = Column(Float, nullable=True)

    # PostGIS MultiPolygon boundary (SRID 4326 WGS84)
    boundary = Column(Geometry(geometry_type="MULTIPOLYGON", srid=4326, spatial_index=True), nullable=True)
    
    # Provenance tracking
    source = Column(String(50), default="SIMULATED", nullable=False)

    # Relationships
    local_bodies = relationship("LocalBody", back_populates="district", cascade="all, delete-orphan", lazy="selectin")


class LocalBody(Base):
    """Local governance body (Municipal Corporation, Municipality, or Grama Panchayat)."""
    __tablename__ = "local_bodies"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    district_id = Column(UUID(as_uuid=True), ForeignKey("districts.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(150), nullable=False, index=True)
    body_type = Column(String(50), default="Corporation", nullable=False)  # Corporation, Municipality, Grama Panchayat

    center_latitude = Column(Float, nullable=True)
    center_longitude = Column(Float, nullable=True)

    # PostGIS MultiPolygon boundary (SRID 4326)
    boundary = Column(Geometry(geometry_type="MULTIPOLYGON", srid=4326, spatial_index=True), nullable=True)
    
    # Provenance tracking
    source = Column(String(50), default="SIMULATED", nullable=False)

    # Relationships
    district = relationship("District", back_populates="local_bodies", lazy="selectin")
    wards = relationship("Ward", back_populates="local_body", cascade="all, delete-orphan", lazy="selectin")


class Ward(Base):
    """Electoral / surveillance administrative ward within a local body."""
    __tablename__ = "wards"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    local_body_id = Column(UUID(as_uuid=True), ForeignKey("local_bodies.id", ondelete="CASCADE"), nullable=False, index=True)
    ward_number = Column(Integer, nullable=False, index=True)
    name = Column(String(150), nullable=False)

    center_latitude = Column(Float, nullable=True)
    center_longitude = Column(Float, nullable=True)

    # PostGIS MultiPolygon boundary (SRID 4326)
    boundary = Column(Geometry(geometry_type="MULTIPOLYGON", srid=4326, spatial_index=True), nullable=True)
    
    # Provenance tracking
    source = Column(String(50), default="SIMULATED", nullable=False)

    # Relationships
    local_body = relationship("LocalBody", back_populates="wards", lazy="selectin")
