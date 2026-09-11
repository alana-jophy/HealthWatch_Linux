import React, { useState, useEffect, useRef, useMemo } from 'react';
import { 
  MapContainer, 
  TileLayer, 
  Marker, 
  Popup, 
  Polyline, 
  Circle,
  useMap 
} from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { 
  fetchPatientRoadmap,
  fetchPatientsList,
  fetchMyPatientProfile
} from '../../services/api';
import { 
  PatientRoadmapResponse, 
  RoadmapObservationItem
} from '../../types';
import { useAuth } from '../../context/AuthContext';
import { 
  Route, 
  AlertTriangle, 
  Clock, 
  Calendar, 
  Search, 
  RotateCcw, 
  MapPin, 
  User,
  Activity,
  Maximize2,
  Minimize2,
  AlertCircle,
  CheckCircle2,
  Sliders
} from 'lucide-react';

// Leaflet default icon fix
delete (L.Icon.Default.prototype as any)._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
});

// Helper component to auto-fit map viewport to polyline bounds or pan to selected observation
const MapBoundsFitter: React.FC<{ 
  observations: RoadmapObservationItem[]; 
  selectedCoord?: [number, number] | null;
}> = ({
  observations,
  selectedCoord
}) => {
  const map = useMap();

  useEffect(() => {
    if (selectedCoord) {
      map.flyTo(selectedCoord, 16, { duration: 1.2 });
    } else if (observations.length > 0) {
      const bounds = L.latLngBounds(observations.map(o => [o.latitude, o.longitude]));
      map.fitBounds(bounds, { padding: [50, 50], maxZoom: 16 });
    }
  }, [observations, selectedCoord, map]);

  return null;
};

// Create custom colored DivIcon supporting both Officer Letter Markers (A, B, C...) and Patient Numeric Markers (1, 2, 3...)
const createCustomMarkerIcon = (
  obsNumber: number,
  index: number, 
  total: number, 
  timeStr: string, 
  isSelected: boolean,
  source: string,
  movementStatus?: string,
  isStationaryDrift?: boolean,
  isOfficerMode: boolean = false
) => {
  const isStart = index === 0;
  const isEnd = index === total - 1 && total > 1;

  let bgClass = 'bg-cyan-500';
  let borderClass = 'border-cyan-300';

  if (isOfficerMode) {
    if (isStart) {
      bgClass = 'bg-emerald-500';
      borderClass = 'border-emerald-200';
    } else if (isEnd) {
      bgClass = 'bg-rose-500';
      borderClass = 'border-rose-200';
    } else if (source === 'HEALTH_WORKER') {
      bgClass = 'bg-indigo-500';
      borderClass = 'border-indigo-300';
    } else {
      bgClass = 'bg-cyan-500';
      borderClass = 'border-cyan-300';
    }
  } else {
    if (source === 'STATIC_ADMIN_LOCATION') {
      bgClass = 'bg-amber-500';
      borderClass = 'border-amber-300';
    } else if (isStationaryDrift || movementStatus === 'STATIONARY_DRIFT') {
      bgClass = 'bg-slate-700';
      borderClass = 'border-amber-400';
    } else if (isStart) {
      bgClass = 'bg-emerald-500';
      borderClass = 'border-emerald-200';
    } else if (isEnd) {
      bgClass = 'bg-rose-500';
      borderClass = 'border-rose-200';
    } else if (source === 'HEALTH_WORKER') {
      bgClass = 'bg-indigo-500';
      borderClass = 'border-indigo-300';
    }
  }

  const selectedRing = isSelected ? 'ring-4 ring-cyan-400/80 scale-125 z-50' : 'hover:scale-110';
  const label = isOfficerMode ? String.fromCharCode(65 + (index % 26)) : obsNumber;

  const html = `
    <div class="relative flex items-center justify-center transition-all duration-300 ${selectedRing}">
      <div class="w-8 h-8 rounded-full ${bgClass} text-white font-bold text-[11px] flex items-center justify-center shadow-lg border-2 ${borderClass} font-mono tracking-tight">
        ${label}
      </div>
      <div class="absolute -bottom-5 whitespace-nowrap bg-slate-950/90 text-[9px] font-semibold text-slate-200 px-1.5 py-0.5 rounded border border-slate-800 shadow pointer-events-none">
        ${timeStr}
      </div>
    </div>
  `;

  return L.divIcon({
    html,
    className: 'custom-roadmap-marker',
    iconSize: [32, 32],
    iconAnchor: [16, 16],
    popupAnchor: [0, -18],
  });
};

interface PatientMovementRoadmapProps {
  isOfficerMode?: boolean;
  officerPatientPseudoId?: string;
  officerFilterDate?: string;
}

export const PatientMovementRoadmap: React.FC<PatientMovementRoadmapProps> = ({
  isOfficerMode = false,
  officerPatientPseudoId,
  officerFilterDate,
}) => {
  const { user, role } = useAuth();
  const isPatientUser = role === 'PATIENT';

  // Filters State
  const [selectedPseudoId, setSelectedPseudoId] = useState<string>(
    officerPatientPseudoId || (isPatientUser && user?.patient_pseudo_id ? user.patient_pseudo_id : '')
  );
  const [selectedDate, setSelectedDate] = useState<string>(officerFilterDate || '');
  const [startTime, setStartTime] = useState<string>('');
  const [endTime, setEndTime] = useState<string>('');

  // Roadmap Data & State
  const [patients, setPatients] = useState<{ pseudo_id: string; full_name: string }[]>([]);
  const [roadmapData, setRoadmapData] = useState<PatientRoadmapResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedPointId, setSelectedPointId] = useState<string | null>(null);
  const [flyToCoord, setFlyToCoord] = useState<[number, number] | null>(null);
  const [isLivePolling, setIsLivePolling] = useState<boolean>(false);
  const [isFullscreen, setIsFullscreen] = useState<boolean>(false);

  const timelineRef = useRef<HTMLDivElement>(null);
  const mapWrapperRef = useRef<HTMLDivElement>(null);

  // Auto-resolve patient identity in patient mode
  useEffect(() => {
    if (isPatientUser) {
      if (user?.patient_pseudo_id) {
        setSelectedPseudoId(user.patient_pseudo_id);
      } else {
        fetchMyPatientProfile()
          .then((profile) => {
            if (profile?.pseudo_id) {
              setSelectedPseudoId(profile.pseudo_id);
            }
          })
          .catch((err) => console.warn('Could not auto-fetch patient profile for roadmap:', err));
      }
    }
  }, [isPatientUser, user]);

  useEffect(() => {
    if (officerPatientPseudoId) {
      setSelectedPseudoId(officerPatientPseudoId);
    }
    if (officerFilterDate !== undefined) {
      setSelectedDate(officerFilterDate);
    }
  }, [officerPatientPseudoId, officerFilterDate]);

  useEffect(() => {
    if (!isPatientUser) {
      fetchPatientsList()
        .then((res) => {
          if (res?.items) {
            setPatients(res.items.map((p) => ({ pseudo_id: p.pseudo_id, full_name: p.full_name })));
          }
        })
        .catch((err) => {
          console.warn('Could not load patient registry for roadmap selector:', err);
        });
    }
  }, [isPatientUser]);

  // Fullscreen change listener
  useEffect(() => {
    const handleFullscreenChange = () => {
      setIsFullscreen(!!document.fullscreenElement);
    };
    document.addEventListener('fullscreenchange', handleFullscreenChange);
    return () => document.removeEventListener('fullscreenchange', handleFullscreenChange);
  }, []);

  const toggleFullscreen = () => {
    if (!document.fullscreenElement) {
      if (mapWrapperRef.current?.requestFullscreen) {
        mapWrapperRef.current.requestFullscreen().catch(() => {});
      } else {
        setIsFullscreen(!isFullscreen);
      }
    } else {
      if (document.exitFullscreen) {
        document.exitFullscreen().catch(() => {});
      }
    }
  };

  const loadRoadmap = async () => {
    if (!isPatientUser && !selectedPseudoId) {
      setIsLoading(false);
      setRoadmapData(null);
      return;
    }
    setIsLoading(true);
    setError(null);
    try {
      const data = await fetchPatientRoadmap({
        pseudoId: isPatientUser ? undefined : selectedPseudoId,
        date: selectedDate || undefined,
        startTime: startTime || undefined,
        endTime: endTime || undefined,
      });
      setRoadmapData(data);
      if (data.patient_pseudo_id && !selectedPseudoId) {
        setSelectedPseudoId(data.patient_pseudo_id);
      }
      if (data.observations && data.observations.length > 0) {
        const sorted = [...data.observations].sort(
          (a, b) => new Date(a.recorded_at).getTime() - new Date(b.recorded_at).getTime()
        );
        setSelectedPointId(sorted[sorted.length - 1].id);
      } else {
        setSelectedPointId(null);
      }
    } catch (err: any) {
      console.error('Failed to query movement roadmap:', err);
      setError(err?.response?.data?.error?.message || err?.message || 'Failed to load movement roadmap');
    } finally {
      setIsLoading(false);
    }
  };

  // Safe Near-Real-Time Dashboard Polling
  useEffect(() => {
    if (!isLivePolling) return;
    if (!isPatientUser && !selectedPseudoId) return;
    const interval = setInterval(() => {
      fetchPatientRoadmap({
        pseudoId: isPatientUser ? undefined : selectedPseudoId,
        date: selectedDate || undefined,
        startTime: startTime || undefined,
        endTime: endTime || undefined,
      })
        .then((data) => {
          setRoadmapData(data);
        })
        .catch((err) => console.warn('Roadmap polling update notice:', err));
    }, 15000);
    return () => clearInterval(interval);
  }, [isLivePolling, isPatientUser, selectedPseudoId, selectedDate, startTime, endTime]);

  useEffect(() => {
    if (isPatientUser || selectedPseudoId) {
      loadRoadmap();
    } else {
      setIsLoading(false);
    }
  }, [isPatientUser, selectedPseudoId, selectedDate]);

  const handleApplyFilters = (e: React.FormEvent) => {
    e.preventDefault();
    loadRoadmap();
  };

  const handleSelectToday = () => {
    const today = new Date().toISOString().split('T')[0];
    setSelectedDate(today);
    setStartTime('00:00');
    setEndTime('23:59');
  };

  const handleClearDateFilter = () => {
    setSelectedDate('');
    setStartTime('');
    setEndTime('');
  };

  const handleSelectObservation = (point: RoadmapObservationItem) => {
    setSelectedPointId(point.id);
    setFlyToCoord([point.latitude, point.longitude]);

    const el = document.getElementById(`timeline-item-${point.id}`);
    if (el && timelineRef.current) {
      el.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
  };

  // Chronologically sort all observations (recorded_at ASC)
  const sortedObservations: RoadmapObservationItem[] = useMemo(() => {
    if (!roadmapData?.observations) return [];
    return [...roadmapData.observations].sort(
      (a, b) => new Date(a.recorded_at).getTime() - new Date(b.recorded_at).getTime()
    );
  }, [roadmapData?.observations]);

  // Construct movement polyline:
  // - In Officer Mode: Connect all recorded observations sequentially as the reference visual trail
  // - In Patient Mode: Only connect verified physical displacement segments (suppressing stationary drift back and forth)
  const polylineCoords: [number, number][] = useMemo(() => {
    if (!sortedObservations || sortedObservations.length <= 1) return [];

    if (isOfficerMode) {
      return sortedObservations.map(o => [o.latitude, o.longitude]);
    }

    const hasConfirmedMovement = sortedObservations.some(obs => obs.movement_status === 'CONFIRMED_MOVEMENT');
    if (!hasConfirmedMovement) {
      // All observations represent stationary location / GPS drift
      return [];
    }

    // Connect sequence of distinct confirmed location anchors
    const points: [number, number][] = [];
    let lastPt: [number, number] | null = null;

    for (const obs of sortedObservations) {
      if (obs.movement_status === 'INITIAL') {
        const pt: [number, number] = [obs.anchor_latitude || obs.latitude, obs.anchor_longitude || obs.longitude];
        points.push(pt);
        lastPt = pt;
      } else if (obs.movement_status === 'CONFIRMED_MOVEMENT') {
        const pt: [number, number] = [obs.anchor_latitude || obs.latitude, obs.anchor_longitude || obs.longitude];
        if (!lastPt || lastPt[0] !== pt[0] || lastPt[1] !== pt[1]) {
          points.push(pt);
          lastPt = pt;
        }
      }
    }

    return points.length > 1 ? points : [];
  }, [sortedObservations, isOfficerMode]);

  const latestObservation = sortedObservations.length > 0 
    ? sortedObservations[sortedObservations.length - 1] 
    : null;

  const defaultCenter: [number, number] = latestObservation
    ? [latestObservation.latitude, latestObservation.longitude]
    : [10.5276, 76.2144]; // Central Kerala (Thrissur)

  const isStaticAdmin = roadmapData?.is_static_admin_location || !roadmapData?.has_phone;

  return (
    <div className="space-y-6">
      {/* 1. Header Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-cyan-500/10 border border-cyan-500/20 text-xs font-semibold text-cyan-400 mb-2">
            <Route className="w-3.5 h-3.5" />
            <span>{isOfficerMode ? 'Movement Analysis' : 'My Movement Roadmap'}</span>
          </div>
          <h1 className="font-heading text-2xl md:text-3xl font-extrabold text-white tracking-tight">
            {isOfficerMode ? 'Movement Analysis' : 'Patient Movement Roadmap'}
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            {isOfficerMode 
              ? `Surveillance movement analysis and sequential travel observations for registered patients (approximately ~${roadmapData?.tracking_interval_minutes || 15}-minute cadence).`
              : `Visualizing personal spatial telemetry observations collected approximately every ${roadmapData?.tracking_interval_minutes || 15} minutes.`}
          </p>
        </div>

        {/* Identity Pill */}
        <div className="glass-panel px-4 py-2.5 rounded-xl border border-slate-800 flex items-center gap-3 shrink-0 self-start">
          <div className="w-9 h-9 rounded-lg bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center text-cyan-400">
            <User className="w-5 h-5" />
          </div>
          <div>
            <div className="text-xs font-medium text-slate-400">Surveillance Subject</div>
            <div className="text-sm font-bold text-white flex items-center gap-2">
              <span>{roadmapData?.patient_pseudo_id || selectedPseudoId || 'Patient'}</span>
              {roadmapData?.patient_name && (
                <span className="text-[10px] bg-slate-800 text-slate-300 px-1.5 py-0.5 rounded font-mono">
                  {roadmapData.patient_name}
                </span>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* 2. STATUTORY DISCLAIMER (Required by Prompt) */}
      <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-4 md:p-5 relative overflow-hidden">
        <div className="flex items-start gap-3.5">
          <div className="p-2 rounded-lg bg-amber-500/20 border border-amber-500/40 text-amber-400 shrink-0 mt-0.5">
            <AlertTriangle className="w-5 h-5" />
          </div>
          <div className="space-y-1.5 text-xs md:text-sm">
            <div className="font-bold text-amber-300 flex items-center gap-2">
              <span>{roadmapData?.disclaimer_title || "Recorded GPS observations"}</span>
              <span className="text-[11px] bg-amber-500/20 px-2 py-0.5 rounded-full text-amber-200 border border-amber-500/30 font-mono">
                ~{roadmapData?.tracking_interval_minutes || 15}-Min Sampling
              </span>
            </div>
            <p className="text-slate-300 leading-relaxed font-semibold">
              {roadmapData?.disclaimer || "The connecting line represents the connection between recorded observations and does not represent continuous GPS tracking."}
            </p>
            {isStaticAdmin && (
              <p className="text-amber-200 text-xs leading-relaxed bg-amber-950/40 p-2 rounded-lg border border-amber-500/20 mt-1">
                <strong>Note:</strong> This patient is registered without a smartphone. Showing the official administrative centroid for their registered Kerala local body / ward.
              </p>
            )}
          </div>
        </div>
      </div>

      {/* 3. Filter Controls & Live Polling Toolbar */}
      <div className="glass-panel p-5 rounded-2xl border border-slate-800 space-y-4">
        <form onSubmit={handleApplyFilters} className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4 items-end">
          {/* Patient Selector (Only in Officer Mode) */}
          <div>
            <label className="block text-xs font-semibold text-slate-400 mb-1.5 flex items-center gap-1.5">
              <User className="w-3.5 h-3.5 text-cyan-400" />
              <span>Patient Account:</span>
            </label>
            {isPatientUser ? (
              <input
                type="text"
                disabled
                value={selectedPseudoId ? `${selectedPseudoId} (Your Account)` : 'Your Authenticated Account'}
                className="w-full bg-slate-900/60 border border-slate-800 rounded-lg px-3 py-2 text-sm text-brand-400 font-mono text-xs opacity-80"
              />
            ) : (
              <select
                value={selectedPseudoId}
                onChange={(e) => setSelectedPseudoId(e.target.value)}
                className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-cyan-500 font-mono text-xs"
              >
                <option value="">-- Select a patient to inspect --</option>
                {patients.map((p) => (
                  <option key={p.pseudo_id} value={p.pseudo_id}>
                    {p.pseudo_id} — {p.full_name}
                  </option>
                ))}
              </select>
            )}
          </div>

          {/* Date Selector */}
          <div>
            <label className="block text-xs font-semibold text-slate-400 mb-1.5 flex items-center gap-1.5">
              <Calendar className="w-3.5 h-3.5 text-cyan-400" />
              <span>Surveillance Date:</span>
            </label>
            <input
              type="date"
              value={selectedDate}
              onChange={(e) => setSelectedDate(e.target.value)}
              className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-cyan-500 text-xs"
            />
          </div>

          {/* Quick Date Shortcuts */}
          <div className="flex gap-2">
            <button
              type="button"
              onClick={handleSelectToday}
              className="flex-1 py-2 px-3 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs rounded-lg font-medium transition-colors border border-slate-700"
            >
              Today
            </button>
            <button
              type="button"
              onClick={handleClearDateFilter}
              className="flex-1 py-2 px-3 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs rounded-lg font-medium transition-colors border border-slate-700"
            >
              All Dates
            </button>
          </div>

          {/* Filter Action */}
          <div>
            <button
              type="submit"
              disabled={isLoading}
              className="w-full py-2 px-4 bg-cyan-600 hover:bg-cyan-500 disabled:opacity-50 text-white text-xs font-semibold rounded-lg transition-colors flex items-center justify-center gap-1.5 shadow"
            >
              <Search className="w-3.5 h-3.5" />
              <span>Apply Filters</span>
            </button>
          </div>

          {/* Live Sync Toggle */}
          <div>
            <button
              type="button"
              onClick={() => setIsLivePolling(!isLivePolling)}
              className={`w-full py-2 px-3 rounded-lg text-xs font-semibold transition-all flex items-center justify-center gap-2 border ${
                isLivePolling
                  ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40 shadow-sm shadow-emerald-500/20'
                  : 'bg-slate-800 hover:bg-slate-700 text-slate-300 border-slate-700'
              }`}
            >
              <span className={`w-2 h-2 rounded-full ${isLivePolling ? 'bg-emerald-400 animate-ping' : 'bg-slate-500'}`} />
              <span>{isLivePolling ? 'Live Sync Active (15s)' : 'Enable Live Sync'}</span>
            </button>
          </div>
        </form>
      </div>

      {/* 4. Telemetry Statistics Grid */}
      {roadmapData?.statistics && (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
          <div className="glass-panel p-3.5 rounded-xl border border-slate-800">
            <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Observations</div>
            <div className="text-xl font-bold text-white mt-1 flex items-baseline gap-1">
              <span>{roadmapData.statistics.total_observations}</span>
              <span className="text-xs font-normal text-slate-400 font-mono">points</span>
            </div>
          </div>

          <div className="glass-panel p-3.5 rounded-xl border border-slate-800">
            <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Start Time</div>
            <div className="text-sm font-bold text-emerald-400 mt-1 font-mono">
              {roadmapData.statistics.monitoring_start 
                ? new Date(roadmapData.statistics.monitoring_start).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
                : '—'}
            </div>
            <div className="text-[10px] text-slate-500 font-mono">Marker 1 (Initial)</div>
          </div>

          <div className="glass-panel p-3.5 rounded-xl border border-slate-800">
            <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Latest Point</div>
            <div className="text-sm font-bold text-rose-400 mt-1 font-mono">
              {roadmapData.statistics.monitoring_end 
                ? new Date(roadmapData.statistics.monitoring_end).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
                : '—'}
            </div>
            <div className="text-[10px] text-slate-500 font-mono">Marker {roadmapData.statistics.total_observations || '—'}</div>
          </div>

          <div className="glass-panel p-3.5 rounded-xl border border-slate-800">
            <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Avg Accuracy</div>
            <div className="text-xl font-bold text-cyan-400 mt-1 flex items-baseline gap-1">
              <span>{roadmapData.statistics.average_accuracy !== null && roadmapData.statistics.average_accuracy !== undefined ? `±${roadmapData.statistics.average_accuracy}` : '—'}</span>
              <span className="text-xs font-normal text-slate-400 font-mono">m</span>
            </div>
          </div>

          <div className="glass-panel p-3.5 rounded-xl border border-slate-800">
            <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">GPS Cadence</div>
            <div className="text-sm font-bold text-slate-200 mt-1 font-mono">
              ~{roadmapData.tracking_interval_minutes || 15} Mins
            </div>
            <div className="text-[10px] text-slate-500 truncate">
              {roadmapData.tracking_days ? roadmapData.tracking_days.split(',').length + ' days/wk' : 'All Days'}
            </div>
          </div>

          <div className="glass-panel p-3.5 rounded-xl border border-slate-800">
            <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Latest Coord</div>
            <div className="text-xs font-bold text-slate-300 mt-1 font-mono truncate">
              {latestObservation 
                ? `${latestObservation.latitude.toFixed(4)}, ${latestObservation.longitude.toFixed(4)}`
                : '—'}
            </div>
            <div className="text-[10px] text-slate-500">{isStaticAdmin ? 'Admin Centroid' : 'WGS84 GPS'}</div>
          </div>
        </div>
      )}

      {/* Error Notice */}
      {error && (
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-sm">
          {error}
        </div>
      )}

      {/* 5. Main Visual Area: Map + Synchronized Timeline */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left/Center: Leaflet Map (8 Cols) */}
        <div className="lg:col-span-8 space-y-4">
          <div 
            ref={mapWrapperRef}
            className={`
              relative rounded-2xl overflow-hidden border border-slate-800 shadow-2xl bg-slate-950
              ${isFullscreen ? 'fixed inset-0 z-[9999] h-screen w-screen rounded-none' : 'h-[560px]'}
            `}
          >
            {/* FULL SCREEN TOGGLE BUTTON (Clear & Responsive) */}
            <div className="absolute top-4 right-4 z-[1000] flex items-center gap-2">
              <button
                type="button"
                onClick={toggleFullscreen}
                className="px-3 py-2 bg-slate-900/90 hover:bg-slate-800 text-white rounded-xl text-xs font-semibold shadow-xl border border-slate-700 flex items-center gap-1.5 backdrop-blur-md transition-all active:scale-95"
                title={isFullscreen ? 'Exit Full Screen' : 'View Map in Full Screen'}
              >
                {isFullscreen ? (
                  <>
                    <Minimize2 className="w-4 h-4 text-cyan-400" />
                    <span className="hidden sm:inline">Exit Full Screen</span>
                  </>
                ) : (
                  <>
                    <Maximize2 className="w-4 h-4 text-cyan-400" />
                    <span>FULL SCREEN</span>
                  </>
                )}
              </button>
            </div>

            {isLoading && (
              <div className="absolute inset-0 z-20 bg-slate-950/80 flex flex-col items-center justify-center space-y-3">
                <div className="w-10 h-10 border-4 border-cyan-500/30 border-t-cyan-400 rounded-full animate-spin"></div>
                <div className="text-sm font-semibold text-slate-300">Rendering Movement Roadmap...</div>
              </div>
            )}

            {!isPatientUser && !selectedPseudoId && !isLoading && (
              <div className="absolute inset-0 z-20 bg-slate-950/85 flex flex-col items-center justify-center p-6 text-center space-y-3">
                <Route className="w-12 h-12 text-cyan-400/60" />
                <p className="text-base font-semibold text-slate-200 max-w-md">
                  Please select a patient from the dropdown above to inspect their movement roadmap.
                </p>
                <p className="text-xs text-slate-400 max-w-sm">
                  Choose any registered patient from the directory to visualize their discrete surveillance observations and timeline.
                </p>
              </div>
            )}

            {((isPatientUser || selectedPseudoId) && sortedObservations.length === 0 && !isLoading) && (
              <div className="absolute inset-0 z-20 bg-slate-950/85 flex flex-col items-center justify-center p-6 text-center space-y-2">
                <MapPin className="w-10 h-10 text-slate-500" />
                <p className="text-base font-semibold text-slate-200">
                  No recorded location observations available.
                </p>
                <p className="text-xs text-slate-400 max-w-md">
                  GPS telemetry or location reports have not yet been recorded for this patient account.
                </p>
              </div>
            )}

            <MapContainer
              center={defaultCenter}
              zoom={14}
              scrollWheelZoom={true}
              className="w-full h-full"
            >
              <TileLayer
                attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              />

              <MapBoundsFitter 
                observations={sortedObservations} 
                selectedCoord={flyToCoord}
              />

              {/* Sequential Visual Connection Polyline (Chronologically Ordered for Verified Movements) */}
              {polylineCoords.length > 1 && (
                <Polyline
                  positions={polylineCoords}
                  pathOptions={{
                    color: '#0284c7',
                    weight: 4,
                    opacity: 0.85,
                    dashArray: '8, 8', // Dashed line to emphasize discrete visual connection, NOT continuous path
                    lineCap: 'round',
                    lineJoin: 'round',
                  }}
                />
              )}

              {/* Accuracy Circles for Observations (Makes GPS uncertainty margins visible) */}
              {sortedObservations.map((obs) => {
                const isSelected = obs.id === selectedPointId;
                const accRadius = obs.accuracy && obs.accuracy > 0 ? obs.accuracy : 20;
                return (
                  <Circle
                    key={`accuracy-circle-${obs.id}`}
                    center={[obs.latitude, obs.longitude]}
                    radius={accRadius}
                    pathOptions={{
                      color: isSelected ? '#06b6d4' : (obs.is_stationary_drift ? '#f59e0b' : '#0284c7'),
                      fillColor: isSelected ? '#06b6d4' : (obs.is_stationary_drift ? '#f59e0b' : '#0284c7'),
                      fillOpacity: isSelected ? 0.25 : 0.07,
                      weight: isSelected ? 2 : 1,
                      dashArray: '4, 4',
                    }}
                  />
                );
              })}

              {/* Observation Markers */}
              {sortedObservations.map((obs, idx) => {
                const isSelected = obs.id === selectedPointId;
                const obsNum = obs.observation_number || (idx + 1);
                const timeFormatted = new Date(obs.recorded_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
                const icon = createCustomMarkerIcon(
                  obsNum,
                  idx, 
                  sortedObservations.length, 
                  timeFormatted, 
                  isSelected,
                  obs.source,
                  obs.movement_status,
                  obs.is_stationary_drift,
                  isOfficerMode
                );

                const pointLetter = String.fromCharCode(65 + (idx % 26));

                return (
                  <Marker
                    key={obs.id}
                    position={[obs.latitude, obs.longitude]}
                    icon={icon}
                    eventHandlers={{
                      click: () => handleSelectObservation(obs),
                    }}
                  >
                    <Popup className="custom-popup" offset={[0, -10]}>
                      <div className="p-1 space-y-2 text-slate-900 min-w-[220px]">
                        <div className="flex items-center justify-between border-b pb-1.5">
                          <span className="font-bold text-xs uppercase tracking-wider text-cyan-800">
                            {isOfficerMode 
                              ? `Point ${pointLetter} ${idx === 0 ? '(Start Observation)' : idx === sortedObservations.length - 1 ? '(Latest Observation)' : '(Way-point)'}`
                              : `Marker ${obsNum} ${idx === 0 ? '(START)' : idx === sortedObservations.length - 1 ? '(LATEST)' : ''}`}
                          </span>
                          <span className="text-[11px] font-mono font-semibold bg-slate-100 px-1.5 py-0.5 rounded">
                            {timeFormatted}
                          </span>
                        </div>

                        <div className="space-y-1 text-xs">
                          {/* Movement Status Badge */}
                          <div className="flex justify-between items-center">
                            <span className="text-slate-500">Status:</span>
                            <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${
                              obs.is_stationary_drift 
                                ? 'bg-amber-100 text-amber-800' 
                                : obs.movement_status === 'CONFIRMED_MOVEMENT'
                                ? 'bg-cyan-100 text-cyan-800'
                                : 'bg-emerald-100 text-emerald-800'
                            }`}>
                              {obs.is_stationary_drift ? 'STATIONARY / GPS DRIFT' : obs.movement_status === 'CONFIRMED_MOVEMENT' ? 'CONFIRMED MOVEMENT' : 'INITIAL ANCHOR'}
                            </span>
                          </div>

                          <div className="flex justify-between">
                            <span className="text-slate-500">Timestamp:</span>
                            <span className="font-mono text-[11px] text-slate-700">
                              {new Date(obs.recorded_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                            </span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-slate-500">Raw GPS Coord:</span>
                            <span className="font-mono text-[11px] font-semibold text-slate-800">
                              {obs.latitude.toFixed(6)}, {obs.longitude.toFixed(6)}
                            </span>
                          </div>
                          {obs.district_name && (
                            <div className="flex justify-between">
                              <span className="text-slate-500">Location:</span>
                              <span className="font-medium text-slate-700">
                                {obs.ward_name ? `${obs.ward_name}, ` : ''}{obs.local_body_name || obs.district_name}
                              </span>
                            </div>
                          )}
                          <div className="flex justify-between">
                            <span className="text-slate-500">Reported Accuracy:</span>
                            <span className="font-mono text-[11px] text-emerald-700 font-semibold">
                              {obs.accuracy ? `±${obs.accuracy} m (Circle shown)` : (obs.source === 'STATIC_ADMIN_LOCATION' ? 'Administrative Centroid' : 'N/A')}
                            </span>
                          </div>

                          {obs.is_stationary_drift && (
                            <div className="text-[10px] text-amber-900 bg-amber-50 p-1.5 rounded border border-amber-200 mt-1 leading-snug">
                              Displacement is within GPS uncertainty margin. Preserved as stationary location.
                            </div>
                          )}

                          <div className="flex justify-between items-center pt-1 border-t">
                            <span className="text-slate-500">Data Source:</span>
                            <span className={`text-[10px] font-bold px-2 py-0.5 rounded ${
                              obs.source === 'PATIENT_GPS' 
                                ? 'bg-emerald-100 text-emerald-800'
                                : obs.source === 'STATIC_ADMIN_LOCATION'
                                ? 'bg-amber-100 text-amber-800'
                                : 'bg-indigo-100 text-indigo-800'
                            }`}>
                              {obs.source === 'PATIENT_GPS' ? 'REAL PHONE GPS' : obs.source === 'STATIC_ADMIN_LOCATION' ? 'STATIC ADMIN LOCATION' : obs.source}
                            </span>
                          </div>
                        </div>
                      </div>
                    </Popup>
                  </Marker>
                );
              })}
            </MapContainer>
          </div>

          {/* 6. MAP LEGEND */}
          <div className="glass-panel p-4 rounded-xl border border-slate-800 space-y-3">
            <div className="flex items-center justify-between pb-2 border-b border-slate-800/80">
              <span className="text-xs font-bold text-slate-300 uppercase tracking-wider font-mono flex items-center gap-2">
                <Sliders className="w-3.5 h-3.5 text-cyan-400" />
                <span>Map Legend</span>
              </span>
              <span className="text-[11px] text-slate-400 font-mono">
                Sampling Interval: ~{roadmapData?.tracking_interval_minutes || 15} Min
              </span>
            </div>

            {isOfficerMode ? (
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs text-slate-300">
                <div className="flex items-center gap-2.5 bg-slate-900/60 p-2.5 rounded-lg border border-slate-800">
                  <span className="w-6 h-6 rounded-full bg-emerald-500 border-2 border-emerald-300 text-white font-bold text-[11px] flex items-center justify-center font-mono shrink-0">
                    A
                  </span>
                  <div>
                    <div className="font-semibold text-white">Point A (Start Observation)</div>
                    <div className="text-[10px] text-slate-400">First recorded observation</div>
                  </div>
                </div>

                <div className="flex items-center gap-2.5 bg-slate-900/60 p-2.5 rounded-lg border border-slate-800">
                  <span className="w-6 h-6 rounded-full bg-cyan-500 border-2 border-cyan-300 text-white font-bold text-[11px] flex items-center justify-center font-mono shrink-0">
                    B...
                  </span>
                  <div>
                    <div className="font-semibold text-cyan-300">Intermediate Observations</div>
                    <div className="text-[10px] text-slate-400">Way-points along route</div>
                  </div>
                </div>

                <div className="flex items-center gap-2.5 bg-slate-900/60 p-2.5 rounded-lg border border-slate-800">
                  <span className="w-6 h-6 rounded-full bg-rose-500 border-2 border-rose-300 text-white font-bold text-[11px] flex items-center justify-center font-mono shrink-0">
                    {String.fromCharCode(65 + Math.min(25, Math.max(1, sortedObservations.length - 1)))}
                  </span>
                  <div>
                    <div className="font-semibold text-rose-300">Final Observation</div>
                    <div className="text-[10px] text-slate-400">Latest recorded observation</div>
                  </div>
                </div>

                <div className="flex items-center gap-2.5 bg-slate-900/60 p-2.5 rounded-lg border border-slate-800">
                  <div className="w-6 h-0.5 border-t-2 border-dashed border-cyan-400 shrink-0"></div>
                  <div>
                    <div className="font-semibold text-white">Visual Connection</div>
                    <div className="text-[10px] text-slate-400">Not continuous GPS tracking</div>
                  </div>
                </div>
              </div>
            ) : (
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs text-slate-300">
                <div className="flex items-center gap-2.5 bg-slate-900/60 p-2.5 rounded-lg border border-slate-800">
                  <span className="w-6 h-6 rounded-full bg-emerald-500 border-2 border-emerald-300 text-white font-bold text-[11px] flex items-center justify-center font-mono shrink-0">
                    1
                  </span>
                  <div>
                    <div className="font-semibold text-white">Start Anchor</div>
                    <div className="text-[10px] text-slate-400">First recorded point</div>
                  </div>
                </div>

                <div className="flex items-center gap-2.5 bg-slate-900/60 p-2.5 rounded-lg border border-slate-800">
                  <span className="w-6 h-6 rounded-full bg-slate-700 border-2 border-amber-400 text-amber-300 font-bold text-[11px] flex items-center justify-center font-mono shrink-0">
                    ~
                  </span>
                  <div>
                    <div className="font-semibold text-amber-300">Stationary / Drift</div>
                    <div className="text-[10px] text-slate-400">Within GPS uncertainty</div>
                  </div>
                </div>

                <div className="flex items-center gap-2.5 bg-slate-900/60 p-2.5 rounded-lg border border-slate-800">
                  <span className="w-6 h-6 rounded-full bg-cyan-500 border-2 border-cyan-300 text-white font-bold text-[11px] flex items-center justify-center font-mono shrink-0">
                    {sortedObservations.length > 1 ? sortedObservations.length : 'N'}
                  </span>
                  <div>
                    <div className="font-semibold text-white">Confirmed Movement</div>
                    <div className="text-[10px] text-slate-400">Verified displacement</div>
                  </div>
                </div>

                <div className="flex items-center gap-2.5 bg-slate-900/60 p-2.5 rounded-lg border border-slate-800">
                  <div className="w-6 h-0.5 border-t-2 border-dashed border-cyan-400 shrink-0"></div>
                  <div>
                    <div className="font-semibold text-white">Connecting Line</div>
                    <div className="text-[10px] text-slate-400">Connection (not tracking)</div>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Right: Synchronized Interactive Timeline (4 Cols) */}
        <div className="lg:col-span-4 space-y-3">
          <div className="glass-panel p-4 rounded-2xl border border-slate-800">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <div className="flex items-center gap-2 text-sm font-bold text-white">
                <Clock className="w-4 h-4 text-cyan-400" />
                <span>Chronological Timeline</span>
              </div>
              <span className="text-xs text-slate-400 font-mono">
                {sortedObservations.length} Records
              </span>
            </div>

            {/* Timeline Scrollable Container */}
            <div 
              ref={timelineRef}
              className="mt-3 space-y-2.5 max-h-[580px] overflow-y-auto pr-1"
            >
              {sortedObservations.length > 0 ? (
                sortedObservations.map((obs, idx) => {
                  const isSelected = obs.id === selectedPointId;
                  const isStart = idx === 0;
                  const isEnd = idx === sortedObservations.length - 1 && sortedObservations.length > 1;
                  const obsNum = obs.observation_number || (idx + 1);
                  const timeFormatted = new Date(obs.recorded_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

                  return (
                    <div
                      key={obs.id}
                      id={`timeline-item-${obs.id}`}
                      onClick={() => handleSelectObservation(obs)}
                      className={`
                        p-3 rounded-xl border transition-all duration-200 cursor-pointer text-xs
                        ${isSelected 
                          ? 'bg-cyan-500/15 border-cyan-500/50 shadow-lg shadow-cyan-500/10' 
                          : 'bg-slate-900/80 border-slate-800/80 hover:bg-slate-900 hover:border-slate-700'
                        }
                      `}
                    >
                      <div className="flex items-center justify-between gap-2">
                        <div className="flex items-center gap-2">
                          <span className={`
                            w-6 h-6 rounded-full font-bold text-[11px] flex items-center justify-center font-mono
                            ${isOfficerMode
                              ? isStart 
                                ? 'bg-emerald-500 text-white' 
                                : isEnd 
                                ? 'bg-rose-500 text-white' 
                                : 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/40'
                              : isStart 
                              ? 'bg-emerald-500 text-white' 
                              : isEnd 
                              ? 'bg-rose-500 text-white' 
                              : obs.source === 'STATIC_ADMIN_LOCATION'
                              ? 'bg-amber-500 text-white'
                              : obs.is_stationary_drift
                              ? 'bg-slate-700 text-amber-300 border border-amber-400'
                              : 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/40'
                            }
                          `}>
                            {isOfficerMode ? String.fromCharCode(65 + (idx % 26)) : obsNum}
                          </span>
                          <span className="font-bold text-white font-mono text-sm">
                            {timeFormatted}
                          </span>
                          {isOfficerMode ? (
                            <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded border ${
                              isStart 
                                ? 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20' 
                                : isEnd 
                                ? 'text-rose-400 bg-rose-500/10 border-rose-500/20' 
                                : 'text-cyan-400 bg-cyan-500/10 border-cyan-500/20'
                            }`}>
                              {isStart ? 'START' : isEnd ? 'LATEST' : 'WAYPOINT'}
                            </span>
                          ) : (
                            <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded border ${
                              obs.is_stationary_drift
                                ? 'text-amber-300 bg-amber-500/10 border-amber-500/30'
                                : isStart 
                                ? 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20'
                                : isEnd 
                                ? 'text-rose-400 bg-rose-500/10 border-rose-500/20'
                                : obs.source === 'STATIC_ADMIN_LOCATION'
                                ? 'text-amber-400 bg-amber-500/10 border-amber-500/20'
                                : 'text-cyan-400 bg-cyan-500/10 border-cyan-500/20'
                            }`}>
                              {obs.is_stationary_drift ? 'Stationary Drift' : isStart ? 'Start' : isEnd ? 'Latest' : obs.source === 'STATIC_ADMIN_LOCATION' ? 'Admin Centroid' : 'Movement'}
                            </span>
                          )}
                        </div>

                        {/* Source Tag Badge */}
                        <span className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded border ${
                          obs.source === 'PATIENT_GPS' 
                            ? 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30'
                            : obs.source === 'STATIC_ADMIN_LOCATION'
                            ? 'bg-amber-500/15 text-amber-300 border-amber-500/30'
                            : 'bg-indigo-500/15 text-indigo-300 border-indigo-500/30'
                        }`}>
                          {obs.source === 'PATIENT_GPS' ? 'REAL GPS' : obs.source === 'STATIC_ADMIN_LOCATION' ? 'NO PHONE' : obs.source}
                        </span>
                      </div>

                      <div className="mt-2 text-[11px] text-slate-400 font-mono flex items-center justify-between border-t border-slate-800/60 pt-1.5">
                        <span className="flex items-center gap-1">
                          <MapPin className="w-3 h-3 text-cyan-400" />
                          <span>{obs.latitude.toFixed(6)}, {obs.longitude.toFixed(6)}</span>
                        </span>
                        <span className="text-slate-500">
                          {obs.accuracy ? `±${obs.accuracy}m` : (obs.source === 'STATIC_ADMIN_LOCATION' ? 'Centroid' : 'Acc: N/A')}
                        </span>
                      </div>
                    </div>
                  );
                })
              ) : (
                <div className="text-center py-12 text-slate-400 text-xs px-4">
                  {!isPatientUser && !selectedPseudoId 
                    ? "Please select a patient from the dropdown above to inspect their movement roadmap."
                    : "No recorded location observations available."}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
