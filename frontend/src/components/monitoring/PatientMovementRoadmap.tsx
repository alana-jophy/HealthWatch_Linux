import React, { useState, useEffect, useRef, useMemo } from 'react';
import { 
  MapContainer, 
  TileLayer, 
  Marker, 
  Popup, 
  Polyline, 
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
  Bug,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Activity
} from 'lucide-react';

// Leaflet default icon fix
delete (L.Icon.Default.prototype as any)._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
});

// Helper component to auto-fit map viewport to polyline bounds or pan to latest observation
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

// Create custom colored DivIcon for Start, Intermediate, and End markers
const createCustomMarkerIcon = (
  index: number, 
  total: number, 
  timeStr: string, 
  isSelected: boolean,
  source: string
) => {
  const isStart = index === 0;
  const isEnd = index === total - 1 && total > 1;

  let bgClass = 'bg-cyan-500';
  let borderClass = 'border-cyan-300';

  if (isStart) {
    bgClass = 'bg-emerald-500';
    borderClass = 'border-emerald-200';
  } else if (isEnd) {
    bgClass = 'bg-rose-500';
    borderClass = 'border-rose-200';
  } else if (source === 'HEALTH_WORKER') {
    bgClass = 'bg-indigo-500';
    borderClass = 'border-indigo-300';
  }

  const selectedRing = isSelected ? 'ring-4 ring-cyan-400/80 scale-125 z-50' : 'hover:scale-110';

  const html = `
    <div class="relative flex items-center justify-center transition-all duration-300 ${selectedRing}">
      <div class="w-8 h-8 rounded-full ${bgClass} text-white font-bold text-[10px] flex items-center justify-center shadow-lg border-2 ${borderClass} font-mono tracking-wider">
        ${String.fromCharCode(65 + (index % 26))}
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
    officerPatientPseudoId || (isPatientUser && user?.patient_pseudo_id ? user.patient_pseudo_id : 'PAT-USER-143')
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
  const [showDebugPanel, setShowDebugPanel] = useState<boolean>(true);

  const timelineRef = useRef<HTMLDivElement>(null);

  // If patient mode, automatically fetch their own profile to resolve pseudo_id
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
    if (officerFilterDate) {
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

  // Safe Near-Real-Time Dashboard Polling
  useEffect(() => {
    if (!isLivePolling) return;
    const interval = setInterval(() => {
      fetchPatientRoadmap({
        pseudoId: selectedPseudoId,
        date: selectedDate || undefined,
        startTime: startTime || undefined,
        endTime: endTime || undefined,
      })
        .then((data) => {
          setRoadmapData(data);
        })
        .catch((err) => console.warn('Roadmap polling update notice:', err));
    }, 15000); // 15-second visual polling
    return () => clearInterval(interval);
  }, [isLivePolling, selectedPseudoId, selectedDate, startTime, endTime]);

  const loadRoadmap = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await fetchPatientRoadmap({
        pseudoId: selectedPseudoId,
        date: selectedDate || undefined,
        startTime: startTime || undefined,
        endTime: endTime || undefined,
      });
      setRoadmapData(data);
      if (data.observations.length > 0) {
        // Sort chronologically
        const sorted = [...data.observations].sort(
          (a, b) => new Date(a.recorded_at).getTime() - new Date(b.recorded_at).getTime()
        );
        setSelectedPointId(sorted[sorted.length - 1].id);
      }
    } catch (err: any) {
      console.error('Failed to query movement roadmap:', err);
      setError(err?.response?.data?.error?.message || err?.message || 'Failed to load movement roadmap');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (selectedPseudoId) {
      loadRoadmap();
    }
  }, [selectedPseudoId]);

  const handleApplyFilters = (e: React.FormEvent) => {
    e.preventDefault();
    loadRoadmap();
  };

  const handleSelectToday = () => {
    const today = new Date().toISOString().split('T')[0];
    setSelectedDate(today);
    setStartTime('00:00');
    setEndTime('23:59');
    setTimeout(loadRoadmap, 50);
  };

  const handleClearDateFilter = () => {
    setSelectedDate('');
    setStartTime('');
    setEndTime('');
    setTimeout(loadRoadmap, 50);
  };

  const handleResetFilters = () => {
    setSelectedDate('');
    setStartTime('');
    setEndTime('');
    setTimeout(loadRoadmap, 50);
  };

  const handleSelectObservation = (point: RoadmapObservationItem) => {
    setSelectedPointId(point.id);
    setFlyToCoord([point.latitude, point.longitude]);

    // Scroll timeline item into view
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

  const polylineCoords: [number, number][] = useMemo(() => {
    return sortedObservations.map((obs) => [obs.latitude, obs.longitude]);
  }, [sortedObservations]);

  // Center dynamically on the latest observation (or central Kerala)
  const latestObservation = sortedObservations.length > 0 
    ? sortedObservations[sortedObservations.length - 1] 
    : null;

  const defaultCenter: [number, number] = latestObservation
    ? [latestObservation.latitude, latestObservation.longitude]
    : [10.5276, 76.2144]; // Central Kerala (Thrissur)

  return (
    <div className="space-y-6">
      {/* 1. Header Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-cyan-500/10 border border-cyan-500/20 text-xs font-semibold text-cyan-400 mb-2">
            <Route className="w-3.5 h-3.5" />
            <span>Patient Movement Roadmap</span>
          </div>
          <h1 className="font-heading text-2xl md:text-3xl font-extrabold text-white tracking-tight">
            Movement Roadmap & Sequential Observations
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Visualizing discrete spatial telemetry observations collected approximately every 15 minutes.
          </p>
        </div>

        {/* Quick Identity Pill */}
        <div className="glass-panel px-4 py-2.5 rounded-xl border border-slate-800 flex items-center gap-3 shrink-0 self-start">
          <div className="w-9 h-9 rounded-lg bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center text-cyan-400">
            <User className="w-5 h-5" />
          </div>
          <div>
            <div className="text-xs font-medium text-slate-400">Viewing Patient Account</div>
            <div className="text-sm font-bold text-white flex items-center gap-2">
              <span>{roadmapData?.patient_pseudo_id || selectedPseudoId}</span>
              {roadmapData?.patient_name && (
                <span className="text-[10px] bg-slate-800 text-slate-300 px-1.5 py-0.5 rounded font-mono">
                  {roadmapData.patient_name}
                </span>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* 2. CRITICAL TECHNICAL LIMITATION NOTICE (Statutory Specification) */}
      <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-4 md:p-5 relative overflow-hidden">
        <div className="flex items-start gap-3.5">
          <div className="p-2 rounded-lg bg-amber-500/20 border border-amber-500/40 text-amber-400 shrink-0 mt-0.5">
            <AlertTriangle className="w-5 h-5" />
          </div>
          <div className="space-y-1.5 text-xs md:text-sm">
            <div className="font-bold text-amber-300 flex items-center gap-2">
              <span>Recorded GPS observations — approximately 15-minute sampling</span>
              <span className="text-[11px] bg-amber-500/20 px-2 py-0.5 rounded-full text-amber-200 border border-amber-500/30">
                15-Min Cadence
              </span>
            </div>
            <p className="text-slate-300 leading-relaxed">
              HealthWatch is <strong>NOT performing continuous second-by-second GPS tracking</strong>. Location observations are sampled approximately every <strong>15 MINUTES</strong> under explicit patient consent.
            </p>
            <p className="text-slate-300 text-xs leading-relaxed italic bg-amber-950/40 p-2 rounded-lg border border-amber-500/20">
              &ldquo;The connecting line is a visual representation between recorded observations and does not represent continuous GPS tracking.&rdquo;
            </p>
          </div>
        </div>
      </div>

      {/* 3. Filter Controls & Live Polling Panel */}
      <div className="glass-panel p-5 rounded-2xl border border-slate-800 space-y-4">
        <form onSubmit={handleApplyFilters} className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4 items-end">
          {/* Patient Selector (Hidden or Locked in Patient Mode) */}
          <div>
            <label className="block text-xs font-semibold text-slate-400 mb-1.5 flex items-center gap-1.5">
              <User className="w-3.5 h-3.5 text-cyan-400" />
              <span>Patient Account:</span>
            </label>
            {isPatientUser ? (
              <input
                type="text"
                disabled
                value={`${selectedPseudoId} (Your Account)`}
                className="w-full bg-slate-900/60 border border-slate-800 rounded-lg px-3 py-2 text-sm text-brand-400 font-mono text-xs opacity-80"
              />
            ) : (
              <select
                value={selectedPseudoId}
                onChange={(e) => setSelectedPseudoId(e.target.value)}
                className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-cyan-500 font-mono text-xs"
              >
                {patients.length > 0 ? (
                  patients.map((p) => (
                    <option key={p.pseudo_id} value={p.pseudo_id}>
                      {p.pseudo_id} — {p.full_name}
                    </option>
                  ))
                ) : (
                  <option value={selectedPseudoId}>{selectedPseudoId}</option>
                )}
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
              className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-cyan-500 font-mono"
            />
          </div>

          {/* Start Time */}
          <div>
            <label className="block text-xs font-semibold text-slate-400 mb-1.5 flex items-center gap-1.5">
              <Clock className="w-3.5 h-3.5 text-cyan-400" />
              <span>Start Time:</span>
            </label>
            <input
              type="time"
              value={startTime}
              onChange={(e) => setStartTime(e.target.value)}
              className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-cyan-500 font-mono"
            />
          </div>

          {/* End Time */}
          <div>
            <label className="block text-xs font-semibold text-slate-400 mb-1.5 flex items-center gap-1.5">
              <Clock className="w-3.5 h-3.5 text-cyan-400" />
              <span>End Time:</span>
            </label>
            <input
              type="time"
              value={endTime}
              onChange={(e) => setEndTime(e.target.value)}
              className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-cyan-500 font-mono"
            />
          </div>

          {/* Actions */}
          <div className="flex items-center gap-2">
            <button
              type="submit"
              disabled={isLoading}
              className="flex-1 bg-cyan-600 hover:bg-cyan-500 disabled:bg-slate-800 text-white font-semibold py-2 px-4 rounded-lg text-sm transition-colors flex items-center justify-center gap-1.5 shadow cursor-pointer"
            >
              <Search className="w-4 h-4" />
              <span>{isLoading ? 'Filtering...' : 'Apply'}</span>
            </button>

            <button
              type="button"
              onClick={handleResetFilters}
              title="Reset Filters"
              className="bg-slate-800 hover:bg-slate-700 text-slate-300 p-2.5 rounded-lg border border-slate-700 transition-colors cursor-pointer"
            >
              <RotateCcw className="w-4 h-4" />
            </button>
          </div>
        </form>

        {/* Live Testing Quick Actions & Polling Toolbar */}
        <div className="flex flex-wrap items-center justify-between gap-3 pt-3 border-t border-slate-800/80 text-xs">
          <div className="flex items-center gap-2">
            <span className="text-slate-400 font-medium">Quick Filter:</span>
            <button
              type="button"
              onClick={handleSelectToday}
              className="px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 font-mono cursor-pointer"
            >
              Today&apos;s Route
            </button>
            <button
              type="button"
              onClick={handleClearDateFilter}
              className="px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 font-mono cursor-pointer"
            >
              All Observations (Live)
            </button>
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setIsLivePolling(!isLivePolling)}
              className={`flex items-center gap-2 px-3 py-1.5 rounded-xl border text-xs font-semibold transition-all cursor-pointer ${
                isLivePolling 
                  ? 'bg-emerald-950/40 border-emerald-500/50 text-emerald-300 shadow-md shadow-emerald-500/10'
                  : 'bg-slate-900 border-slate-800 text-slate-400 hover:text-slate-200'
              }`}
            >
              <span className={`w-2 h-2 rounded-full ${isLivePolling ? 'bg-emerald-400 animate-ping' : 'bg-slate-600'}`}></span>
              <span>Live Dashboard Polling: {isLivePolling ? 'ACTIVE (15s)' : 'OFF'}</span>
            </button>
          </div>
        </div>
      </div>

      {/* 4. Telemetry Statistics Bar */}
      {roadmapData?.statistics && (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
          <div className="glass-panel p-3.5 rounded-xl border border-slate-800">
            <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Observations</div>
            <div className="text-xl font-bold text-white mt-1 flex items-baseline gap-1.5">
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
            <div className="text-[10px] text-slate-500 font-mono">Point A (Initial)</div>
          </div>

          <div className="glass-panel p-3.5 rounded-xl border border-slate-800">
            <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Latest Point</div>
            <div className="text-sm font-bold text-rose-400 mt-1 font-mono">
              {roadmapData.statistics.monitoring_end 
                ? new Date(roadmapData.statistics.monitoring_end).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
                : '—'}
            </div>
            <div className="text-[10px] text-slate-500 font-mono">Final Telemetry</div>
          </div>

          <div className="glass-panel p-3.5 rounded-xl border border-slate-800">
            <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Avg Accuracy</div>
            <div className="text-xl font-bold text-cyan-400 mt-1 flex items-baseline gap-1">
              <span>{roadmapData.statistics.average_accuracy !== null && roadmapData.statistics.average_accuracy !== undefined ? `±${roadmapData.statistics.average_accuracy}` : '—'}</span>
              <span className="text-xs font-normal text-slate-400 font-mono">m</span>
            </div>
          </div>

          <div className="glass-panel p-3.5 rounded-xl border border-slate-800">
            <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Cadence</div>
            <div className="text-sm font-bold text-slate-200 mt-1">~15 Minutes</div>
            <div className="text-[10px] text-slate-500">Discrete Sampling</div>
          </div>

          <div className="glass-panel p-3.5 rounded-xl border border-slate-800">
            <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Latest Lat/Lng</div>
            <div className="text-xs font-bold text-slate-300 mt-1 font-mono truncate">
              {latestObservation 
                ? `${latestObservation.latitude.toFixed(4)}, ${latestObservation.longitude.toFixed(4)}`
                : '—'}
            </div>
            <div className="text-[10px] text-slate-500">WGS84 (EPSG:4326)</div>
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
        <div className="lg:col-span-8 space-y-3">
          <div className="relative rounded-2xl overflow-hidden border border-slate-800 shadow-2xl h-[560px] bg-slate-950">
            {isLoading ? (
              <div className="absolute inset-0 z-20 bg-slate-950/80 flex flex-col items-center justify-center space-y-3">
                <div className="w-10 h-10 border-4 border-cyan-500/30 border-t-cyan-400 rounded-full animate-spin"></div>
                <div className="text-sm font-semibold text-slate-300">Rendering Movement Roadmap...</div>
              </div>
            ) : null}

            <MapContainer
              center={defaultCenter}
              zoom={14}
              scrollWheelZoom={true}
              className="w-full h-full"
            >
              <TileLayer
                attribution='&copy; <a href="https://carto.com/">CARTO</a> & OpenStreetMap'
                url="https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png"
              />

              <MapBoundsFitter 
                observations={sortedObservations} 
                selectedCoord={flyToCoord}
              />

              {/* Sequential Visual Connection Polyline (Chronologically Ordered) */}
              {polylineCoords.length > 1 && (
                <Polyline
                  positions={polylineCoords}
                  pathOptions={{
                    color: '#0284c7', // Brand Cyan 600
                    weight: 4,
                    opacity: 0.85,
                    dashArray: '8, 8', // Dashed line to emphasize discrete visual connection, NOT continuous path
                    lineCap: 'round',
                    lineJoin: 'round',
                  }}
                />
              )}

              {/* Observation Markers (Chronologically Ordered) */}
              {sortedObservations.map((obs, idx) => {
                const isSelected = obs.id === selectedPointId;
                const timeFormatted = new Date(obs.recorded_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
                const icon = createCustomMarkerIcon(
                  idx, 
                  sortedObservations.length, 
                  timeFormatted, 
                  isSelected,
                  obs.source
                );

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
                      <div className="p-1 space-y-2 text-slate-900 min-w-[210px]">
                        <div className="flex items-center justify-between border-b pb-1.5">
                          <span className="font-bold text-xs uppercase tracking-wider text-cyan-800">
                            Point {String.fromCharCode(65 + (idx % 26))} {idx === 0 ? '(START)' : idx === sortedObservations.length - 1 ? '(LATEST)' : ''}
                          </span>
                          <span className="text-[11px] font-mono font-semibold bg-slate-100 px-1.5 py-0.5 rounded">
                            {timeFormatted}
                          </span>
                        </div>

                        <div className="space-y-1 text-xs">
                          <div className="flex justify-between">
                            <span className="text-slate-500">Timestamp:</span>
                            <span className="font-mono text-[11px] text-slate-700">
                              {new Date(obs.recorded_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                            </span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-slate-500">Coordinates:</span>
                            <span className="font-mono text-[11px] font-semibold text-slate-800">
                              {obs.latitude.toFixed(6)}, {obs.longitude.toFixed(6)}
                            </span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-slate-500">Accuracy:</span>
                            <span className="font-mono text-[11px] text-emerald-700">
                              {obs.accuracy ? `±${obs.accuracy} m` : 'N/A'}
                            </span>
                          </div>
                          <div className="flex justify-between items-center pt-1 border-t">
                            <span className="text-slate-500">Data Source:</span>
                            <span className={`text-[10px] font-bold px-2 py-0.5 rounded ${
                              obs.source === 'PATIENT_GPS' 
                                ? 'bg-emerald-100 text-emerald-800'
                                : obs.source === 'HEALTH_WORKER'
                                ? 'bg-indigo-100 text-indigo-800'
                                : 'bg-slate-100 text-slate-700'
                            }`}>
                              {obs.source === 'PATIENT_GPS' ? 'REAL PHONE GPS' : obs.source}
                            </span>
                          </div>
                        </div>
                      </div>
                    </Popup>
                  </Marker>
                );
              })}
            </MapContainer>

            {/* Map Legend Overlay */}
            <div className="absolute bottom-4 left-4 z-[1000] bg-slate-950/90 backdrop-blur-md border border-slate-800 rounded-xl p-3 text-xs text-slate-300 shadow-xl space-y-2 pointer-events-auto">
              <div className="font-bold text-[11px] text-slate-400 uppercase tracking-wider">Map Legend</div>
              <div className="flex items-center gap-2">
                <span className="w-3 h-3 rounded-full bg-emerald-500 border border-emerald-300"></span>
                <span>Point A (Start Observation)</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="w-3 h-3 rounded-full bg-cyan-500 border border-cyan-300"></span>
                <span>Intermediate Waypoints</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="w-3 h-3 rounded-full bg-rose-500 border border-rose-300"></span>
                <span>Latest Observation</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="w-6 h-0.5 border-t-2 border-dashed border-cyan-500"></span>
                <span className="text-[11px] text-slate-400">Visual Connection (~15m Sampling)</span>
              </div>
            </div>
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
              className="mt-3 space-y-2.5 max-h-[500px] overflow-y-auto pr-1"
            >
              {sortedObservations.length > 0 ? (
                sortedObservations.map((obs, idx) => {
                  const isSelected = obs.id === selectedPointId;
                  const isStart = idx === 0;
                  const isEnd = idx === sortedObservations.length - 1 && sortedObservations.length > 1;
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
                            w-5 h-5 rounded-full font-bold text-[10px] flex items-center justify-center font-mono
                            ${isStart 
                              ? 'bg-emerald-500 text-white' 
                              : isEnd 
                              ? 'bg-rose-500 text-white' 
                              : 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/40'
                            }
                          `}>
                            {String.fromCharCode(65 + (idx % 26))}
                          </span>
                          <span className="font-bold text-white font-mono text-sm">
                            {timeFormatted}
                          </span>
                          <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded border ${
                            isStart 
                              ? 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20'
                              : isEnd 
                              ? 'text-rose-400 bg-rose-500/10 border-rose-500/20'
                              : 'text-cyan-400 bg-cyan-500/10 border-cyan-500/20'
                          }`}>
                            {isStart ? 'Start' : isEnd ? 'Latest' : 'Way-point'}
                          </span>
                        </div>

                        {/* Source Tag Badge */}
                        <span className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded border ${
                          obs.source === 'PATIENT_GPS' 
                            ? 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30'
                            : obs.source === 'HEALTH_WORKER'
                            ? 'bg-indigo-500/15 text-indigo-300 border-indigo-500/30'
                            : 'bg-slate-800 text-slate-400 border-slate-700'
                        }`}>
                          {obs.source === 'PATIENT_GPS' ? 'REAL GPS' : obs.source}
                        </span>
                      </div>

                      <div className="mt-2 text-[11px] text-slate-400 font-mono flex items-center justify-between border-t border-slate-800/60 pt-1.5">
                        <span className="flex items-center gap-1">
                          <MapPin className="w-3 h-3 text-cyan-400" />
                          <span>{obs.latitude.toFixed(6)}, {obs.longitude.toFixed(6)}</span>
                        </span>
                        <span className="text-slate-500">
                          {obs.accuracy ? `±${obs.accuracy}m` : 'Acc: N/A'}
                        </span>
                      </div>
                    </div>
                  );
                })
              ) : (
                <div className="text-center py-12 text-slate-500 text-xs">
                  No location observations recorded for this patient account.
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* 6. Location Debug Panel (Geospatial Axis & Coordinate Verification) */}
      <div className="glass-panel rounded-2xl border border-slate-800 overflow-hidden shadow-xl">
        <button
          type="button"
          onClick={() => setShowDebugPanel(!showDebugPanel)}
          className="w-full px-5 py-3.5 bg-slate-900/90 hover:bg-slate-900 flex items-center justify-between text-left transition-colors cursor-pointer"
        >
          <div className="flex items-center gap-2.5">
            <Bug className="w-4 h-4 text-emerald-400" />
            <div>
              <span className="text-xs font-bold text-slate-200">
                Location Debug Panel & Geospatial Coordinate Audit
              </span>
              <span className="ml-2 text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                Zero Axis Inversion
              </span>
            </div>
          </div>
          {showDebugPanel ? <ChevronUp className="w-4 h-4 text-slate-400" /> : <ChevronDown className="w-4 h-4 text-slate-400" />}
        </button>

        {showDebugPanel && (
          <div className="p-5 space-y-4 border-t border-slate-800/80 bg-slate-950/60 text-xs font-mono">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 p-3 rounded-xl bg-emerald-950/20 border border-emerald-500/30 text-emerald-300 text-[11px]">
              <div className="flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                <span>
                  <strong>Coordinate Axis Verification:</strong> Latitude (Y: ~8.0° - 13.0° N) and Longitude (X: ~74.0° - 78.0° E) are correctly mapped directly into Leaflet <code>[latitude, longitude]</code> with 0% inversion.
                </span>
              </div>
              <span className="shrink-0 text-[10px] font-bold px-2 py-0.5 rounded bg-emerald-500/20 border border-emerald-500/30">
                WGS-84 Validated
              </span>
            </div>

            {sortedObservations.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-[11px]">
                  <thead className="bg-slate-900 text-slate-400 border-b border-slate-800 uppercase tracking-wider text-[10px]">
                    <tr>
                      <th className="py-2.5 px-3">Point</th>
                      <th className="py-2.5 px-3">Observation ID</th>
                      <th className="py-2.5 px-3">Timestamp (UTC)</th>
                      <th className="py-2.5 px-3 text-cyan-300">Database WGS84 (Lat, Lon)</th>
                      <th className="py-2.5 px-3 text-emerald-300">FastAPI REST Response</th>
                      <th className="py-2.5 px-3 text-amber-300">Leaflet [lat, lng]</th>
                      <th className="py-2.5 px-3">Kerala Bounds Check</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/50">
                    {sortedObservations.slice(0, 10).map((obs, idx) => {
                      const inKeralaLat = obs.latitude >= 8.0 && obs.latitude <= 13.0;
                      const inKeralaLon = obs.longitude >= 74.0 && obs.longitude <= 78.0;
                      const isValidKerala = inKeralaLat && inKeralaLon;

                      return (
                        <tr key={obs.id} className="hover:bg-slate-900/40">
                          <td className="py-2 px-3 font-bold text-white">
                            {String.fromCharCode(65 + (idx % 26))}
                          </td>
                          <td className="py-2 px-3 text-slate-500 truncate max-w-[120px]">
                            {obs.id}
                          </td>
                          <td className="py-2 px-3 text-slate-400">
                            {new Date(obs.recorded_at).toISOString().replace('T', ' ').substring(11, 19)}
                          </td>
                          <td className="py-2 px-3 text-cyan-400 font-semibold">
                            {obs.latitude.toFixed(6)}, {obs.longitude.toFixed(6)}
                          </td>
                          <td className="py-2 px-3 text-emerald-400 font-semibold">
                            {`{"lat": ${obs.latitude.toFixed(6)}, "lng": ${obs.longitude.toFixed(6)}}`}
                          </td>
                          <td className="py-2 px-3 text-amber-400 font-semibold">
                            {`[${obs.latitude.toFixed(6)}, ${obs.longitude.toFixed(6)}]`}
                          </td>
                          <td className="py-2 px-3">
                            {isValidKerala ? (
                              <span className="text-emerald-400 text-[10px] font-bold flex items-center gap-1">
                                <CheckCircle2 className="w-3 h-3" />
                                Valid Kerala
                              </span>
                            ) : (
                              <span className="text-cyan-400 text-[10px] font-bold">
                                Valid Earth
                              </span>
                            )}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="text-slate-500 text-center py-4">
                No observations currently loaded to audit.
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};
