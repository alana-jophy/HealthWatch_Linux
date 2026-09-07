import uuid
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class GeoJSONGeometry(BaseModel):
    """GeoJSON Geometry Object."""
    type: str = Field(..., description="Geometry type e.g. Point, Polygon, MultiPolygon")
    coordinates: Any = Field(..., description="Coordinate array")


class GeoJSONFeature(BaseModel):
    """GeoJSON Feature Object."""
    type: str = "Feature"
    geometry: Optional[GeoJSONGeometry] = None
    properties: Dict[str, Any] = Field(default_factory=dict)
    id: Optional[str] = None


class GeoJSONFeatureCollection(BaseModel):
    """GeoJSON FeatureCollection."""
    type: str = "FeatureCollection"
    features: List[GeoJSONFeature] = Field(default_factory=list)


class DistrictGISResponse(BaseModel):
    """District GIS record."""
    id: uuid.UUID
    code: str
    name: str
    state: str = "Kerala"
    center_latitude: Optional[float] = None
    center_longitude: Optional[float] = None
    source: str = "SIMULATED"
    geojson: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)


class LocalBodyGISResponse(BaseModel):
    """Local Body GIS record."""
    id: uuid.UUID
    district_id: uuid.UUID
    code: Optional[str] = None
    name: str
    body_type: str
    center_latitude: Optional[float] = None
    center_longitude: Optional[float] = None
    source: str = "OFFICIAL_SEC"
    geojson: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)


class WardGISResponse(BaseModel):
    """Ward GIS record."""
    id: uuid.UUID
    local_body_id: uuid.UUID
    ward_code: Optional[str] = None
    ward_number: int
    name: str
    ward_name: Optional[str] = None
    center_latitude: Optional[float] = None
    center_longitude: Optional[float] = None
    source: str = "OFFICIAL_SEC"
    geojson: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)



class CaseLocationPoint(BaseModel):
    """Point location telemetry for an individual disease case."""
    case_id: uuid.UUID
    patient_pseudo_id: str
    disease_code: str
    disease_name: str
    contagion_type: str
    case_status: str
    severity: str
    diagnosis_date: str
    latitude: float
    longitude: float
    district_name: Optional[str] = None
    local_body_name: Optional[str] = None
    ward_number: Optional[int] = None
    source: str = "SIMULATED"


# ==============================================================================
# Disease Surveillance Heatmap & Hotspot Schemas (Step 15)
# ==============================================================================

class HotspotArea(BaseModel):
    """Aggregated geographic cluster representing a disease concentration or outbreak zone."""
    area_id: str
    area_name: str
    ward_name: Optional[str] = None
    district_name: str
    local_body_name: Optional[str] = None
    ward_number: Optional[int] = None
    latitude: float
    longitude: float
    total_cases: int
    case_count: Optional[int] = None
    confirmed_cases: int = 0
    suspected_cases: int = 0
    recovered_cases: int = 0
    dominant_disease: str
    risk_tier: str  # "HOTSPOT", "HIGH", "MODERATE", "LOW"
    risk_level: Optional[str] = None
    intensity: float  # Normalized density weight 0.0 to 1.0


class HeatmapDensityPoint(BaseModel):
    """Individual density coordinate weighting for canvas heatmap rendering."""
    latitude: float
    longitude: float
    intensity: float
    case_count: int
    risk_tier: str


class DiseaseDistributionItem(BaseModel):
    """Distribution metric for specific disease in the analyzed area."""
    disease_id: str
    disease_code: str
    disease_name: str
    case_count: int
    percentage: float


class StatusDistribution(BaseModel):
    """Clinical status distribution breakdown."""
    confirmed: int = 0
    suspected: int = 0
    recovered: int = 0
    deceased: int = 0


class DiseaseHeatmapResponse(BaseModel):
    """Complete aggregated disease surveillance heatmap payload."""
    status: str = "success"
    is_demo_data: bool = True
    is_synthetic_demo_data: bool = True
    demo_data_notice: str = "SYNTHETIC DEMO DATA: Patient coordinates aggregated to ward/area centroids for privacy preservation."
    disclaimer: str = "Demo synthetic data. Patient coordinates aggregated to ward/area centroids for privacy preservation."
    total_cases_statewide: int
    cases_in_selected_area: int
    density_points: List[List[float]] = Field(
        default_factory=list,
        description="List of [latitude, longitude, intensity] tuples for Leaflet heat layer",
    )
    hotspot_areas: List[HotspotArea] = Field(default_factory=list)
    hotspots: List[HotspotArea] = Field(default_factory=list, description="Alias for hotspot_areas")
    total_hotspots: int = 0
    disease_distribution: List[DiseaseDistributionItem] = Field(default_factory=list)
    status_distribution: StatusDistribution
    concentration_summary: Dict[str, int] = Field(
        default_factory=dict,
        description="Counts of clusters by concentration level: low, moderate, high, hotspot",
    )

