"""Pydantic Schemas for HealthWatch Report Generation."""

import enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ReportTypeEnum(str, enum.Enum):
    """Supported epidemiological report categories."""
    COMPREHENSIVE = "comprehensive"
    DISEASE_STATISTICS = "disease_statistics"
    DISTRICT_CASES = "district_cases"
    LOCAL_BODY_CASES = "local_body_cases"
    WARD_CASES = "ward_cases"
    DATE_RANGE_CASES = "date_range_cases"
    HOTSPOT_SUMMARY = "hotspot_summary"
    POTENTIAL_EXPOSURES = "potential_exposures"
    MONITORING_SUMMARY = "monitoring_summary"


class ReportFormatEnum(str, enum.Enum):
    """Supported export serialization formats."""
    CSV = "csv"
    PDF = "pdf"
    JSON = "json"


class ReportPreviewResponse(BaseModel):
    """Structured report metadata and tabular preview for UI display."""
    report_type: str = Field(..., description="Type of report generated")
    title: str = Field(..., description="Human-readable title of report")
    generated_at: str = Field(..., description="Timestamp of compilation")
    total_records: int = Field(..., description="Number of compiled tabular rows")
    columns: List[str] = Field(..., description="Column header keys")
    rows: List[Dict[str, Any]] = Field(..., description="Tabular row dictionaries")
    applied_filters: Dict[str, Any] = Field(default_factory=dict, description="Active filter parameters")
    disclaimer: str = Field(
        default="DECISION SUPPORT ONLY: HealthWatch surveillance data compiled from authorized health records.",
        description="Epidemiological decision support disclaimer"
    )
