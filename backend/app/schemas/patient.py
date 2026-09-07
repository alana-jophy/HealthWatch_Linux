import uuid
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field, field_validator


class PatientBase(BaseModel):
    """Base patient data schema."""
    pseudo_id: str = Field(..., description="Unique synthetic patient identifier (e.g. PAT-SYNTH-101)")
    full_name: str = Field(..., min_length=2, max_length=150, description="Synthetic patient full name")
    age: int = Field(..., ge=0, le=125, description="Patient age")
    gender: str = Field(default="UNKNOWN", description="Gender (MALE, FEMALE, OTHER, UNKNOWN)")
    has_phone: bool = Field(default=True, description="Whether the patient possesses an active mobile phone")
    contact_number: Optional[str] = Field(None, description="Contact phone number (10 numeric digits if has_phone=True)")
    disease_id: Optional[uuid.UUID] = Field(None, description="Referenced Disease ID from catalog")
    disease_name: Optional[str] = Field(None, description="Catalog disease name")
    address: Optional[str] = Field(None, description="Residential address description")
    district_name: str = Field(default="Central District", description="District name")
    local_body_name: str = Field(default="Metropolitan Municipality", description="Municipality or local body")
    ward_number: int = Field(default=1, ge=1, description="Ward number")
    is_active: bool = Field(default=True, description="Active status")
    assigned_worker_id: Optional[uuid.UUID] = Field(None, description="Assigned Health Worker user ID")
    district_id: Optional[uuid.UUID] = Field(None, description="Referenced District ID")
    local_body_id: Optional[uuid.UUID] = Field(None, description="Referenced Local Body ID")
    ward_id: Optional[uuid.UUID] = Field(None, description="Referenced Ward ID")
    ward_name: Optional[str] = Field(None, description="Ward name")
    ward_code: Optional[str] = Field(None, description="Official SEC Ward Code (e.g. M04014001)")


class PatientCreate(PatientBase):
    """Schema for creating a new patient, with optional individual user account credentials."""
    user_id: Optional[uuid.UUID] = Field(None, description="Optional linked user account ID")
    email: Optional[str] = Field(None, description="Patient account email for login")
    initial_password: Optional[str] = Field(None, min_length=6, description="Patient initial password for login")

    @field_validator("contact_number")
    @classmethod
    def validate_contact_number(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v.strip() != "":
            clean = v.strip()
            if not clean.isdigit() or len(clean) != 10:
                raise ValueError("Phone number must be exactly 10 numeric digits")
            return clean
        return None


class PatientUpdate(BaseModel):
    """Schema for updating an existing patient."""
    full_name: Optional[str] = Field(None, min_length=2, max_length=150)
    age: Optional[int] = Field(None, ge=0, le=125)
    gender: Optional[str] = None
    has_phone: Optional[bool] = None
    contact_number: Optional[str] = None
    disease_id: Optional[uuid.UUID] = None
    disease_name: Optional[str] = None
    address: Optional[str] = None
    district_name: Optional[str] = None
    local_body_name: Optional[str] = None
    ward_number: Optional[int] = Field(None, ge=1)
    district_id: Optional[uuid.UUID] = None
    local_body_id: Optional[uuid.UUID] = None
    ward_id: Optional[uuid.UUID] = None
    ward_name: Optional[str] = None
    is_active: Optional[bool] = None
    assigned_worker_id: Optional[uuid.UUID] = None
    email: Optional[str] = None
    password: Optional[str] = None


class PatientResponse(PatientBase):
    """Schema for patient response output."""
    id: uuid.UUID
    user_id: Optional[uuid.UUID] = None
    assigned_worker_id: Optional[uuid.UUID] = None
    created_at: datetime
    updated_at: datetime
    account_email: Optional[str] = None
    account_id: Optional[str] = None
    latest_latitude: Optional[float] = None
    latest_longitude: Optional[float] = None
    latest_accuracy: Optional[float] = None
    latest_recorded_at: Optional[datetime] = None
    latest_source: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class PatientListResponse(BaseModel):
    """Paginated list of patients."""
    total: int
    items: List[PatientResponse]
