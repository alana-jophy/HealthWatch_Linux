"""Pydantic Schemas for Public Health Surveillance Dashboard."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class DashboardKPISummary(BaseModel):
    """Core public health surveillance key performance indicator metrics."""
    total_patients: int = Field(..., description="Total unique registered patients")
    active_cases: int = Field(..., description="Active cases (Confirmed + Suspected)")
    confirmed_cases: int = Field(..., description="Total clinically confirmed disease cases")
    suspected_cases: int = Field(..., description="Total suspected disease cases undergoing investigation")
    recovered_cases: int = Field(..., description="Total recovered patient cases")
    deceased_cases: int = Field(default=0, description="Total deceased cases")
    active_monitoring_sessions: int = Field(..., description="Active location monitoring sessions")
    potential_exposure_events: int = Field(..., description="Identified potential spatial-temporal exposure intersections")


class CaseOverTimeItem(BaseModel):
    """Daily or temporal incidence tracking item for time-series charts."""
    date: str = Field(..., description="Diagnosis date (YYYY-MM-DD)")
    total: int = Field(..., description="Total cases diagnosed on this date")
    confirmed: int = Field(default=0, description="Confirmed cases")
    suspected: int = Field(default=0, description="Suspected cases")
    recovered: int = Field(default=0, description="Recovered cases")


class CaseByDiseaseItem(BaseModel):
    """Categorical case distribution by disease."""
    disease_id: str
    disease_name: str
    disease_code: str
    category: str
    count: int
    percentage: float


class CaseByDistrictItem(BaseModel):
    """Geographic case distribution by administrative district."""
    district_id: str
    district_name: str
    count: int
    percentage: float


class CaseByLocalBodyItem(BaseModel):
    """Geographic case distribution by local governing body."""
    local_body_id: str
    local_body_name: str
    district_name: str
    count: int
    percentage: float


class CaseByWardItem(BaseModel):
    """Geographic case distribution by ward."""
    ward_id: str
    ward_name: str
    local_body_name: str
    count: int
    percentage: float


class DashboardChartData(BaseModel):
    """Consolidated chart datasets for Recharts visualizations."""
    cases_over_time: List[CaseOverTimeItem] = Field(default_factory=list)
    cases_by_disease: List[CaseByDiseaseItem] = Field(default_factory=list)
    cases_by_district: List[CaseByDistrictItem] = Field(default_factory=list)
    cases_by_local_body: List[CaseByLocalBodyItem] = Field(default_factory=list)
    cases_by_ward: List[CaseByWardItem] = Field(default_factory=list)


class DashboardMapCaseItem(BaseModel):
    """Discrete disease case spatial record for map rendering."""
    id: str
    patient_pseudo_id: str
    disease_name: str
    case_status: str
    severity: str
    latitude: float
    longitude: float
    ward_name: str
    district_name: str
    diagnosis_date: str


class DashboardDistrictMapItem(BaseModel):
    """District level aggregate item for spatial district visualization."""
    id: str
    name: str
    latitude: float
    longitude: float
    case_count: int
    active_count: int


class DashboardMapData(BaseModel):
    """Consolidated spatial datasets for Leaflet map views."""
    disease_cases: List[DashboardMapCaseItem] = Field(default_factory=list)
    heatmap_points: List[List[float]] = Field(
        default_factory=list,
        description="List of [latitude, longitude, intensity] points for heat canvas"
    )
    districts: List[DashboardDistrictMapItem] = Field(default_factory=list)


class DashboardActiveFilters(BaseModel):
    """Echoed active filter parameters."""
    disease_id: Optional[str] = None
    district_id: Optional[str] = None
    local_body_id: Optional[str] = None
    ward_id: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    case_status: Optional[str] = None


class SurveillanceDashboardResponse(BaseModel):
    """Comprehensive response for Public Health Surveillance Dashboard."""
    kpi_summary: DashboardKPISummary
    charts: DashboardChartData
    map_data: DashboardMapData
    active_filters: DashboardActiveFilters
    generated_at: str
    disclaimer: str = (
        "DECISION SUPPORT ONLY: Epidemiological surveillance metrics computed dynamically "
        "from recorded health registry data and authorized spatial observations."
    )
