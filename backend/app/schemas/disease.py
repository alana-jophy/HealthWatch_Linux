import uuid
from datetime import datetime
from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field


class ContagionTypeEnum(str, Enum):
    CONTAGIOUS = "CONTAGIOUS"
    NON_CONTAGIOUS = "NON_CONTAGIOUS"


class DiseaseBase(BaseModel):
    """Base schema for Disease entities."""
    code: str = Field(..., min_length=2, max_length=50, description="Unique disease code (e.g. DENGUE-01)")
    name: str = Field(..., min_length=2, max_length=150, description="Common disease name")
    contagion_type: ContagionTypeEnum = Field(default=ContagionTypeEnum.CONTAGIOUS, description="CONTAGIOUS or NON_CONTAGIOUS")
    category: str = Field(default="Vector-Borne", description="Epidemiological category")
    incubation_period_days: int = Field(default=7, ge=1, le=365, description="Average incubation period in days")
    r0_estimate: Optional[float] = Field(default=1.5, ge=0.0, description="Basic reproduction number estimate (R0)")
    description: Optional[str] = Field(None, description="Clinical summary and symptoms")
    is_active: bool = Field(default=True, description="Surveillance status flag")


class DiseaseCreate(DiseaseBase):
    """Schema for registering a new disease in the catalog."""
    pass


class DiseaseUpdate(BaseModel):
    """Schema for updating disease information."""
    name: Optional[str] = Field(None, min_length=2, max_length=150)
    contagion_type: Optional[ContagionTypeEnum] = None
    category: Optional[str] = None
    incubation_period_days: Optional[int] = Field(None, ge=1, le=365)
    r0_estimate: Optional[float] = Field(None, ge=0.0)
    description: Optional[str] = None
    is_active: Optional[bool] = None


class DiseaseResponse(DiseaseBase):
    """Output schema for Disease catalog items."""
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DiseaseListResponse(BaseModel):
    """Paginated list of diseases."""
    total: int
    items: List[DiseaseResponse]
