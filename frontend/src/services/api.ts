import axios from 'axios';
import { 
  SystemHealth, 
  DistrictGIS, 
  LocalBodyGIS, 
  WardGIS, 
  DiseaseGISCase,
  DiseaseItem,
  PatientMonitoringStatus,
  LocationConsentItem,
  MonitoringSessionItem,
  PatientRoadmapResponse,
  PatientProfile,
  PatientDiseaseCase,
  LocationHistoryResponse,
  DiseaseHeatmapResponse,
  HeatmapFilterParams,
  ExposureEventItem,
  ExposureListResponse,
  ExposureAnalysisParams,
  ExposureAnalysisSummaryResponse,
  ExposureStatus,
  SurveillanceDashboardResponse,
  SurveillanceFilterParams,
  ReportFilterParams,
  ReportPreviewResponse,
  OutbreakPredictionResponse,
  UserItem,
} from '../types';

/**
 * Dynamic API Base URL resolver:
 * 1. If accessed from a mobile browser or client over LAN (e.g. http://192.168.0.109:5173),
 *    automatically directs API requests to http://192.168.0.109:8000.
 * 2. Honors explicit VITE_API_BASE_URL environment variable if set.
 * 3. Defaults to http://localhost:8000 for standard local development.
 */
export const getApiBaseUrl = (): string => {
  if (import.meta.env.VITE_API_BASE_URL) {
    return import.meta.env.VITE_API_BASE_URL;
  }
  if (
    typeof window !== 'undefined' &&
    window.location.hostname &&
    window.location.hostname !== 'localhost' &&
    window.location.hostname !== '127.0.0.1'
  ) {
    return `${window.location.protocol}//${window.location.hostname}:8000`;
  }
  return 'http://localhost:8000';
};

export const API_BASE_URL = getApiBaseUrl();

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 15000,
  headers: {
    'Content-Type': 'application/json',
  },
});

/**
 * Returns current authenticated JWT bearer token from localStorage
 */
export const getAuthToken = (): string | null => {
  return localStorage.getItem('healthwatch_jwt_token');
};

export const getAuthHeader = (): string => {
  const token = getAuthToken();
  return token ? `Bearer ${token}` : '';
};

// Aliases for unified role-scoped requests using active user's session
export const getOfficerAuthHeader = async (): Promise<string> => getAuthHeader();
export const getPatientAuthHeader = async (): Promise<string> => getAuthHeader();

export const getActivePatientEmail = (): string => {
  const userJson = localStorage.getItem('healthwatch_user_profile');
  if (userJson) {
    try {
      const u = JSON.parse(userJson);
      if (u.email) return u.email;
    } catch {}
  }
  return 'patient@test.com';
};

export const setActivePatientAccount = (email: string, password?: string): void => {
  localStorage.setItem('healthwatch_active_patient_email', email);
};

apiClient.interceptors.request.use((config) => {
  const token = getAuthToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

/**
 * Fetch system telemetry and backend/database health
 */
export const fetchSystemHealth = async (): Promise<SystemHealth> => {
  try {
    const response = await apiClient.get<SystemHealth>('/api/health');
    return response.data;
  } catch (error) {
    return {
      status: 'down',
      app_name: 'HealthWatch',
      version: '1.0.0',
      environment: 'development',
      timestamp: new Date().toISOString(),
      database: {
        status: 'disconnected',
        postgis_installed: false,
        error: 'Unable to reach backend service',
      },
    };
  }
};

/**
 * Fetch Districts in Kerala hierarchy
 */
export const fetchDistricts = async (): Promise<DistrictGIS[]> => {
  const auth = await getOfficerAuthHeader();
  const res = await apiClient.get<DistrictGIS[]>('/api/v1/gis/districts', {
    headers: { Authorization: auth },
  });
  return res.data;
};

/**
 * Fetch Local Bodies (Corporation, Municipality, Panchayat)
 */
export const fetchLocalBodies = async (districtId?: string, bodyType?: string): Promise<LocalBodyGIS[]> => {
  const auth = await getOfficerAuthHeader();
  const params: Record<string, string> = {};
  if (districtId) params.district_id = districtId;
  if (bodyType) params.body_type = bodyType;
  const res = await apiClient.get<LocalBodyGIS[]>('/api/v1/gis/local-bodies', {
    headers: { Authorization: auth },
    params,
  });
  return res.data;
};

/**
 * Fetch Wards belonging to a local body with optional search filter
 */
export const fetchWards = async (localBodyId?: string, search?: string): Promise<WardGIS[]> => {
  const auth = await getOfficerAuthHeader();
  const params: Record<string, string> = {};
  if (localBodyId) params.local_body_id = localBodyId;
  if (search && search.trim()) params.q = search.trim();
  const res = await apiClient.get<WardGIS[]>('/api/v1/gis/wards', {
    headers: { Authorization: auth },
    params,
  });
  return res.data;
};


/**
 * Fetch Disease catalog
 */
export const fetchDiseases = async (): Promise<DiseaseItem[]> => {
  const auth = await getOfficerAuthHeader();
  const res = await apiClient.get<{ total: number; items: DiseaseItem[] }>('/api/v1/diseases/', {
    headers: { Authorization: auth },
  });
  return res.data.items;
};

/**
 * Fetch Disease Case point locations for GIS visualization
 */
export const fetchGISCases = async (filters: {
  disease_id?: string;
  district_id?: string;
  local_body_id?: string;
  ward_id?: string;
  case_status?: string;
  contagion_type?: string;
  start_date?: string;
  end_date?: string;
}): Promise<DiseaseGISCase[]> => {
  const auth = await getOfficerAuthHeader();
  const res = await apiClient.get<DiseaseGISCase[]>('/api/v1/gis/cases', {
    headers: { Authorization: auth },
    params: filters,
  });
  return res.data;
};

// ==============================================================================
// Step 8 & 9: Patient Location Consent & Monitoring APIs
// ==============================================================================

/**
 * Fetch full location monitoring and consent status for the logged-in patient
 */
export const fetchMonitoringStatus = async (): Promise<PatientMonitoringStatus> => {
  const auth = await getPatientAuthHeader();
  const res = await apiClient.get<PatientMonitoringStatus>('/api/v1/monitoring/status', {
    headers: { Authorization: auth },
  });
  return res.data;
};

/**
 * Explicitly grant location monitoring consent
 */
export const grantLocationConsent = async (durationDays: number = 14): Promise<LocationConsentItem> => {
  const auth = await getPatientAuthHeader();
  const res = await apiClient.post<LocationConsentItem>(
    '/api/v1/monitoring/consent/grant',
    {
      consent_version: 'v1.0',
      duration_days: durationDays,
      purpose: 'Authorized Quarantine Compliance & Outbreak Contact Surveillance (approx. every 15 mins)',
    },
    { headers: { Authorization: auth } }
  );
  return res.data;
};

/**
 * Explicitly revoke location monitoring consent
 */
export const revokeLocationConsent = async (consentId?: string): Promise<LocationConsentItem> => {
  const auth = await getPatientAuthHeader();
  const res = await apiClient.post<LocationConsentItem>(
    '/api/v1/monitoring/consent/revoke',
    { consent_id: consentId, reason: 'Patient revoked location surveillance authorization' },
    { headers: { Authorization: auth } }
  );
  return res.data;
};

/**
 * Start an authorized monitoring session under active consent
 */
export const startMonitoringSession = async (
  startTime?: string,
  endTime?: string,
  durationHours: number = 24,
  samplingIntervalMinutes?: number
): Promise<MonitoringSessionItem> => {
  const auth = await getPatientAuthHeader();
  const res = await apiClient.post<MonitoringSessionItem>(
    '/api/v1/monitoring/sessions/start',
    {
      start_time: startTime || undefined,
      end_time: endTime || undefined,
      duration_hours: durationHours,
      sampling_interval_minutes: samplingIntervalMinutes || undefined,
    },
    { headers: { Authorization: auth } }
  );
  return res.data;
};

/**
 * Stop an active location monitoring session
 */
export const stopMonitoringSession = async (sessionId?: string): Promise<MonitoringSessionItem> => {
  const auth = await getPatientAuthHeader();
  const res = await apiClient.post<MonitoringSessionItem>(
    '/api/v1/monitoring/sessions/stop',
    { session_id: sessionId },
    { headers: { Authorization: auth } }
  );
  return res.data;
};

/**
 * Submit periodic location observation from mobile client/agent
 */
export const submitLocationObservation = async (
  sessionId: string,
  latitude: number,
  longitude: number,
  accuracyMeters: number = 5.0,
  source: string = 'PATIENT_GPS'
): Promise<any> => {
  const auth = await getPatientAuthHeader();
  const res = await apiClient.post(
    '/api/v1/monitoring/locations/submit',
    {
      session_id: sessionId,
      latitude,
      longitude,
      accuracy_meters: accuracyMeters,
      is_mock_provider: source === 'SIMULATED',
      source,
    },
    { headers: { Authorization: auth } }
  );
  return res.data;
};

export interface RoadmapFilterParams {
  patientId?: string;
  pseudoId?: string;
  sessionId?: string;
  date?: string;
  startTime?: string;
  endTime?: string;
}

/**
 * Retrieve patient movement roadmap (discrete observations, timeline, stats, and disclaimer)
 */
export const fetchPatientRoadmap = async (
  params?: RoadmapFilterParams
): Promise<PatientRoadmapResponse> => {
  const auth = getAuthHeader();
  const queryParams: Record<string, string> = {};
  if (params?.patientId) queryParams.patient_id = params.patientId;
  if (params?.pseudoId) queryParams.pseudo_id = params.pseudoId;
  if (params?.sessionId) queryParams.session_id = params.sessionId;
  if (params?.date) queryParams.date = params.date;
  if (params?.startTime) queryParams.start_time = params.startTime;
  if (params?.endTime) queryParams.end_time = params.endTime;

  const res = await apiClient.get<PatientRoadmapResponse>(
    '/api/v1/monitoring/roadmap',
    {
      headers: { Authorization: auth },
      params: queryParams,
    }
  );
  return res.data;
};

// ==============================================================================
// Step 13: Patient-Facing Dashboard APIs (Strict Patient Identity & RBAC)
// ==============================================================================

/**
 * Fetch profile for the authenticated patient
 */
export const fetchMyPatientProfile = async (): Promise<PatientProfile> => {
  const auth = await getPatientAuthHeader();
  const res = await apiClient.get<PatientProfile>('/api/v1/patients/me', {
    headers: { Authorization: auth },
  });
  return res.data;
};

/**
 * Fetch disease surveillance cases linked to the authenticated patient
 */
export const fetchMyDiseaseCases = async (): Promise<{ total: number; items: PatientDiseaseCase[] }> => {
  const auth = await getPatientAuthHeader();
  const res = await apiClient.get<{ total: number; items: PatientDiseaseCase[] }>('/api/v1/cases/me', {
    headers: { Authorization: auth },
  });
  return res.data;
};

/**
 * Fetch tabular location history for the authenticated patient
 */
export const fetchMyLocationHistory = async (
  limit: number = 50,
  skip: number = 0
): Promise<LocationHistoryResponse> => {
  const auth = await getPatientAuthHeader();
  const res = await apiClient.get<LocationHistoryResponse>('/api/v1/monitoring/locations/history', {
    headers: { Authorization: auth },
    params: { limit, skip },
  });
  return res.data;
};

/**
 * Fetch patient's own movement roadmap (using patient authentication)
 */
export const fetchMyRoadmap = async (
  params?: RoadmapFilterParams
): Promise<PatientRoadmapResponse> => {
  const auth = await getPatientAuthHeader();
  const queryParams: Record<string, string> = {};
  if (params?.sessionId) queryParams.session_id = params.sessionId;
  if (params?.date) queryParams.date = params.date;
  if (params?.startTime) queryParams.start_time = params.startTime;
  if (params?.endTime) queryParams.end_time = params.endTime;

  const res = await apiClient.get<PatientRoadmapResponse>(
    '/api/v1/monitoring/roadmap',
    {
      headers: { Authorization: auth },
      params: queryParams,
    }
  );
  return res.data;
};

// ==============================================================================
// Step 15: Disease Surveillance Heatmap & Hotspots API
// ==============================================================================

/**
 * Retrieve aggregated disease surveillance heatmap, concentration levels, and hotspot areas
 */
export const fetchDiseaseHeatmaps = async (
  filters?: HeatmapFilterParams
): Promise<DiseaseHeatmapResponse> => {
  const auth = await getOfficerAuthHeader();
  const queryParams: Record<string, string> = {};
  if (filters?.disease_id) queryParams.disease_id = filters.disease_id;
  if (filters?.district_id) queryParams.district_id = filters.district_id;
  if (filters?.local_body_id) queryParams.local_body_id = filters.local_body_id;
  if (filters?.ward_id) queryParams.ward_id = filters.ward_id;
  if (filters?.case_status) queryParams.case_status = filters.case_status;
  if (filters?.start_date) queryParams.start_date = filters.start_date;
  if (filters?.end_date) queryParams.end_date = filters.end_date;

  const res = await apiClient.get<DiseaseHeatmapResponse>(
    '/api/v1/gis/heatmaps',
    {
      headers: { Authorization: auth },
      params: queryParams,
    }
  );
  return res.data;
};

// ==============================================================================
// Step 16: Potential Spatial-Temporal Exposure Analysis API
// ==============================================================================

/**
 * List identified potential exposure events with optional status and date filters
 */
export const fetchExposureEvents = async (
  status?: string,
  patientId?: string,
  startDate?: string,
  endDate?: string
): Promise<ExposureListResponse> => {
  const auth = await getOfficerAuthHeader();
  const queryParams: Record<string, string> = {};
  if (status && status !== 'ALL') queryParams.status = status;
  if (patientId) queryParams.patient_id = patientId;
  if (startDate) queryParams.start_date = startDate;
  if (endDate) queryParams.end_date = endDate;

  const res = await apiClient.get<ExposureListResponse>(
    '/api/v1/exposure/events',
    {
      headers: { Authorization: auth },
      params: queryParams,
    }
  );
  return res.data;
};

/**
 * Trigger spatial-temporal overlap detection algorithm with configurable thresholds
 */
export const triggerExposureAnalysis = async (
  params: ExposureAnalysisParams
): Promise<ExposureAnalysisSummaryResponse> => {
  const auth = await getOfficerAuthHeader();
  const res = await apiClient.post<ExposureAnalysisSummaryResponse>(
    '/api/v1/exposure/analyze',
    params,
    {
      headers: { Authorization: auth },
    }
  );
  return res.data;
};

/**
 * Update exposure event status (Review, Dismiss, Confirm) and clinical review notes
 */
export const updateExposureStatus = async (
  exposureId: string,
  status: ExposureStatus,
  reviewNotes?: string
): Promise<ExposureEventItem> => {
  const auth = await getOfficerAuthHeader();
  const res = await apiClient.patch<ExposureEventItem>(
    `/api/v1/exposure/events/${exposureId}`,
    {
      status,
      review_notes: reviewNotes || undefined,
    },
    {
      headers: { Authorization: auth },
    }
  );
  return res.data;
};

/**
 * Step 17: Fetch Public Health Surveillance Dashboard aggregations and charts
 */
export const fetchSurveillanceDashboard = async (
  filters?: SurveillanceFilterParams
): Promise<SurveillanceDashboardResponse> => {
  const auth = await getOfficerAuthHeader();
  const queryParams: Record<string, string> = {};
  if (filters?.disease_id) queryParams.disease_id = filters.disease_id;
  if (filters?.district_id) queryParams.district_id = filters.district_id;
  if (filters?.local_body_id) queryParams.local_body_id = filters.local_body_id;
  if (filters?.ward_id) queryParams.ward_id = filters.ward_id;
  if (filters?.start_date) queryParams.start_date = filters.start_date;
  if (filters?.end_date) queryParams.end_date = filters.end_date;
  if (filters?.case_status && filters.case_status !== 'ALL') queryParams.case_status = filters.case_status;

  const res = await apiClient.get<SurveillanceDashboardResponse>(
    '/api/v1/surveillance/dashboard',
    {
      headers: { Authorization: auth },
      params: queryParams,
    }
  );
  return res.data;
};

/**
 * Step 18: Fetch report preview metadata and rows
 */
export const fetchReportPreview = async (
  filters?: ReportFilterParams
): Promise<ReportPreviewResponse> => {
  const auth = await getOfficerAuthHeader();
  const queryParams: Record<string, string> = {};
  if (filters?.report_type) queryParams.report_type = filters.report_type;
  if (filters?.disease_id) queryParams.disease_id = filters.disease_id;
  if (filters?.district_id) queryParams.district_id = filters.district_id;
  if (filters?.local_body_id) queryParams.local_body_id = filters.local_body_id;
  if (filters?.ward_id) queryParams.ward_id = filters.ward_id;
  if (filters?.start_date) queryParams.start_date = filters.start_date;
  if (filters?.end_date) queryParams.end_date = filters.end_date;
  if (filters?.case_status && filters.case_status !== 'ALL') queryParams.case_status = filters.case_status;

  const res = await apiClient.get<ReportPreviewResponse>(
    '/api/v1/reports/preview',
    {
      headers: { Authorization: auth },
      params: queryParams,
    }
  );
  return res.data;
};

/**
 * Step 18: Download report export file as Blob (PDF or CSV)
 */
export const downloadReportFile = async (
  filters?: ReportFilterParams
): Promise<{ blob: Blob; filename: string }> => {
  const auth = await getOfficerAuthHeader();
  const queryParams: Record<string, string> = {};
  const format = filters?.format || 'pdf';
  queryParams.format = format;
  if (filters?.report_type) queryParams.report_type = filters.report_type;
  if (filters?.disease_id) queryParams.disease_id = filters.disease_id;
  if (filters?.district_id) queryParams.district_id = filters.district_id;
  if (filters?.local_body_id) queryParams.local_body_id = filters.local_body_id;
  if (filters?.ward_id) queryParams.ward_id = filters.ward_id;
  if (filters?.start_date) queryParams.start_date = filters.start_date;
  if (filters?.end_date) queryParams.end_date = filters.end_date;
  if (filters?.case_status && filters.case_status !== 'ALL') queryParams.case_status = filters.case_status;

  const res = await apiClient.get('/api/v1/reports/export', {
    headers: { Authorization: auth },
    params: queryParams,
    responseType: 'blob',
  });

  const disposition = res.headers['content-disposition'] || '';
  let filename = `healthwatch_report_${Date.now()}.${format}`;
  const filenameMatch = disposition.match(/filename="?([^"]+)"?/);
  if (filenameMatch && filenameMatch[1]) {
    filename = filenameMatch[1];
  }

  return { blob: res.data, filename };
};

/**
 * Step 23: Fetch patient registry records with search & filters
 */
export const fetchPatientsList = async (
  q?: string,
  districtName?: string,
  wardNumber?: number,
  districtId?: string,
  localBodyId?: string,
  wardId?: string,
  isActive?: boolean,
  diseaseId?: string,
  hasPhone?: boolean
): Promise<{ total: number; items: PatientProfile[] }> => {
  const auth = await getOfficerAuthHeader();
  const queryParams: Record<string, any> = {};
  if (q) queryParams.q = q;
  if (districtName) queryParams.district_name = districtName;
  if (wardNumber !== undefined) queryParams.ward_number = wardNumber;
  if (districtId) queryParams.district_id = districtId;
  if (localBodyId) queryParams.local_body_id = localBodyId;
  if (wardId) queryParams.ward_id = wardId;
  if (isActive !== undefined) queryParams.is_active = isActive;
  if (diseaseId) queryParams.disease_id = diseaseId;
  if (hasPhone !== undefined) queryParams.has_phone = hasPhone;

  const res = await apiClient.get<{ total: number; items: PatientProfile[] }>('/api/v1/patients/', {
    headers: { Authorization: auth },
    params: queryParams,
  });
  return res.data;
};

/**
 * Register a new patient in the surveillance directory
 */
export const createPatientRecord = async (
  payload: {
    pseudo_id: string;
    full_name: string;
    age: number;
    gender: string;
    has_phone?: boolean;
    contact_number?: string | null;
    disease_id?: string;
    disease_name?: string;
    address: string;
    district_name?: string;
    local_body_name?: string;
    ward_number?: number;
    district_id?: string;
    local_body_id?: string;
    ward_id?: string;
    ward_name?: string;
    email?: string;
    initial_password?: string;
    user_id?: string;
  }
): Promise<PatientProfile> => {
  const auth = await getOfficerAuthHeader();
  const res = await apiClient.post<PatientProfile>('/api/v1/patients/', payload, {
    headers: { Authorization: auth },
  });
  return res.data;
};

/**
 * Update an existing patient record
 */
export const updatePatientRecord = async (
  patientId: string,
  payload: Partial<{
    full_name: string;
    age: number;
    gender: string;
    has_phone: boolean;
    contact_number: string | null;
    disease_id: string | null;
    disease_name: string | null;
    address: string;
    district_name: string;
    local_body_name: string;
    ward_number: number;
    district_id: string;
    local_body_id: string;
    ward_id: string;
    ward_name: string;
    is_active: boolean;
    email: string;
    password: string;
  }>
): Promise<PatientProfile> => {
  const auth = await getOfficerAuthHeader();
  const res = await apiClient.put<PatientProfile>(`/api/v1/patients/${patientId}`, payload, {
    headers: { Authorization: auth },
  });
  return res.data;
};

/**
 * Deactivate / delete a patient record (soft deactivation)
 */
export const deletePatientRecord = async (
  patientId: string
): Promise<{ status: string; message: string }> => {
  const auth = await getOfficerAuthHeader();
  const res = await apiClient.delete<{ status: string; message: string }>(`/api/v1/patients/${patientId}`, {
    headers: { Authorization: auth },
  });
  return res.data;
};


/**
 * Step 19 & 23: Fetch AI Outbreak Risk Predictions
 */
export const fetchOutbreakPredictions = async (
  diseaseId?: string,
  districtId?: string
): Promise<OutbreakPredictionResponse> => {
  const auth = await getOfficerAuthHeader();
  const queryParams: Record<string, string> = {};
  if (diseaseId) queryParams.disease_id = diseaseId;
  if (districtId) queryParams.district_id = districtId;

  const res = await apiClient.get<OutbreakPredictionResponse>('/api/v1/predictions/outbreak-risk', {
    headers: { Authorization: auth },
    params: queryParams,
  });
  return res.data;
};

/**
 * Step 23: Fetch System User list for User Management
 */
export const fetchSystemUsers = async (): Promise<UserItem[]> => {
  const auth = await getOfficerAuthHeader();
  const res = await apiClient.get<UserItem[]>('/api/v1/users/', {
    headers: { Authorization: auth },
  });
  return res.data;
};



