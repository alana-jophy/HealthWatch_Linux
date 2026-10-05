export interface DatabaseHealth {
  status: 'connected' | 'disconnected';
  postgis_installed: boolean;
  postgis_version?: string | null;
  postgis_full_version?: string | null;
  latency_ms?: number | null;
  error?: string | null;
}

export interface SystemHealth {
  status: 'ok' | 'degraded' | 'down';
  app_name: string;
  version: string;
  environment: string;
  timestamp: string;
  database: DatabaseHealth;
  system_info?: {
    debug?: boolean;
    api_version?: string;
  };
}

export interface DistrictGIS {
  id: string;
  code: string;
  name: string;
  state: string;
  center_latitude: number;
  center_longitude: number;
  source: string;
  geojson?: any;
}

export interface LocalBodyGIS {
  id: string;
  district_id: string;
  code?: string;
  name: string;
  body_type: string;
  center_latitude: number;
  center_longitude: number;
  source: string;
  geojson?: any;
}

export interface WardGIS {
  id: string;
  local_body_id: string;
  ward_code?: string;
  ward_number: number;
  name: string;
  ward_name?: string;
  center_latitude: number;
  center_longitude: number;
  source: string;
  geojson?: any;
}


export interface DiseaseGISCase {
  case_id: string;
  patient_pseudo_id: string;
  disease_code: string;
  disease_name: string;
  contagion_type: 'CONTAGIOUS' | 'NON_CONTAGIOUS';
  case_status: 'SUSPECTED' | 'CONFIRMED' | 'RECOVERED' | 'DECEASED';
  severity: 'MILD' | 'MODERATE' | 'SEVERE' | 'CRITICAL';
  diagnosis_date: string;
  latitude: number;
  longitude: number;
  district_name?: string;
  local_body_name?: string;
  ward_number?: number;
  source: string;
}

export interface DiseaseItem {
  id: string;
  code: string;
  name: string;
  contagion_type: 'CONTAGIOUS' | 'NON_CONTAGIOUS';
  category: string;
  incubation_period_days: number;
  r0_estimate?: number;
  description?: string;
  is_active?: boolean;
}

export interface LocationConsentItem {
  id: string;
  patient_id: string;
  consent_status: 'ACTIVE' | 'REVOKED' | 'EXPIRED';
  consent_given_at: string;
  consent_version: string;
  monitoring_start: string;
  monitoring_end: string;
  revoked_at?: string | null;
  purpose: string;
}

export interface MonitoringSessionItem {
  id: string;
  patient_id: string;
  consent_id?: string | null;
  start_time: string;
  end_time: string;
  status: 'ACTIVE' | 'STOPPED' | 'EXPIRED';
  stopped_at?: string | null;
}

export interface PatientMonitoringStatus {
  patient_id: string;
  patient_pseudo_id: string;
  has_active_consent: boolean;
  active_consent?: LocationConsentItem | null;
  latest_consent?: LocationConsentItem | null;
  has_active_session: boolean;
  active_session?: MonitoringSessionItem | null;
  latest_session?: MonitoringSessionItem | null;
  can_collect_location: boolean;
  explanation_notice: string;
  sampling_interval_seconds?: number;
  sampling_interval_minutes?: number;
  sampling_interval_description?: string;
}

export interface RoadmapObservationItem {
  id: string;
  observation_number?: number;
  recorded_at: string;
  latitude: number;
  longitude: number;
  accuracy?: number | null;
  source: 'PATIENT_GPS' | 'HEALTH_WORKER' | 'APPROXIMATE' | 'SIMULATED' | 'STATIC_ADMIN_LOCATION' | string;
  session_id?: string | null;
  district_name?: string | null;
  local_body_name?: string | null;
  ward_name?: string | null;
  ward_number?: number | null;
  movement_status?: 'INITIAL' | 'STATIONARY_DRIFT' | 'CONFIRMED_MOVEMENT' | string;
  is_stationary_drift?: boolean;
  displacement_from_prev_meters?: number | null;
  anchor_latitude?: number | null;
  anchor_longitude?: number | null;
}

export interface RoadmapPoint {
  latitude: number;
  longitude: number;
}

export interface RoadmapStatistics {
  total_observations: number;
  stationary_count?: number;
  confirmed_movement_count?: number;
  monitoring_start?: string | null;
  monitoring_end?: string | null;
  first_recorded_location?: RoadmapPoint | null;
  last_recorded_location?: RoadmapPoint | null;
  average_accuracy?: number | null;
}

export interface PatientRoadmapResponse {
  patient_id: string;
  patient_pseudo_id: string;
  patient_name?: string | null;
  disease_name?: string | null;
  has_phone?: boolean;
  is_static_admin_location?: boolean;
  district_name?: string | null;
  local_body_name?: string | null;
  ward_name?: string | null;
  ward_number?: number | null;
  admin_geojson?: any | null;
  ward_geojson?: any | null;
  tracking_interval_minutes?: number;
  tracking_days?: string | null;
  session_id?: string | null;
  filter_date?: string | null;
  start_time?: string | null;
  end_time?: string | null;
  disclaimer_title?: string;
  disclaimer: string;
  statistics: RoadmapStatistics;
  observations: RoadmapObservationItem[];
}

export interface AlertIncident {
  id: string;
  disease: string;
  location: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  timestamp: string;
  status: 'active' | 'investigating' | 'resolved';
}

export interface PatientProfile {
  id: string;
  pseudo_id: string;
  full_name: string;
  age: number;
  gender: string;
  contact_number?: string | null;
  has_phone?: boolean;
  date_of_birth?: string | null;
  tracking_interval_minutes?: number;
  tracking_days?: string;
  disease_id?: string | null;
  disease_name?: string | null;
  address: string;
  district_name: string;
  local_body_name: string;
  ward_number: number;
  is_active: boolean;
  assigned_worker_id?: string | null;
  assigned_worker_name?: string | null;
  created_at?: string;
  district_id?: string | null;
  local_body_id?: string | null;
  ward_id?: string | null;
  ward_name?: string | null;
  ward_code?: string | null;
  account_email?: string | null;
  account_id?: string | null;
  user_id?: string | null;
  latest_latitude?: number | null;
  latest_longitude?: number | null;
  latest_accuracy?: number | null;
  latest_recorded_at?: string | null;
  latest_source?: string | null;
}

export interface PatientDiseaseCase {
  id: string;
  patient_id: string;
  disease_id: string;
  case_status: 'SUSPECTED' | 'CONFIRMED' | 'RECOVERED' | 'DECEASED';
  severity: 'MILD' | 'MODERATE' | 'SEVERE' | 'CRITICAL';
  diagnosis_date: string;
  recovery_date?: string | null;
  clinical_notes?: string | null;
  disease?: DiseaseItem;
  created_at?: string;
}

export interface PatientLocationHistoryItem {
  id: string;
  recorded_at: string;
  latitude: number;
  longitude: number;
  accuracy?: number | null;
  source: string;
  session_id?: string | null;
}

export interface LocationHistoryResponse {
  total: number;
  items: PatientLocationHistoryItem[];
  patient_id: string;
  patient_pseudo_id: string;
}

export interface HotspotAreaItem {
  area_id: string;
  area_name: string;
  district_name: string;
  local_body_name?: string | null;
  ward_number?: number | null;
  latitude: number;
  longitude: number;
  total_cases: number;
  confirmed_cases: number;
  suspected_cases: number;
  recovered_cases: number;
  dominant_disease: string;
  risk_tier: 'HOTSPOT' | 'HIGH' | 'MODERATE' | 'LOW';
  intensity: number;
}

export interface DiseaseDistributionItem {
  disease_id: string;
  disease_code: string;
  disease_name: string;
  case_count: number;
  percentage: number;
}

export interface StatusDistribution {
  confirmed: number;
  suspected: number;
  recovered: number;
  deceased: number;
}

export interface DiseaseHeatmapResponse {
  status: string;
  is_demo_data: boolean;
  disclaimer: string;
  total_cases_statewide: number;
  cases_in_selected_area: number;
  density_points: [number, number, number][]; // [lat, lng, intensity]
  hotspot_areas: HotspotAreaItem[];
  disease_distribution: DiseaseDistributionItem[];
  status_distribution: StatusDistribution;
  concentration_summary: {
    low: number;
    moderate: number;
    high: number;
    hotspot: number;
  };
}

export interface HeatmapFilterParams {
  disease_id?: string;
  district_id?: string;
  local_body_id?: string;
  ward_id?: string;
  case_status?: string;
  start_date?: string;
  end_date?: string;
}

export type ExposureStatus = 'POTENTIAL' | 'REVIEWED' | 'DISMISSED' | 'CONFIRMED_BY_AUTHORITY';

export interface ExposureEventItem {
  id: string;
  exposure_id: string;
  patient_a_id?: string;
  patient_b_id?: string;
  patient_a_pseudo_id: string;
  patient_b_pseudo_id: string;
  patient_a_disease?: string;
  patient_b_disease?: string;
  observation_a_time?: string;
  observation_b_time?: string;
  latitude: number;
  longitude: number;
  approximate_location: string;
  distance: number;
  time_difference: number;
  confidence_score: number;
  status: ExposureStatus;
  review_notes?: string | null;
  reviewed_by?: string | null;
  reviewed_at?: string | null;
  detected_at: string;
  disclaimer?: string;
}

export interface ExposureListResponse {
  total: number;
  items: ExposureEventItem[];
  summary_by_status: {
    POTENTIAL: number;
    REVIEWED: number;
    DISMISSED: number;
    CONFIRMED_BY_AUTHORITY: number;
  };
  disclaimer: string;
}

export interface ExposureAnalysisParams {
  spatial_distance_threshold_meters: number;
  temporal_difference_threshold_minutes: number;
  start_date?: string;
  end_date?: string;
  district_id?: string;
}

export interface ExposureAnalysisSummaryResponse {
  status: string;
  spatial_threshold_meters: number;
  temporal_threshold_minutes: number;
  candidate_pairs_evaluated: number;
  potential_overlaps_detected: number;
  newly_created_events: number;
  existing_events_retained: number;
  disclaimer: string;
  events: ExposureEventItem[];
}

export interface DashboardKPISummary {
  total_patients: number;
  active_cases: number;
  confirmed_cases: number;
  suspected_cases: number;
  recovered_cases: number;
  deceased_cases: number;
  active_monitoring_sessions: number;
  potential_exposure_events: number;
}

export interface CaseOverTimeItem {
  date: string;
  total: number;
  confirmed: number;
  suspected: number;
  recovered: number;
}

export interface CaseByDiseaseItem {
  disease_id: string;
  disease_name: string;
  disease_code: string;
  category: string;
  count: number;
  percentage: number;
}

export interface CaseByDistrictItem {
  district_id: string;
  district_name: string;
  count: number;
  percentage: number;
}

export interface CaseByLocalBodyItem {
  local_body_id: string;
  local_body_name: string;
  district_name: string;
  count: number;
  percentage: number;
}

export interface CaseByWardItem {
  ward_id: string;
  ward_name: string;
  local_body_name: string;
  count: number;
  percentage: number;
}

export interface DashboardChartData {
  cases_over_time: CaseOverTimeItem[];
  cases_by_disease: CaseByDiseaseItem[];
  cases_by_district: CaseByDistrictItem[];
  cases_by_local_body: CaseByLocalBodyItem[];
  cases_by_ward: CaseByWardItem[];
}

export interface DashboardMapCaseItem {
  id: string;
  patient_pseudo_id: string;
  disease_name: string;
  case_status: string;
  severity: string;
  latitude: number;
  longitude: number;
  ward_name: string;
  district_name: string;
  diagnosis_date: string;
}

export interface DashboardDistrictMapItem {
  id: string;
  name: string;
  latitude: number;
  longitude: number;
  case_count: number;
  active_count: number;
}

export interface DashboardMapData {
  disease_cases: DashboardMapCaseItem[];
  heatmap_points: [number, number, number][];
  districts: DashboardDistrictMapItem[];
}

export interface DashboardActiveFilters {
  disease_id?: string | null;
  district_id?: string | null;
  local_body_id?: string | null;
  ward_id?: string | null;
  start_date?: string | null;
  end_date?: string | null;
  case_status?: string | null;
}

export interface SurveillanceDashboardResponse {
  kpi_summary: DashboardKPISummary;
  charts: DashboardChartData;
  map_data: DashboardMapData;
  active_filters: DashboardActiveFilters;
  generated_at: string;
  disclaimer: string;
}

export interface SurveillanceFilterParams {
  disease_id?: string;
  district_id?: string;
  local_body_id?: string;
  ward_id?: string;
  start_date?: string;
  end_date?: string;
  case_status?: string;
}

export type ReportType =
  | 'comprehensive'
  | 'disease_statistics'
  | 'district_cases'
  | 'local_body_cases'
  | 'ward_cases'
  | 'date_range_cases'
  | 'hotspot_summary'
  | 'potential_exposures'
  | 'monitoring_summary';

export type ReportFormat = 'csv' | 'pdf' | 'json';

export interface ReportPreviewResponse {
  report_type: string;
  title: string;
  generated_at: string;
  total_records: number;
  columns: string[];
  rows: Record<string, any>[];
  applied_filters: Record<string, string>;
  disclaimer: string;
}

export interface ReportFilterParams {
  report_type?: ReportType;
  format?: ReportFormat;
  disease_id?: string;
  district_id?: string;
  local_body_id?: string;
  ward_id?: string;
  start_date?: string;
  end_date?: string;
  case_status?: string;
}

// AI Prediction Types
export interface AreaOutbreakPrediction {
  area_name: string;
  disease_name: string;
  district_name?: string | null;
  recent_cases: number;
  historical_cases: number;
  case_growth_rate: number;
  risk_score: number;
  risk_level: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  predicted_trend: 'DECLINING' | 'STABLE' | 'INCREASING' | 'SURGING';
  confidence_score: number;
  feature_contributions: Record<string, number>;
  prediction_date: string;
}

export interface OutbreakPredictionResponse {
  status: string;
  model_type: string;
  predictions: AreaOutbreakPrediction[];
  total_areas_evaluated: number;
  high_or_critical_risk_areas: number;
  disclaimer: string;
}

export interface UserItem {
  id: string;
  email: string;
  full_name: string;
  role_name: string;
  is_active: boolean;
  is_superuser: boolean;
  created_at?: string;
}
