import datetime
import uuid
from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field
from app.schemas.disease import DiseaseResponse
from app.schemas.patient import PatientResponse


class CaseStatusEnum(str, Enum):
    SUSPECTED = "SUSPECTED"
    CONFIRMED = "CONFIRMED"
    RECOVERED = "RECOVERED"
    DECEASED = "DECEASED"


class SeverityEnum(str, Enum):
    MILD = "MILD"
    MODERATE = "MODERATE"
    SEVERE = "SEVERE"
    CRITICAL = "CRITICAL"


class DiseaseCaseBase(BaseModel):
    """Base schema for reported disease case incidents."""
    patient_id: uuid.UUID = Field(..., description="ID of the patient")
    disease_id: uuid.UUID = Field(..., description="ID of the disease")
    case_status: CaseStatusEnum = Field(default=CaseStatusEnum.SUSPECTED, description="SUSPECTED, CONFIRMED, RECOVERED, DECEASED")
    severity: SeverityEnum = Field(default=SeverityEnum.MODERATE, description="Clinical severity level")
    diagnosis_date: datetime.date = Field(default_factory=datetime.date.today, description="Date of diagnosis")
    recovery_date: Optional[datetime.date] = Field(None, description="Date of recovery if applicable")
    clinical_notes: Optional[str] = Field(None, description="Observations, lab test IDs, treatment notes")


class DiseaseCaseCreate(DiseaseCaseBase):
    """Schema for registering a new disease case."""
    pass


class DiseaseCaseUpdate(BaseModel):
    """Schema for updating disease case status and clinical notes."""
    case_status: Optional[CaseStatusEnum] = None
    severity: Optional[SeverityEnum] = None
    diagnosis_date: Optional[datetime.date] = None
    recovery_date: Optional[datetime.date] = None
    clinical_notes: Optional[str] = None


class DiseaseCaseResponse(DiseaseCaseBase):
    """Output schema for disease case records."""
    id: uuid.UUID
    reported_by_id: Optional[uuid.UUID] = None
    created_at: datetime.datetime
    updated_at: datetime.datetime
    
    # Nested entity summaries for display
    patient: Optional[PatientResponse] = None
    disease: Optional[DiseaseResponse] = None

    model_config = ConfigDict(from_attributes=True)


class DiseaseCaseListResponse(BaseModel):
    """Paginated list of disease cases."""
    total: int
    items: List[DiseaseCaseResponse]
