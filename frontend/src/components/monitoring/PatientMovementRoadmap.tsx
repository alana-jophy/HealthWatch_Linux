import React, { useState, useEffect, useRef } from 'react';
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
  fetchPatientsList
} from '../../services/api';
import { 
  PatientRoadmapResponse, 
  RoadmapObservationItem,
  PatientProfile
} from '../../types';
import { 
  Route, 
  AlertTriangle, 
  Clock, 
  Calendar, 
  Search, 
  RotateCcw, 
  MapPin, 
  User
} from 'lucide-react';

// Leaflet default icon fix
delete (L.Icon.Default.prototype as any)._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
});

// Helper component to auto-fit map viewport to polyline bounds
const MapBoundsFitter: React.FC<{ observations: RoadmapObservationItem[]; selectedCoord?: [number, number] | null }> = ({
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
        ${String.fromCharCode(65 + index)}
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
  // Filters State
  const [selectedPseudoId, setSelectedPseudoId] = useState<string>(officerPatientPseudoId || 'PAT-SYNTH-101');
  const [selectedDate, setSelectedDate] = useState<string>(officerFilterDate || '2026-09-05');
  const [startTime, setStartTime] = useState<string>('09:00');
  const [endTime, setEndTime] = useState<string>('18:00');

  useEffect(() => {
    if (officerPatientPseudoId) {
      setSelectedPseudoId(officerPatientPseudoId);
    }
    if (officerFilterDate) {
      setSelectedDate(officerFilterDate);
    }
  }, [officerPatientPseudoId, officerFilterDate]);

  // Roadmap Data & State
  const [patients, setPatients] = useState<{ pseudo_id: string; full_name: string }[]>([]);
  const [roadmapData, setRoadmapData] = useState<PatientRoadmapResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedPointId, setSelectedPointId] = useState<string | null>(null);
  const [flyToCoord, setFlyToCoord] = useState<[number, number] | null>(null);

  const timelineRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fetchPatientsList()
      .then((res) => {
        if (res?.items) {
          setPatients(res.items.map((p) => ({ pseudo_id: p.pseudo_id, full_name: p.full_name })));
        }
      })
      .catch((err) => {
        console.warn('Could not load patient registry for roadmap selector:', err);
      });
  }, []);

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
        setSelectedPointId(data.observations[0].id);
      }
    } catch (err: any) {
      console.error('Failed to query movement roadmap:', err);
      setError(err?.response?.data?.error?.message || err?.message || 'Failed to load movement roadmap');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadRoadmap();
  }, [selectedPseudoId]);

  const handleApplyFilters = (e: React.FormEvent) => {
    e.preventDefault();
    loadRoadmap();
  };

  const handleResetFilters = () => {
    setSelectedDate('2026-09-05');
    setStartTime('09:00');
    setEndTime('18:00');
    setSelectedPseudoId('PAT-SYNTH-101');
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

  const polylineCoords: [number, number][] = roadmapData?.observations?.map(
    (obs) => [obs.latitude, obs.longitude]
  ) || [];

  const defaultCenter: [number, number] = polylineCoords.length > 0
    ? polylineCoords[0]
    : [8.5241, 76.9366]; // Thiruvananthapuram center

  return (
    <div className="space-y-6">
      {/* 1. Header Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-cyan-500/10 border border-cyan-500/20 text-xs font-semibold text-cyan-400 mb-2">
            <Route className="w-3.5 h-3.5" />
            <span>Step 12: Patient Movement Roadmap</span>
          </div>
          <h1 className="font-heading text-2xl md:text-3xl font-extrabold text-white tracking-tight">
            Patient Movement Roadmap & Sequential Observation Stream
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Visualizing authorized discrete spatial telemetry observations collected approximately every 15 minutes.
          </p>
        </div>

        {/* Quick Identity Pill */}
        <div className="glass-panel px-4 py-2.5 rounded-xl border border-slate-800 flex items-center gap-3 shrink-0 self-start">
          <div className="w-9 h-9 rounded-lg bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center text-cyan-400">
            <User className="w-5 h-5" />
          </div>
          <div>
            <div className="text-xs font-medium text-slate-400">Viewing Patient</div>
            <div className="text-sm font-bold text-white flex items-center gap-2">
              <span>{roadmapData?.patient_pseudo_id || selectedPseudoId}</span>
              <span className="text-[10px] bg-slate-800 text-slate-300 px-1.5 py-0.5 rounded font-mono">
                {roadmapData?.patient_name || 'Synthetic Patient'}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* 2. CRITICAL TECHNICAL LIMITATION NOTICE (Mandatory Prompt Requirement) */}
      <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-4 md:p-5 relative overflow-hidden">
        <div className="flex items-start gap-3.5">
          <div className="p-2 rounded-lg bg-amber-500/20 border border-amber-500/40 text-amber-400 shrink-0 mt-0.5">
            <AlertTriangle className="w-5 h-5" />
          </div>
          <div className="space-y-1.5 text-xs md:text-sm">
            <div className="font-bold text-amber-300 flex items-center gap-2">
              <span>IMPORTANT TECHNICAL SPECIFICATION & PRIVACY CLARIFICATION</span>
              <span className="text-[11px] bg-amber-500/20 px-2 py-0.5 rounded-full text-amber-200 border border-amber-500/30">
                15-Minute Cadence
              </span>
            </div>
            <p className="text-slate-300 leading-relaxed">
              HealthWatch is <strong>NOT performing continuous second-by-second GPS tracking</strong>. Location observations are sampled approximately every <strong>15 MINUTES</strong> under explicit patient consent.
            </p>
            <p className="text-slate-400 text-xs leading-relaxed">
              Therefore, the roadmap represents <em>“Recorded location observations”</em>, <strong>NOT</strong> <em>“Exact continuous movement”</em>. The line connecting observations is strictly a <strong>chronological visual connection</strong>. HealthWatch makes no claim that the patient travelled along that exact physical path between observations.
            </p>
          </div>
        </div>
      </div>

      {/* 3. Filter Controls Panel */}
      <div className="glass-panel p-5 rounded-2xl border border-slate-800">
        <form onSubmit={handleApplyFilters} className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4 items-end">
          {/* Patient Selector */}
          <div>
            <label className="block text-xs font-semibold text-slate-400 mb-1.5 flex items-center gap-1.5">
              <User className="w-3.5 h-3.5 text-cyan-400" />
              <span>Select Patient:</span>
            </label>
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
                <>
                  <option value="PAT-SYNTH-101">PAT-SYNTH-101 — Synthetic Patient 101</option>
                  <option value="PAT-SYNTH-102">PAT-SYNTH-102 — Synthetic Patient 102</option>
                </>
              )}
            </select>
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
              className="flex-1 bg-cyan-600 hover:bg-cyan-500 disabled:bg-slate-800 text-white font-semibold py-2 px-4 rounded-lg text-sm transition-colors flex items-center justify-center gap-1.5 shadow"
            >
              <Search className="w-4 h-4" />
              <span>{isLoading ? 'Filtering...' : 'Apply Filters'}</span>
            </button>

            <button
              type="button"
              onClick={handleResetFilters}
              title="Reset Filters"
              className="bg-slate-800 hover:bg-slate-700 text-slate-300 p-2.5 rounded-lg border border-slate-700 transition-colors"
            >
              <RotateCcw className="w-4 h-4" />
            </button>
          </div>
        </form>
      </div>

      {/* 4. Telemetry Statistics Bar */}
      {roadmapData?.statistics && (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
          {/* Card 1: Total Points */}
          <div className="glass-panel p-3.5 rounded-xl border border-slate-800">
            <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Observations</div>
            <div className="text-xl font-bold text-white mt-1 flex items-baseline gap-1.5">
              <span>{roadmapData.statistics.total_observations}</span>
              <span className="text-xs font-normal text-slate-400 font-mono">points</span>
            </div>
          </div>

          {/* Card 2: Monitoring Start */}
          <div className="glass-panel p-3.5 rounded-xl border border-slate-800">
            <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Start Time</div>
            <div className="text-sm font-bold text-emerald-400 mt-1 font-mono">
              {roadmapData.statistics.monitoring_start 
                ? new Date(roadmapData.statistics.monitoring_start).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
                : '—'}
            </div>
            <div className="text-[10px] text-slate-500 font-mono">Point A (Initial)</div>
          </div>

          {/* Card 3: Monitoring End */}
          <div className="glass-panel p-3.5 rounded-xl border border-slate-800">
            <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Latest Point</div>
            <div className="text-sm font-bold text-rose-400 mt-1 font-mono">
              {roadmapData.statistics.monitoring_end 
                ? new Date(roadmapData.statistics.monitoring_end).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
                : '—'}
            </div>
            <div className="text-[10px] text-slate-500 font-mono">Final Telemetry</div>
          </div>

          {/* Card 4: Average Accuracy */}
          <div className="glass-panel p-3.5 rounded-xl border border-slate-800">
            <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Avg Accuracy</div>
            <div className="text-xl font-bold text-cyan-400 mt-1 flex items-baseline gap-1">
              <span>{roadmapData.statistics.average_accuracy !== null ? `±${roadmapData.statistics.average_accuracy}` : '—'}</span>
              <span className="text-xs font-normal text-slate-400 font-mono">m</span>
            </div>
          </div>

          {/* Card 5: Sampling Cadence */}
          <div className="glass-panel p-3.5 rounded-xl border border-slate-800">
            <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Cadence</div>
            <div className="text-sm font-bold text-slate-200 mt-1">~15 Minutes</div>
            <div className="text-[10px] text-slate-500">Discrete Sampling</div>
          </div>

          {/* Card 6: Spatial Coordinates */}
          <div className="glass-panel p-3.5 rounded-xl border border-slate-800">
            <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">First Lat/Lng</div>
            <div className="text-xs font-bold text-slate-300 mt-1 font-mono truncate">
              {roadmapData.statistics.first_recorded_location 
                ? `${roadmapData.statistics.first_recorded_location.latitude.toFixed(4)}, ${roadmapData.statistics.first_recorded_location.longitude.toFixed(4)}`
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
              {/* Dark Carto Tile Layer for clean academic / geospatial visualization */}
              <TileLayer
                attribution='&copy; <a href="https://carto.com/">CARTO</a> & OpenStreetMap'
                url="https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png"
              />

              <MapBoundsFitter 
                observations={roadmapData?.observations || []} 
                selectedCoord={flyToCoord}
              />

              {/* Sequential Visual Connection Polyline */}
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

              {/* Observation Markers */}
              {roadmapData?.observations?.map((obs, idx) => {
                const isSelected = obs.id === selectedPointId;
                const timeFormatted = new Date(obs.recorded_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
                const icon = createCustomMarkerIcon(
                  idx, 
                  roadmapData?.observations?.length || 1, 
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
                      <div className="p-1 space-y-2 text-slate-900 min-w-[200px]">
                        <div className="flex items-center justify-between border-b pb-1.5">
                          <span className="font-bold text-xs uppercase tracking-wider text-cyan-800">
                            Point {String.fromCharCode(65 + idx)} {idx === 0 ? '(START)' : idx === roadmapData.observations.length - 1 ? '(END)' : ''}
                          </span>
                          <span className="text-[11px] font-mono font-semibold bg-slate-100 px-1.5 py-0.5 rounded">
                            {timeFormatted}
                          </span>
                        </div>

                        <div className="space-y-1 text-xs">
                          <div className="flex justify-between">
                            <span className="text-slate-500">Timestamp:</span>
                            <span className="font-mono text-[11px] text-slate-700">
                              {new Date(obs.recorded_at).toISOString().replace('T', ' ').substring(0, 19)} UTC
                            </span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-slate-500">Coordinates:</span>
                            <span className="font-mono text-[11px] font-semibold text-slate-800">
                              {obs.latitude.toFixed(5)}, {obs.longitude.toFixed(5)}
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
                              {obs.source}
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
                <span>Intermediate Observations</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="w-3 h-3 rounded-full bg-rose-500 border border-rose-300"></span>
                <span>Point D/E (Final Observation)</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="w-6 h-0.5 border-t-2 border-dashed border-cyan-500"></span>
                <span className="text-[11px] text-slate-400">Visual Connection (Not continuous GPS)</span>
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
                <span>Sequential Timeline</span>
              </div>
              <span className="text-xs text-slate-400 font-mono">
                {roadmapData?.observations.length || 0} Records
              </span>
            </div>

            {/* Timeline Scrollable Container */}
            <div 
              ref={timelineRef}
              className="mt-3 space-y-2.5 max-h-[500px] overflow-y-auto pr-1"
            >
              {roadmapData?.observations && roadmapData.observations.length > 0 ? (
                roadmapData.observations.map((obs, idx) => {
                  const isSelected = obs.id === selectedPointId;
                  const isStart = idx === 0;
                  const isEnd = idx === roadmapData.observations.length - 1 && roadmapData.observations.length > 1;
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
                            {String.fromCharCode(65 + idx)}
                          </span>
                          <span className="font-bold text-white font-mono text-sm">
                            {timeFormatted}
                          </span>
                          {isStart && (
                            <span className="text-[10px] font-bold text-emerald-400 bg-emerald-500/10 px-1.5 py-0.5 rounded border border-emerald-500/20">
                              START
                            </span>
                          )}
                          {isEnd && (
                            <span className="text-[10px] font-bold text-rose-400 bg-rose-500/10 px-1.5 py-0.5 rounded border border-rose-500/20">
                              END
                            </span>
                          )}
                        </div>

                        {/* Source Tag Badge */}
                        <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${
                          obs.source === 'PATIENT_GPS' 
                            ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                            : obs.source === 'HEALTH_WORKER'
                            ? 'bg-indigo-500/10 text-indigo-400 border border-indigo-500/20'
                            : 'bg-slate-800 text-slate-400 border border-slate-700'
                        }`}>
                          {obs.source}
                        </span>
                      </div>

                      <div className="mt-2 text-[11px] text-slate-400 font-mono flex items-center justify-between border-t border-slate-800/60 pt-1.5">
                        <span className="flex items-center gap-1">
                          <MapPin className="w-3 h-3 text-cyan-400" />
                          <span>{obs.latitude.toFixed(4)}, {obs.longitude.toFixed(4)}</span>
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
                  No location observations recorded for the selected filters.
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
