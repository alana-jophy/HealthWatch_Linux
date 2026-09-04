import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from loguru import logger

from app.api.deps import (
    get_current_user,
    require_admin,
    require_public_health_officer,
)
from app.db.session import get_db
from app.models.disease import ContagionType, Disease
from app.models.user import User
from app.schemas.disease import (
    ContagionTypeEnum,
    DiseaseCreate,
    DiseaseListResponse,
    DiseaseResponse,
    DiseaseUpdate,
)

router = APIRouter()


@router.post(
    "/",
    response_model=DiseaseResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new disease in surveillance catalog",
    description="Public Health Officers and Admins can register contagious & non-contagious diseases.",
)
def create_disease(
    payload: DiseaseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_public_health_officer),
) -> DiseaseResponse:
    """Create a new disease catalog entry."""
    existing = db.query(Disease).filter(Disease.code == payload.code.upper()).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"A disease with code '{payload.code}' already exists",
        )

    disease = Disease(
        code=payload.code.upper(),
        name=payload.name,
        contagion_type=payload.contagion_type.value,
        category=payload.category,
        incubation_period_days=payload.incubation_period_days,
        r0_estimate=payload.r0_estimate,
        description=payload.description,
        is_active=payload.is_active,
    )
    db.add(disease)
    db.commit()
    db.refresh(disease)

    logger.info(f"Disease created: {disease.code} - {disease.name} by {current_user.email}")
    return disease


@router.get(
    "/",
    response_model=DiseaseListResponse,
    summary="List disease catalog with filtering and search",
    description="Accessible by all authenticated roles. Filter by contagion type (CONTAGIOUS / NON_CONTAGIOUS), category, or keyword.",
)
def list_diseases(
    q: Optional[str] = Query(None, description="Search term for disease code or name"),
    contagion_type: Optional[ContagionTypeEnum] = Query(None, description="Filter by CONTAGIOUS or NON_CONTAGIOUS"),
    category: Optional[str] = Query(None, description="Filter by category (e.g. Vector-Borne, Respiratory)"),
    is_active: Optional[bool] = Query(None, description="Filter by active surveillance flag"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DiseaseListResponse:
    """Retrieve disease records matching criteria."""
    query = db.query(Disease)

    if q:
        search_pattern = f"%{q}%"
        query = query.filter((Disease.code.ilike(search_pattern)) | (Disease.name.ilike(search_pattern)))
    if contagion_type:
        query = query.filter(Disease.contagion_type == contagion_type.value)
    if category:
        query = query.filter(Disease.category.ilike(f"%{category}%"))
    if is_active is not None:
        query = query.filter(Disease.is_active == is_active)

    total = query.count()
    items = query.order_by(Disease.name.asc()).offset(skip).limit(limit).all()

    return DiseaseListResponse(total=total, items=items)


@router.get(
    "/{disease_id}",
    response_model=DiseaseResponse,
    summary="Get disease details by ID",
)
def get_disease(
    disease_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DiseaseResponse:
    """Get single disease record."""
    disease = db.query(Disease).filter(Disease.id == disease_id).first()
    if not disease:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Disease not found in surveillance catalog",
        )
    return disease


@router.put(
    "/{disease_id}",
    response_model=DiseaseResponse,
    summary="Update disease details",
    description="Public Health Officers and Admins can update clinical parameters and contagion properties.",
)
def update_disease(
    disease_id: uuid.UUID,
    payload: DiseaseUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_public_health_officer),
) -> DiseaseResponse:
    """Update disease parameters."""
    disease = db.query(Disease).filter(Disease.id == disease_id).first()
    if not disease:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Disease not found in surveillance catalog",
        )

    update_data = payload.model_dump(exclude_unset=True)
    if "contagion_type" in update_data and update_data["contagion_type"] is not None:
        update_data["contagion_type"] = update_data["contagion_type"].value

    for field, value in update_data.items():
        setattr(disease, field, value)

    db.commit()
    db.refresh(disease)
    logger.info(f"Disease {disease.code} updated by {current_user.email}")
    return disease


@router.delete(
    "/{disease_id}",
    status_code=status.HTTP_200_OK,
    summary="Deactivate or delete disease catalog entry",
    description="Exclusively available to System Administrators.",
)
def delete_disease(
    disease_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Deactivate disease record."""
    disease = db.query(Disease).filter(Disease.id == disease_id).first()
    if not disease:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Disease not found in surveillance catalog",
        )

    disease.is_active = False
    db.commit()
    logger.info(f"Disease {disease.code} deactivated by {current_user.email}")
    return {"status": "success", "message": f"Disease {disease.code} deactivated"}
