import datetime
import uuid
from sqlalchemy import Column, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from app.db.base import Base


class AuditLog(Base):
    """System audit log for compliance, data access tracking, and security inspection."""
    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    action = Column(String(100), nullable=False, index=True)  # e.g., AUTH_LOGIN, PATIENT_VIEW, CONSENT_UPDATE
    entity_name = Column(String(100), nullable=True)
    entity_id = Column(String(100), nullable=True)
    ip_address = Column(String(50), nullable=True)
    
    # Structured JSON metadata (PostgreSQL JSONB)
    metadata_json = Column(JSONB, nullable=True)
    
    recorded_at = Column(DateTime(timezone=True), default=datetime.datetime.utcnow, nullable=False, index=True)
