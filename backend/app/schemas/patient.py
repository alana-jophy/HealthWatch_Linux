import uuid
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field


class PatientBase(BaseModel):
    """Base patient data schema."""
    pseudo_id: str = Field(..., description="Unique synthetic patient identifier (e.g. PAT-SYNTH-101)")
    full_name: str = Field(..., min_length=2, max_length=150, description="Synthetic patient full name")
    age: int = Field(..., ge=0, le=125, description="Patient age")
    gender: str = Field(default="UNKNOWN", description="Gender (MALE, FEMALE, OTHER, UNKNOWN)")
    contact_number: Optional[str] = Field(None, description="Contact phone number")
    address: Optional[str] = Field(None, description="Residential address description")
    district_name: str = Field(default="Central District", description="District name")
    local_body_name: str = Field(default="Metropolitan Municipality", description="Municipality or local body")
    ward_number: int = Field(default=1, ge=1, description="Ward number")
    is_active: bool = Field(default=True, description="Active status")
    assigned_worker_id: Optional[uuid.UUID] = Field(None, description="Assigned Health Worker user ID")


class PatientCreate(PatientBase):
    """Schema for creating a new patient."""
    user_id: Optional[uuid.UUID] = Field(None, description="Optional linked user account ID")


class PatientUpdate(BaseModel):
    """Schema for updating an existing patient."""
    full_name: Optional[str] = Field(None, min_length=2, max_length=150)
    age: Optional[int] = Field(None, ge=0, le=125)
    gender: Optional[str] = None
    contact_number: Optional[str] = None
    address: Optional[str] = None
    district_name: Optional[str] = None
    local_body_name: Optional[str] = None
    ward_number: Optional[int] = Field(None, ge=1)
    is_active: Optional[bool] = None
    assigned_worker_id: Optional[uuid.UUID] = None


class PatientResponse(PatientBase):
    """Schema for patient response output."""
    id: uuid.UUID
    user_id: Optional[uuid.UUID] = None
    assigned_worker_id: Optional[uuid.UUID] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PatientListResponse(BaseModel):
    """Paginated list of patients."""
    total: int
    items: List[PatientResponse]
