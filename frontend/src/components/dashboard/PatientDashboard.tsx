import React, { useState, useEffect } from 'react';
import {
  fetchMyPatientProfile,
  fetchMyDiseaseCases,
  fetchMonitoringStatus,
  fetchMyLocationHistory,
  fetchMyRoadmap,
} from '../../services/api';
import {
  PatientProfile,
  PatientDiseaseCase,
  PatientMonitoringStatus,
  PatientLocationHistoryItem,
  PatientRoadmapResponse,
} from '../../types';
import {
  User,
  Activity,
  ShieldCheck,
  MapPin,
  Clock,
  Route,
  Radio,
  Calendar,
  Phone,
  Home,
  CheckCircle2,
  AlertTriangle,
  RefreshCw,
  FileSpreadsheet,
  Info,
  ChevronRight,
  Crosshair,
  ExternalLink,
} from 'lucide-react';

interface PatientDashboardProps {
  onNavigateToRoadmap?: () => void;
}

export const PatientDashboard: React.FC<PatientDashboardProps> = ({
  onNavigateToRoadmap,
}) => {
  const [profile, setProfile] = useState<PatientProfile | null>(null);
  const [cases, setCases] = useState<PatientDiseaseCase[]>([]);
  const [monitoringStatus, setMonitoringStatus] = useState<PatientMonitoringStatus | null>(null);
  const [locationHistory, setLocationHistory] = useState<PatientLocationHistoryItem[]>([]);
  const [historyTotal, setHistoryTotal] = useState<number>(0);
  const [roadmap, setRoadmap] = useState<PatientRoadmapResponse | null>(null);

  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [historyPage, setHistoryPage] = useState<number>(0);
  const PAGE_SIZE = 10;

  const loadPatientData = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [profileData, casesData, statusData, historyData, roadmapData] = await Promise.all([
        fetchMyPatientProfile(),
        fetchMyDiseaseCases(),
        fetchMonitoringStatus(),
        fetchMyLocationHistory(50, 0),
        fetchMyRoadmap({ date: '2026-09-05' }),
      ]);

      setProfile(profileData);
      setCases(casesData.items || []);
      setMonitoringStatus(statusData);
      setLocationHistory(historyData.items || []);
      setHistoryTotal(historyData.total || 0);
      setRoadmap(roadmapData);
    } catch (err: any) {
      console.error('Error loading patient dashboard data:', err);
      setError(
        err.response?.data?.detail ||
        'Unable to load patient records. Ensure backend service is running and authentication is valid.'
      );
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadPatientData();
  }, []);

  // Determine current monitoring status label
  const getMonitoringBadge = () => {
    if (!monitoringStatus?.has_active_consent) {
      return {
        label: 'EXPIRED',
        color: 'bg-slate-800 text-slate-400 border-slate-700',
        dot: 'bg-slate-500',
      };
    }
    if (monitoringStatus.has_active_session && monitoringStatus.active_session?.status === 'ACTIVE') {
      return {
        label: 'ACTIVE',
        color: 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30',
        dot: 'bg-emerald-400 animate-pulse',
      };
    }
    if (monitoringStatus.active_session?.status === 'STOPPED') {
      return {
        label: 'STOPPED',
        color: 'bg-amber-500/15 text-amber-400 border-amber-500/30',
        dot: 'bg-amber-400',
      };
    }
    return {
      label: 'EXPIRED',
      color: 'bg-rose-500/15 text-rose-400 border-rose-500/30',
      dot: 'bg-rose-400',
    };
  };

  const statusBadge = getMonitoringBadge();

  // Active or latest session period
  const effectiveSession = monitoringStatus?.active_session || monitoringStatus?.latest_session;
  const effectiveConsent = monitoringStatus?.active_consent || monitoringStatus?.latest_consent;

  const sessionPeriod = effectiveSession
    ? {
        start: new Date(effectiveSession.start_time).toLocaleString('en-IN', {
          dateStyle: 'medium',
          timeStyle: 'short',
        }),
        end: new Date(effectiveSession.end_time).toLocaleString('en-IN', {
          dateStyle: 'medium',
          timeStyle: 'short',
        }),
      }
    : effectiveConsent
    ? {
        start: new Date(effectiveConsent.monitoring_start).toLocaleString('en-IN', {
          dateStyle: 'medium',
          timeStyle: 'short',
        }),
        end: new Date(effectiveConsent.monitoring_end).toLocaleString('en-IN', {
          dateStyle: 'medium',
          timeStyle: 'short',
        }),
      }
    : {
        start: '2026-09-05 08:30',
        end: '2026-09-12 18:00',
      };

  // Primary Disease Case (first active case)
  const primaryCase = cases.length > 0 ? cases[0] : null;

  // Paginated slice of history table
  const paginatedHistory = locationHistory.slice(
    historyPage * PAGE_SIZE,
    (historyPage + 1) * PAGE_SIZE
  );
  const totalPages = Math.ceil(locationHistory.length / PAGE_SIZE) || 1;

  return (
    <div className="space-y-6">
      {/* ==================================================================== */}
      {/* 1. Header / Welcome Banner */}
      {/* ==================================================================== */}
      <div className="relative overflow-hidden rounded-2xl bg-gradient-to-r from-slate-900 via-indigo-950/40 to-slate-900 border border-slate-800 p-6 md:p-8 shadow-xl">
        <div className="absolute right-0 top-0 bottom-0 w-1/3 bg-gradient-to-l from-brand-500/10 to-transparent pointer-events-none" />
        
        <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div className="space-y-2">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-brand-500/10 border border-brand-500/30 text-xs font-semibold text-brand-400">
              <ShieldCheck className="w-3.5 h-3.5" />
              <span>Role: PATIENT &bull; Protected Health Data</span>
            </div>

            <h1 className="font-heading text-2xl md:text-3xl font-extrabold text-white tracking-tight">
              Welcome, {profile ? profile.full_name : 'Synthetic Patient 101'}
            </h1>

            <p className="text-sm text-slate-400 max-w-2xl leading-relaxed">
              Your personal health surveillance dashboard. Access your diagnosed conditions, authorized location monitoring status, telemetry records, and movement observations under strict privacy protections.
            </p>
          </div>

          <div className="flex flex-col sm:flex-row items-start sm:items-center gap-3 shrink-0">
            <div className="px-4 py-2 rounded-xl bg-slate-950/80 border border-slate-800 flex items-center gap-3">
              <div className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse" />
              <div className="text-xs">
                <span className="text-slate-500 block text-[10px] font-mono uppercase">Pseudo ID</span>
                <span className="font-mono font-bold text-slate-200">
                  {profile ? profile.pseudo_id : 'PAT-SYNTH-101'}
                </span>
              </div>
            </div>

            <button
              onClick={loadPatientData}
              disabled={isLoading}
              className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 text-xs font-medium transition-all shadow-sm active:scale-95 disabled:opacity-50"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
              <span>Refresh Records</span>
            </button>
          </div>
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 flex items-start gap-3 text-rose-400 text-sm">
          <AlertTriangle className="w-5 h-5 shrink-0 mt-0.5" />
          <div>
            <div className="font-semibold">Security / Authorization Notice</div>
            <div className="text-xs text-rose-300/90 mt-0.5">{error}</div>
          </div>
        </div>
      )}

      {/* ==================================================================== */}
      {/* 2. Top Grid: My Health & My Disease Case */}
      {/* ==================================================================== */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        
        {/* CARD: My Health */}
        <div className="glass-panel rounded-2xl p-6 border border-slate-800 flex flex-col justify-between hover:border-slate-700 transition-colors">
          <div>
            <div className="flex items-center justify-between pb-4 border-b border-slate-800">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-brand-500/10 border border-brand-500/30 flex items-center justify-center text-brand-400">
                  <User className="w-5 h-5" />
                </div>
                <div>
                  <h2 className="font-heading text-lg font-bold text-white">My Health</h2>
                  <p className="text-xs text-slate-400">Demographic & Residential Profile</p>
                </div>
              </div>
              <span className="text-[11px] px-2.5 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 font-medium">
                Active Record
              </span>
            </div>

            <div className="mt-5 grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="p-3.5 rounded-xl bg-slate-900/60 border border-slate-800/80 space-y-1">
                <span className="text-[11px] text-slate-400 flex items-center gap-1.5">
                  <Activity className="w-3.5 h-3.5 text-brand-400" />
                  <span>Age & Gender</span>
                </span>
                <div className="text-sm font-semibold text-slate-200">
                  {profile ? `${profile.age} Years (${profile.gender})` : '34 Years (MALE)'}
                </div>
              </div>

              <div className="p-3.5 rounded-xl bg-slate-900/60 border border-slate-800/80 space-y-1">
                <span className="text-[11px] text-slate-400 flex items-center gap-1.5">
                  <Phone className="w-3.5 h-3.5 text-brand-400" />
                  <span>Contact Number</span>
                </span>
                <div className="text-sm font-semibold text-slate-200">
                  {profile?.contact_number || '+1-555-0192'}
                </div>
              </div>

              <div className="p-3.5 rounded-xl bg-slate-900/60 border border-slate-800/80 space-y-1 sm:col-span-2">
                <span className="text-[11px] text-slate-400 flex items-center gap-1.5">
                  <Home className="w-3.5 h-3.5 text-brand-400" />
                  <span>Residential Address</span>
                </span>
                <div className="text-sm font-semibold text-slate-200">
                  {profile?.address || '104 Maple Street, Palayam'}
                </div>
              </div>

              <div className="p-3.5 rounded-xl bg-slate-900/60 border border-slate-800/80 space-y-1 sm:col-span-2">
                <span className="text-[11px] text-slate-400 flex items-center gap-1.5">
                  <MapPin className="w-3.5 h-3.5 text-brand-400" />
                  <span>Kerala Administrative Ward</span>
                </span>
                <div className="text-xs font-mono text-slate-300">
                  Ward #{profile?.ward_number ?? 1} &bull; {profile?.local_body_name || 'Thiruvananthapuram Municipal Corporation'} &bull; {profile?.district_name || 'Thiruvananthapuram'}
                </div>
              </div>
            </div>
          </div>

          <div className="mt-5 pt-3 border-t border-slate-800/60 flex items-center justify-between text-[11px] text-slate-500">
            <span>Identity Protection: Pseudo-ID Tagged</span>
            <span className="font-mono text-emerald-400">Strict RBAC Enforced</span>
          </div>
        </div>

        {/* CARD: My Disease Case */}
        <div className="glass-panel rounded-2xl p-6 border border-slate-800 flex flex-col justify-between hover:border-slate-700 transition-colors">
          <div>
            <div className="flex items-center justify-between pb-4 border-b border-slate-800">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-rose-500/10 border border-rose-500/30 flex items-center justify-center text-rose-400">
                  <Activity className="w-5 h-5" />
                </div>
                <div>
                  <h2 className="font-heading text-lg font-bold text-white">My Disease Case</h2>
                  <p className="text-xs text-slate-400">Surveillance Case Registry</p>
                </div>
              </div>

              <span className={`text-[11px] px-2.5 py-1 rounded-full font-semibold border ${
                primaryCase?.case_status === 'CONFIRMED'
                  ? 'bg-rose-500/15 text-rose-400 border-rose-500/30'
                  : primaryCase?.case_status === 'RECOVERED'
                  ? 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30'
                  : 'bg-amber-500/15 text-amber-400 border-amber-500/30'
              }`}>
                {primaryCase?.case_status || 'CONFIRMED'}
              </span>
            </div>

            <div className="mt-5 space-y-3.5">
              <div className="flex items-center justify-between p-3 rounded-xl bg-slate-900/60 border border-slate-800/80">
                <div>
                  <div className="text-[11px] text-slate-400">Diagnosed Condition</div>
                  <div className="text-base font-bold text-white mt-0.5">
                    {primaryCase?.disease?.name || 'Dengue Fever'}
                  </div>
                </div>
                <span className="px-2.5 py-1 rounded-lg bg-slate-800 font-mono text-xs font-semibold text-brand-400 border border-slate-700">
                  {primaryCase?.disease?.code || 'DENGUE-01'}
                </span>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800/80">
                  <span className="text-[11px] text-slate-400 block">Clinical Severity</span>
                  <span className="text-xs font-semibold text-amber-300 mt-1 inline-block">
                    {primaryCase?.severity || 'MODERATE'}
                  </span>
                </div>

                <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800/80">
                  <span className="text-[11px] text-slate-400 block">Diagnosis Date</span>
                  <span className="text-xs font-semibold text-slate-200 mt-1 inline-block">
                    {primaryCase?.diagnosis_date ? new Date(primaryCase.diagnosis_date).toLocaleDateString('en-IN', {
                      dateStyle: 'medium',
                    }) : '2026-09-04'}
                  </span>
                </div>
              </div>

              <div className="p-3.5 rounded-xl bg-slate-900/60 border border-slate-800/80">
                <div className="text-[11px] text-slate-400 font-medium mb-1 flex items-center gap-1.5">
                  <Info className="w-3.5 h-3.5 text-brand-400" />
                  <span>Clinical Observations & Notes</span>
                </div>
                <p className="text-xs text-slate-300 leading-relaxed italic">
                  "{primaryCase?.clinical_notes || 'Patient presented with acute high fever, thrombocytopenia, and retro-orbital pain in Palayam Ward. Monitored for plasma leakage.'}"
                </p>
              </div>
            </div>
          </div>

          <div className="mt-5 pt-3 border-t border-slate-800/60 flex items-center justify-between text-[11px] text-slate-500">
            <span>Surveillance Node: Kerala Public Health Dept</span>
            <span className="text-slate-400">Contagion: Vector-Borne</span>
          </div>
        </div>

      </div>

      {/* ==================================================================== */}
      {/* 3. MONITORING CARD */}
      {/* ==================================================================== */}
      <div className="glass-panel rounded-2xl p-6 md:p-8 border border-slate-800 bg-gradient-to-b from-slate-900/90 to-slate-950/90 shadow-xl">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 pb-6 border-b border-slate-800">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-2xl bg-brand-500/15 border border-brand-500/30 flex items-center justify-center text-brand-400 shrink-0">
              <Radio className="w-6 h-6 animate-pulse" />
            </div>
            <div>
              <div className="flex items-center gap-2.5">
                <h2 className="font-heading text-xl font-bold text-white">My Monitoring</h2>
                <span className={`inline-flex items-center gap-1.5 text-xs font-semibold px-3 py-1 rounded-full border ${statusBadge.color}`}>
                  <span className={`w-2 h-2 rounded-full ${statusBadge.dot}`} />
                  <span>Monitoring Status: {statusBadge.label}</span>
                </span>
              </div>
              <p className="text-xs text-slate-400 mt-1">
                Authorized location telemetry collection active under explicit patient consent agreement.
              </p>
            </div>
          </div>

          <button
            onClick={onNavigateToRoadmap}
            className="inline-flex items-center justify-center gap-2 px-6 py-3 rounded-xl bg-gradient-to-r from-brand-600 to-indigo-600 hover:from-brand-500 hover:to-indigo-500 text-white font-semibold text-sm shadow-lg shadow-brand-500/20 transition-all active:scale-95 group shrink-0"
          >
            <Route className="w-4 h-4 transition-transform group-hover:scale-110" />
            <span>View My Movement Roadmap</span>
            <ChevronRight className="w-4 h-4 transition-transform group-hover:translate-x-1" />
          </button>
        </div>

        {/* Monitoring Metrics Row */}
        <div className="mt-6 grid grid-cols-1 md:grid-cols-3 gap-5">
          {/* Status Metric */}
          <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 space-y-2">
            <span className="text-xs font-medium text-slate-400 flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-400" />
              <span>Monitoring Status</span>
            </span>
            <div className="text-lg font-bold text-white flex items-center gap-2">
              <span className={`px-2.5 py-0.5 rounded-md text-xs font-mono font-bold ${statusBadge.color}`}>
                {statusBadge.label}
              </span>
              <span className="text-xs font-normal text-slate-400">
                {statusBadge.label === 'ACTIVE' ? 'Telemetry Authorized' : 'Telemetry Inactive'}
              </span>
            </div>
          </div>

          {/* Monitoring Period */}
          <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 space-y-2">
            <span className="text-xs font-medium text-slate-400 flex items-center gap-2">
              <Calendar className="w-4 h-4 text-indigo-400" />
              <span>Monitoring Period</span>
            </span>
            <div className="text-xs font-semibold text-slate-200 leading-snug">
              <div>{sessionPeriod.start}</div>
              <div className="text-slate-500 text-[11px] font-mono">↓ to</div>
              <div>{sessionPeriod.end}</div>
            </div>
          </div>

          {/* Location Sampling */}
          <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 space-y-2">
            <span className="text-xs font-medium text-slate-400 flex items-center gap-2">
              <Clock className="w-4 h-4 text-brand-400" />
              <span>Location Sampling</span>
            </span>
            <div className="text-lg font-bold text-white font-heading">
              Approximately 15 minutes
            </div>
            <div className="text-[11px] text-slate-400">
              Discrete observations &bull; NOT continuous 10-second GPS
            </div>
          </div>
        </div>

        <div className="mt-5 p-3.5 rounded-xl bg-slate-950/60 border border-slate-800/80 text-xs text-slate-400 flex items-start gap-2.5">
          <Info className="w-4 h-4 text-brand-400 shrink-0 mt-0.5" />
          <span>
            {monitoringStatus?.explanation_notice ||
              'HealthWatch will collect your location approximately every 15 minutes during the authorized monitoring period. Continuous second-by-second tracking is never performed.'}
          </span>
        </div>
      </div>

      {/* ==================================================================== */}
      {/* 4. MY LOCATION HISTORY TABLE */}
      {/* ==================================================================== */}
      <div className="glass-panel rounded-2xl p-6 border border-slate-800">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-800">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-indigo-500/10 border border-indigo-500/30 flex items-center justify-center text-indigo-400">
              <FileSpreadsheet className="w-5 h-5" />
            </div>
            <div>
              <h2 className="font-heading text-lg font-bold text-white">My Location History</h2>
              <p className="text-xs text-slate-400">
                Audited location observations recorded under patient consent ({historyTotal || locationHistory.length} total points)
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2 text-xs text-slate-400">
            <span className="px-2.5 py-1 rounded-lg bg-slate-900 border border-slate-800 font-mono">
              Page {historyPage + 1} of {totalPages}
            </span>
          </div>
        </div>

        {/* Table Container */}
        <div className="mt-5 overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-slate-800 text-[11px] font-semibold text-slate-400 uppercase tracking-wider bg-slate-900/50">
                <th className="py-3 px-4">Timestamp</th>
                <th className="py-3 px-4">Latitude</th>
                <th className="py-3 px-4">Longitude</th>
                <th className="py-3 px-4">Accuracy</th>
                <th className="py-3 px-4">Source</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 text-xs">
              {paginatedHistory.length > 0 ? (
                paginatedHistory.map((item, idx) => (
                  <tr
                    key={item.id || idx}
                    className="hover:bg-slate-800/40 transition-colors group"
                  >
                    {/* Timestamp */}
                    <td className="py-3 px-4 font-mono text-slate-300">
                      <div className="flex items-center gap-2">
                        <Clock className="w-3.5 h-3.5 text-slate-500 group-hover:text-brand-400 transition-colors" />
                        <span>
                          {new Date(item.recorded_at).toLocaleString('en-IN', {
                            dateStyle: 'short',
                            timeStyle: 'medium',
                          })}
                        </span>
                      </div>
                    </td>

                    {/* Latitude */}
                    <td className="py-3 px-4 font-mono text-slate-200">
                      {item.latitude.toFixed(5)}° N
                    </td>

                    {/* Longitude */}
                    <td className="py-3 px-4 font-mono text-slate-200">
                      {item.longitude.toFixed(5)}° E
                    </td>

                    {/* Accuracy */}
                    <td className="py-3 px-4 font-mono">
                      <span className="inline-flex items-center gap-1 text-slate-300">
                        <Crosshair className="w-3 h-3 text-emerald-400" />
                        <span>&plusmn;{item.accuracy !== null && item.accuracy !== undefined ? `${item.accuracy}m` : '10.0m'}</span>
                      </span>
                    </td>

                    {/* Source */}
                    <td className="py-3 px-4">
                      <span className="inline-flex items-center px-2 py-0.5 rounded-md text-[10px] font-mono font-medium bg-indigo-500/10 text-indigo-300 border border-indigo-500/20">
                        {item.source || 'PATIENT_GPS'}
                      </span>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={5} className="py-8 text-center text-slate-500">
                    No location history records logged yet for this monitoring session.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        {/* Table Pagination Controls */}
        {totalPages > 1 && (
          <div className="mt-4 pt-4 border-t border-slate-800/80 flex items-center justify-between text-xs">
            <span className="text-slate-500 text-[11px]">
              Showing {historyPage * PAGE_SIZE + 1} to{' '}
              {Math.min((historyPage + 1) * PAGE_SIZE, locationHistory.length)} of{' '}
              {locationHistory.length} observations
            </span>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setHistoryPage((p) => Math.max(p - 1, 0))}
                disabled={historyPage === 0}
                className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 disabled:opacity-40 disabled:hover:bg-slate-800 transition-colors"
              >
                Previous
              </button>
              <button
                onClick={() => setHistoryPage((p) => Math.min(p + 1, totalPages - 1))}
                disabled={historyPage >= totalPages - 1}
                className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 disabled:opacity-40 disabled:hover:bg-slate-800 transition-colors"
              >
                Next
              </button>
            </div>
          </div>
        )}
      </div>

      {/* ==================================================================== */}
      {/* 5. MY MOVEMENT ROADMAP (Integrated Preview & Stats) */}
      {/* ==================================================================== */}
      <div className="glass-panel rounded-2xl p-6 border border-slate-800 space-y-5">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-800">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-brand-500/10 border border-brand-500/30 flex items-center justify-center text-brand-400">
              <Route className="w-5 h-5" />
            </div>
            <div>
              <h2 className="font-heading text-lg font-bold text-white">My Movement Roadmap</h2>
              <p className="text-xs text-slate-400">
                Sequential visualization of authorized discrete location observations
              </p>
            </div>
          </div>

          <button
            onClick={onNavigateToRoadmap}
            className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-brand-400 hover:text-brand-300 border border-slate-700 text-xs font-semibold transition-all group"
          >
            <span>Open Interactive Map View</span>
            <ExternalLink className="w-3.5 h-3.5 transition-transform group-hover:translate-x-0.5" />
          </button>
        </div>

        {/* Roadmap Observation Sequence Card */}
        {roadmap && roadmap.observations && roadmap.observations.length > 0 ? (
          <div className="space-y-4">
            {/* Quick Metrics Bar */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800">
                <span className="text-[10px] text-slate-400 uppercase font-mono">Total Points</span>
                <div className="text-lg font-bold text-white mt-0.5">
                  {roadmap.statistics.total_observations} Observations
                </div>
              </div>

              <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800">
                <span className="text-[10px] text-slate-400 uppercase font-mono">First Point</span>
                <div className="text-xs font-mono font-semibold text-slate-200 mt-1">
                  Point A ({new Date(roadmap.observations[0].recorded_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })})
                </div>
              </div>

              <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800">
                <span className="text-[10px] text-slate-400 uppercase font-mono">Last Point</span>
                <div className="text-xs font-mono font-semibold text-slate-200 mt-1">
                  Point {String.fromCharCode(64 + roadmap.observations.length)} ({new Date(roadmap.observations[roadmap.observations.length - 1].recorded_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })})
                </div>
              </div>

              <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800">
                <span className="text-[10px] text-slate-400 uppercase font-mono">Average Accuracy</span>
                <div className="text-base font-bold text-emerald-400 mt-0.5 font-mono">
                  &plusmn;{roadmap.statistics.average_accuracy || 11.5} m
                </div>
              </div>
            </div>

            {/* Observation Sequence Stepper Preview */}
            <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 overflow-x-auto">
              <div className="text-[11px] font-semibold text-slate-400 mb-3 uppercase tracking-wider">
                Recorded Observation Sequence (15-min Intervals)
              </div>

              <div className="flex items-center min-w-[550px] gap-2">
                {roadmap.observations.map((obs, idx) => {
                  const letter = String.fromCharCode(65 + idx);
                  const isFirst = idx === 0;
                  const isLast = idx === roadmap.observations.length - 1;

                  return (
                    <React.Fragment key={obs.id || idx}>
                      <div className="flex flex-col items-center">
                        <div
                          className={`w-9 h-9 rounded-xl flex items-center justify-center font-bold font-mono text-xs border shadow-sm ${
                            isFirst
                              ? 'bg-emerald-500/20 text-emerald-400 border-emerald-500/50'
                              : isLast
                              ? 'bg-rose-500/20 text-rose-400 border-rose-500/50'
                              : 'bg-brand-500/20 text-brand-400 border-brand-500/50'
                          }`}
                        >
                          {letter}
                        </div>
                        <span className="text-[10px] font-mono text-slate-400 mt-1">
                          {new Date(obs.recorded_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        </span>
                      </div>

                      {!isLast && (
                        <div className="flex-1 flex items-center justify-center">
                          <div className="h-0.5 w-full bg-slate-700 border-t border-dashed border-brand-500/50" />
                        </div>
                      )}
                    </React.Fragment>
                  );
                })}
              </div>
            </div>
          </div>
        ) : (
          <div className="p-8 text-center bg-slate-900/40 rounded-xl border border-dashed border-slate-800 text-slate-400 text-sm">
            No movement roadmap points recorded for the current filter.
          </div>
        )}

        {/* Technical Limitation Disclaimer (Required) */}
        <div className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/20 flex items-start gap-3 text-xs text-amber-300/90 leading-relaxed">
          <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
          <div>
            <span className="font-semibold text-amber-300 block mb-0.5">
              Technical Limitation & Privacy Notice:
            </span>
            {roadmap?.disclaimer ||
              'This roadmap reflects recorded discrete location observations under authorized patient consent (sampling interval approximately 15 minutes). It does NOT represent exact continuous real-time movement or continuous paths.'}
          </div>
        </div>
      </div>
    </div>
  );
};
