"""AI-Assisted Outbreak Risk Prediction Endpoints."""

import datetime
import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session
from loguru import logger

from app.api.deps import get_db, require_admin_or_officer
from app.models.disease import Disease, DiseaseCase
from app.models.exposure import ExposureEvent
from app.models.spatial import District, LocalBody, Ward
from app.models.user import User
from app.schemas.prediction import (
    AreaOutbreakPrediction,
    OutbreakPredictionInput,
    OutbreakPredictionResponse,
    RiskLevelEnum,
)
from app.services.outbreak_predictor import OutbreakPredictorService

router = APIRouter()


@router.post(
    "/predict",
    response_model=AreaOutbreakPrediction,
    summary="Generate outbreak risk prediction from feature payload",
    description="Authorized for Public Health Officers and Administrators. Strictly for epidemiological decision support.",
)
def predict_scenario_risk(
    payload: OutbreakPredictionInput,
    area_name: str = Query("Scenario Zone", description="Identifier for test or scenario area"),
    disease_name: str = Query("Dengue Fever", description="Disease label for scenario"),
    current_user: User = Depends(require_admin_or_officer),
) -> AreaOutbreakPrediction:
    """Predict outbreak risk level, continuous score, trend, and explainability factors."""
    try:
        prediction = OutbreakPredictorService.predict_risk(
            features=payload,
            area_name=area_name,
            disease_name=disease_name,
        )
        logger.info(
            f"Outbreak risk predicted for '{area_name}' ({disease_name}): "
            f"Score={prediction.risk_score}, Level={prediction.risk_level.value} by {current_user.email}"
        )
        return prediction
    except Exception as exc:
        logger.error(f"Prediction inference error: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to compute outbreak risk prediction",
        )


@router.get(
    "/outbreak-risk",
    response_model=OutbreakPredictionResponse,
    summary="Get multi-area outbreak risk forecasts from surveillance data",
    description="Aggregates active surveillance cases, density, and exposure events across Kerala districts and wards.",
)
def get_surveillance_outbreak_risk(
    disease_id: Optional[uuid.UUID] = Query(None, description="Filter by disease catalog ID"),
    district_id: Optional[uuid.UUID] = Query(None, description="Filter by district ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_officer),
) -> OutbreakPredictionResponse:
    """Generate live AI risk predictions aggregated from database surveillance records."""
    now = datetime.datetime.now(datetime.timezone.utc)
    seven_days_ago = (now - datetime.timedelta(days=7)).date()
    thirty_days_ago = (now - datetime.timedelta(days=30)).date()

    # Query districts
    dist_query = db.query(District)
    if district_id:
        dist_query = dist_query.filter(District.id == district_id)
    districts = dist_query.all()

    # Default disease
    target_disease = None
    if disease_id:
        target_disease = db.query(Disease).filter(Disease.id == disease_id).first()
    if not target_disease:
        target_disease = db.query(Disease).first()

    disease_name = target_disease.name if target_disease else "General Surveillance"
    r0 = target_disease.r0_estimate if target_disease and target_disease.r0_estimate else 1.8
    is_contagious = (target_disease.contagion_type == "CONTAGIOUS") if target_disease else True

    predictions: List[AreaOutbreakPrediction] = []

    for dist in districts:
        # Cases in last 7 days
        recent_cases = (
            db.query(func.count(DiseaseCase.id))
            .join(DiseaseCase.ward)
            .join(Ward.local_body)
            .filter(
                LocalBody.district_id == dist.id,
                DiseaseCase.diagnosis_date >= seven_days_ago,
            )
            .scalar() or 0
        )

        # Historical cases (7 to 30 days ago)
        hist_cases = (
            db.query(func.count(DiseaseCase.id))
            .join(DiseaseCase.ward)
            .join(Ward.local_body)
            .filter(
                LocalBody.district_id == dist.id,
                DiseaseCase.diagnosis_date < seven_days_ago,
                DiseaseCase.diagnosis_date >= thirty_days_ago,
            )
            .scalar() or 0
        )

        # Exposure count
        exposures = db.query(func.count(ExposureEvent.id)).scalar() or 0

        input_feat = OutbreakPredictionInput(
            recent_case_count=int(recent_cases),
            historical_case_count=int(hist_cases),
            disease_r0_estimate=float(r0),
            is_contagious=bool(is_contagious),
            spatial_case_density=round(float(recent_cases) / 5.0, 2) if recent_cases > 0 else 0.1,
            potential_exposure_count=int(exposures),
        )

        pred = OutbreakPredictorService.predict_risk(
            features=input_feat,
            area_name=dist.name,
            disease_name=disease_name,
        )
        pred.district_name = dist.name
        predictions.append(pred)

    high_or_crit = sum(1 for p in predictions if p.risk_level in [RiskLevelEnum.HIGH, RiskLevelEnum.CRITICAL])

    return OutbreakPredictionResponse(
        predictions=predictions,
        total_areas_evaluated=len(predictions),
        high_or_critical_risk_areas=high_or_crit,
    )
