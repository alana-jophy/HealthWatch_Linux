"""HealthWatch Surveillance Report Generation Endpoints."""

import datetime
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.api.deps import require_admin_or_officer
from app.db.session import get_db
from app.models.disease import Disease
from app.models.spatial import District, LocalBody, Ward
from app.models.user import User
from app.schemas.report import ReportFormatEnum, ReportPreviewResponse, ReportTypeEnum
from app.services.report_generator import ReportGeneratorService

router = APIRouter()


def _resolve_filter_names(db: Session, raw_filters: dict) -> dict:
    """Helper to convert UUID filter parameters into human-readable labels for report headers."""
    named = {}
    if raw_filters.get("disease_id"):
        d = db.query(Disease).filter(Disease.id == raw_filters["disease_id"]).first()
        named["Disease"] = f"{d.name} ({d.code})" if d else str(raw_filters["disease_id"])
    if raw_filters.get("district_id"):
        dist = db.query(District).filter(District.id == raw_filters["district_id"]).first()
        named["District"] = dist.name if dist else str(raw_filters["district_id"])
    if raw_filters.get("local_body_id"):
        lb = db.query(LocalBody).filter(LocalBody.id == raw_filters["local_body_id"]).first()
        named["Local Body"] = lb.name if lb else str(raw_filters["local_body_id"])
    if raw_filters.get("ward_id"):
        w = db.query(Ward).filter(Ward.id == raw_filters["ward_id"]).first()
        named["Ward"] = f"Ward {w.ward_number} ({w.name})" if w else str(raw_filters["ward_id"])
    if raw_filters.get("start_date"):
        named["From Date"] = str(raw_filters["start_date"])
    if raw_filters.get("end_date"):
        named["To Date"] = str(raw_filters["end_date"])
    if raw_filters.get("case_status") and raw_filters["case_status"] != "ALL":
        named["Case Status"] = str(raw_filters["case_status"]).upper()
    return named


@router.get(
    "/preview",
    response_model=ReportPreviewResponse,
    summary="Preview epidemiological surveillance report data",
    description="Returns structured tabular preview rows and metadata before initiating file export.",
)
def preview_report(
    report_type: ReportTypeEnum = Query(ReportTypeEnum.COMPREHENSIVE, description="Epidemiological report category"),
    disease_id: Optional[uuid.UUID] = Query(None, description="Filter by disease catalog ID"),
    district_id: Optional[uuid.UUID] = Query(None, description="Filter by district ID"),
    local_body_id: Optional[uuid.UUID] = Query(None, description="Filter by local body ID"),
    ward_id: Optional[uuid.UUID] = Query(None, description="Filter by ward ID"),
    start_date: Optional[datetime.date] = Query(None, description="Filter cases on or after date"),
    end_date: Optional[datetime.date] = Query(None, description="Filter cases on or before date"),
    case_status: Optional[str] = Query(None, description="Filter by case status (CONFIRMED, SUSPECTED, RECOVERED, DECEASED)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_officer),
) -> ReportPreviewResponse:
    """Generate in-memory preview of surveillance report."""
    raw_filters = {
        "disease_id": disease_id,
        "district_id": district_id,
        "local_body_id": local_body_id,
        "ward_id": ward_id,
        "start_date": start_date,
        "end_date": end_date,
        "case_status": case_status,
    }

    title, columns, rows = ReportGeneratorService.compile_report_data(db, report_type, raw_filters)
    active_filters = _resolve_filter_names(db, raw_filters)

    return ReportPreviewResponse(
        report_type=report_type.value,
        title=title,
        generated_at=datetime.datetime.utcnow().isoformat(),
        total_records=len(rows),
        columns=columns,
        rows=rows,
        applied_filters=active_filters,
        disclaimer=(
            "DECISION SUPPORT ONLY: HealthWatch surveillance data compiled from authorized health records. "
            "Confidential & Anonymized for authorized public health personnel."
        ),
    )


@router.get(
    "/export",
    summary="Export epidemiological surveillance report as CSV or PDF",
    description="Streams an official publication-grade PDF document or RFC 4180 CSV export file.",
)
def export_report(
    format: ReportFormatEnum = Query(ReportFormatEnum.PDF, description="Export serialization format (csv or pdf)"),
    report_type: ReportTypeEnum = Query(ReportTypeEnum.COMPREHENSIVE, description="Epidemiological report category"),
    disease_id: Optional[uuid.UUID] = Query(None, description="Filter by disease catalog ID"),
    district_id: Optional[uuid.UUID] = Query(None, description="Filter by district ID"),
    local_body_id: Optional[uuid.UUID] = Query(None, description="Filter by local body ID"),
    ward_id: Optional[uuid.UUID] = Query(None, description="Filter by ward ID"),
    start_date: Optional[datetime.date] = Query(None, description="Filter cases on or after date"),
    end_date: Optional[datetime.date] = Query(None, description="Filter cases on or before date"),
    case_status: Optional[str] = Query(None, description="Filter by case status (CONFIRMED, SUSPECTED, RECOVERED, DECEASED)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin_or_officer),
):
    """Generate and stream CSV or PDF report files."""
    raw_filters = {
        "disease_id": disease_id,
        "district_id": district_id,
        "local_body_id": local_body_id,
        "ward_id": ward_id,
        "start_date": start_date,
        "end_date": end_date,
        "case_status": case_status,
    }

    title, columns, rows = ReportGeneratorService.compile_report_data(db, report_type, raw_filters)
    active_filters = _resolve_filter_names(db, raw_filters)
    timestamp_slug = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")

    if format == ReportFormatEnum.CSV:
        csv_content = ReportGeneratorService.render_csv(title, columns, rows, active_filters)
        filename = f"healthwatch_{report_type.value}_{timestamp_slug}.csv"
        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "X-Report-Type": report_type.value,
                "X-Record-Count": str(len(rows)),
            },
        )
    elif format == ReportFormatEnum.PDF:
        pdf_bytes = ReportGeneratorService.render_pdf(title, columns, rows, active_filters)
        filename = f"healthwatch_{report_type.value}_{timestamp_slug}.pdf"
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "X-Report-Type": report_type.value,
                "X-Record-Count": str(len(rows)),
            },
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported export format '{format}'. Supported formats: 'csv', 'pdf'.",
        )
