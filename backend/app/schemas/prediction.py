"""Outbreak Risk Prediction Schemas."""

import datetime
import enum
import uuid
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class RiskLevelEnum(str, enum.Enum):
    """Epidemiological outbreak risk levels."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class PredictedTrendEnum(str, enum.Enum):
    """Outbreak trajectory direction."""
    DECLINING = "DECLINING"
    STABLE = "STABLE"
    INCREASING = "INCREASING"
    SURGING = "SURGING"


class OutbreakPredictionInput(BaseModel):
    """Input features for outbreak risk estimation."""
    historical_case_count: int = Field(..., ge=0, description="Cumulative cases in preceding 14-30 days")
    recent_case_count: int = Field(..., ge=0, description="Cases reported in the last 7 days")
    case_growth_rate: Optional[float] = Field(None, description="Case growth rate percentage or ratio")
    disease_r0_estimate: float = Field(default=1.5, ge=0.0, le=10.0, description="Basic reproduction number R0")
    is_contagious: bool = Field(default=True, description="Whether pathogen is contagious")
    spatial_case_density: float = Field(default=1.0, ge=0.0, description="Case density per km² or ward unit")
    potential_exposure_count: int = Field(default=0, ge=0, description="Identified spatial-temporal exposure events")


class AreaOutbreakPrediction(BaseModel):
    """Outbreak risk prediction for an administrative area or scenario."""
    area_name: str
    disease_name: str
    district_name: Optional[str] = None
    recent_cases: int
    historical_cases: int
    case_growth_rate: float
    risk_score: float = Field(..., ge=0.0, le=1.0, description="Calculated continuous risk probability")
    risk_level: RiskLevelEnum
    predicted_trend: PredictedTrendEnum
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    feature_contributions: Dict[str, float] = Field(default_factory=dict)
    prediction_date: datetime.date


class OutbreakPredictionResponse(BaseModel):
    """Complete prediction response with mandatory decision-support disclaimer."""
    status: str = "success"
    model_type: str = "RandomForestClassifier (Explainable scikit-learn)"
    predictions: List[AreaOutbreakPrediction]
    total_areas_evaluated: int
    high_or_critical_risk_areas: int
    disclaimer: str = (
        "DECISION SUPPORT ONLY: AI-assisted outbreak risk estimate based on simulated / demonstration surveillance data. "
        "This is not a medical diagnosis system and does not establish clinical transmission or confirm an outbreak."
    )
