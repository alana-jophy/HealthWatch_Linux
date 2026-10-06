import React, { useState, useEffect } from 'react';
import {
  MapContainer,
  TileLayer,
  CircleMarker,
  Popup,
  Circle,
  useMap,
} from 'react-leaflet';
import {
  fetchExposureEvents,
  triggerExposureAnalysis,
  updateExposureStatus,
} from '../../services/api';
import {
  ExposureEventItem,
  ExposureListResponse,
  ExposureStatus,
} from '../../types';
import {
  Route,
  ShieldCheck,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Clock,
  MapPin,
  Sliders,
  Play,
  RefreshCw,
  Users,
  Filter,
  FileCheck2,
  Info,
  Calendar,
} from 'lucide-react';

const MapFlyTo: React.FC<{ center: [number, number]; zoom: number }> = ({ center, zoom }) => {
  const map = useMap();
  useEffect(() => {
    map.flyTo(center, zoom, { duration: 1.2 });
  }, [center, zoom, map]);
  return null;
};

export const SpatialExposureView: React.FC = () => {
  const [eventsData, setEventsData] = useState<ExposureListResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [activeStatusFilter, setActiveStatusFilter] = useState<string>('ALL');

  // Configurable thresholds
  const [spatialThreshold, setSpatialThreshold] = useState<number>(50); // meters
  const [temporalThreshold, setTemporalThreshold] = useState<number>(15); // minutes
  const [isAnalyzing, setIsAnalyzing] = useState<boolean>(false);
  const [analysisResultMsg, setAnalysisResultMsg] = useState<string | null>(null);

  // Review modal / action state
  const [selectedEvent, setSelectedEvent] = useState<ExposureEventItem | null>(null);
  const [reviewNoteInput, setReviewNoteInput] = useState<string>('');
  const [isSubmittingReview, setIsSubmittingReview] = useState<boolean>(false);

  // Map state (defaults to Kerala state center / Trivandrum)
  const [mapCenter, setMapCenter] = useState<[number, number]>([8.5241, 76.9366]);
  const [mapZoom, setMapZoom] = useState<number>(13);

  // 1. Load Exposure Events
  const loadEvents = async () => {
    setIsLoading(true);
    try {
      const data = await fetchExposureEvents(activeStatusFilter);
      setEventsData(data);
      if (data.items.length > 0) {
        setMapCenter([data.items[0].latitude, data.items[0].longitude]);
      }
    } catch (err) {
      console.error('Failed to load exposure events:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadEvents();
  }, [activeStatusFilter]);

  // 2. Trigger PostGIS Spatial-Temporal Analysis
  const handleRunAnalysis = async () => {
    setIsAnalyzing(true);
    setAnalysisResultMsg(null);
    try {
      const summary = await triggerExposureAnalysis({
        spatial_distance_threshold_meters: spatialThreshold,
        temporal_difference_threshold_minutes: temporalThreshold,
      });
      setAnalysisResultMsg(
        `Algorithm completed: ${summary.potential_overlaps_detected} overlap(s) identified (${summary.newly_created_events} new, ${summary.existing_events_retained} existing).`
      );
      await loadEvents();
    } catch (err) {
      console.error('Failed to run spatial-temporal overlap analysis:', err);
      setAnalysisResultMsg('Analysis failed. Please ensure thresholds are valid.');
    } finally {
      setIsAnalyzing(false);
    }
  };

  // 3. Handle Status Update (Review / Dismiss / Confirm)
  const handleUpdateStatus = async (
    exposureId: string,
    newStatus: ExposureStatus,
    notes?: string
  ) => {
    setIsSubmittingReview(true);
    try {
      await updateExposureStatus(exposureId, newStatus, notes);
      await loadEvents();
      setSelectedEvent(null);
      setReviewNoteInput('');
    } catch (err) {
      console.error('Failed to update exposure event status:', err);
    } finally {
      setIsSubmittingReview(false);
    }
  };

  const getStatusBadge = (status: ExposureStatus) => {
    switch (status) {
      case 'POTENTIAL':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-500/15 text-amber-300 border border-amber-500/30">
            <Clock className="w-3 h-3" />
            <span>POTENTIAL (Pending Review)</span>
          </span>
        );
      case 'REVIEWED':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-cyan-500/15 text-cyan-300 border border-cyan-500/30">
            <CheckCircle2 className="w-3 h-3" />
            <span>REVIEWED</span>
          </span>
        );
      case 'CONFIRMED_BY_AUTHORITY':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/15 text-emerald-300 border border-emerald-500/30">
            <ShieldCheck className="w-3 h-3" />
            <span>CONFIRMED BY AUTHORITY</span>
          </span>
        );
      case 'DISMISSED':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-slate-700/40 text-slate-400 border border-slate-700">
            <XCircle className="w-3 h-3" />
            <span>DISMISSED</span>
          </span>
        );
    }
  };

  const summary = eventsData?.summary_by_status || {
    POTENTIAL: 0,
    REVIEWED: 0,
    DISMISSED: 0,
    CONFIRMED_BY_AUTHORITY: 0,
  };

  return (
    <div className="space-y-6">
      {/* 1. Header & Crucial Scientific Disclaimer Banner */}
      <div className="glass-panel rounded-2xl p-6 border-l-4 border-amber-500 relative overflow-hidden">
        <div className="flex flex-col md:flex-row md:items-start justify-between gap-4">
          <div className="space-y-2 max-w-3xl">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-amber-500/10 border border-amber-500/30 text-xs font-semibold text-amber-300">
              <AlertTriangle className="w-3.5 h-3.5" />
              <span>Decision-Support Surveillance (Step 16)</span>
            </div>
            <h1 className="font-heading text-2xl font-extrabold text-white tracking-tight">
              Potential Spatial-Temporal Exposure Analysis
            </h1>
            <p className="text-xs text-slate-300 leading-relaxed font-sans">
              <strong className="text-amber-300">Important Scientific & Ethical Limitation:</strong> HealthWatch{' '}
              <span className="underline font-bold">never states that Patient A infected Patient B</span>. This module
              evaluates discrete recorded telemetry observations close in both <strong className="text-white">SPACE</strong>{' '}
              and <strong className="text-white">TIME</strong> to flag <em className="text-amber-200">"Potential Spatial-Temporal Overlaps"</em> for
              epidemiological decision support and contact tracing.
            </p>
          </div>

          <div className="bg-slate-950/80 border border-slate-800 p-3 rounded-xl shrink-0 flex flex-col gap-1 text-xs min-w-[210px]">
            <div className="text-slate-400 flex items-center justify-between">
              <span>Security Tier:</span>
              <span className="text-emerald-400 font-mono font-semibold">Officer Only</span>
            </div>
            <div className="text-slate-400 flex items-center justify-between">
              <span>Telemetry Source:</span>
              <span className="text-cyan-400 font-mono">Consented GPS (PostGIS)</span>
            </div>
            <div className="text-slate-400 flex items-center justify-between">
              <span>Data Mode:</span>
              <span className="text-amber-300 font-mono font-semibold">Synthetic Demo</span>
            </div>
          </div>
        </div>
      </div>

      {/* 2. Configurable Thresholds & Algorithm Execution Bar */}
      <div className="glass-panel rounded-2xl p-5 border border-slate-800 space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-800 pb-3">
          <div className="flex items-center gap-2 text-sm font-bold text-white">
            <Sliders className="w-4 h-4 text-cyan-400" />
            <span>Configurable Proximity Thresholds</span>
            <span className="text-[11px] font-normal text-slate-400">(Never hard-coded)</span>
          </div>
          <button
            onClick={handleRunAnalysis}
            disabled={isAnalyzing}
            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-gradient-to-r from-brand-600 to-cyan-600 hover:from-brand-500 hover:to-cyan-500 text-white text-xs font-bold shadow-md transition-all disabled:opacity-50"
          >
            {isAnalyzing ? (
              <RefreshCw className="w-4 h-4 animate-spin" />
            ) : (
              <Play className="w-4 h-4 fill-white" />
            )}
            <span>{isAnalyzing ? 'Running PostGIS Engine...' : 'Run Overlap Detection'}</span>
          </button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 pt-1">
          {/* Spatial Distance Threshold Slider */}
          <div className="space-y-2">
            <div className="flex items-center justify-between text-xs">
              <span className="text-slate-300 font-medium">Spatial Distance Threshold:</span>
              <span className="font-mono font-bold text-cyan-400 bg-cyan-950/60 border border-cyan-800 px-2 py-0.5 rounded">
                &le; {spatialThreshold} meters
              </span>
            </div>
            <input
              type="range"
              min="10"
              max="500"
              step="5"
              value={spatialThreshold}
              onChange={(e) => setSpatialThreshold(Number(e.target.value))}
              className="w-full h-1.5 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-cyan-400"
            />
            <div className="flex justify-between text-[10px] text-slate-500">
              <span>10m (High precision)</span>
              <span>100m</span>
              <span>500m (Broad zone)</span>
            </div>
          </div>

          {/* Temporal Difference Threshold Slider */}
          <div className="space-y-2">
            <div className="flex items-center justify-between text-xs">
              <span className="text-slate-300 font-medium">Temporal Difference Threshold:</span>
              <span className="font-mono font-bold text-purple-400 bg-purple-950/60 border border-purple-800 px-2 py-0.5 rounded">
                &le; {temporalThreshold} minutes
              </span>
            </div>
            <input
              type="range"
              min="2"
              max="60"
              step="1"
              value={temporalThreshold}
              onChange={(e) => setTemporalThreshold(Number(e.target.value))}
              className="w-full h-1.5 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-purple-400"
            />
            <div className="flex justify-between text-[10px] text-slate-500">
              <span>2 mins (Near simultaneous)</span>
              <span>15 mins (Sample interval)</span>
              <span>60 mins</span>
            </div>
          </div>
        </div>

        {analysisResultMsg && (
          <div className="p-3 rounded-xl bg-cyan-950/40 border border-cyan-800/60 text-xs text-cyan-200 flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-cyan-400 shrink-0" />
            <span>{analysisResultMsg}</span>
          </div>
        )}
      </div>

      {/* 3. Surveillance KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="glass-panel p-4 rounded-xl flex items-center justify-between border-l-2 border-slate-600">
          <div>
            <div className="text-xs text-slate-400 font-medium">Total Overlaps</div>
            <div className="font-heading text-2xl font-bold text-white mt-1">
              {eventsData?.total || 0}
            </div>
            <div className="text-[10px] text-slate-500 mt-0.5">Evaluated pairs</div>
          </div>
          <div className="p-2.5 rounded-lg bg-slate-800 text-slate-300">
            <Users className="w-5 h-5" />
          </div>
        </div>

        <div className="glass-panel p-4 rounded-xl flex items-center justify-between border-l-2 border-amber-500">
          <div>
            <div className="text-xs text-amber-300 font-medium">Potential (Pending)</div>
            <div className="font-heading text-2xl font-bold text-amber-400 mt-1">
              {summary.POTENTIAL}
            </div>
            <div className="text-[10px] text-slate-500 mt-0.5">Needs officer triage</div>
          </div>
          <div className="p-2.5 rounded-lg bg-amber-500/15 text-amber-400 border border-amber-500/30">
            <Clock className="w-5 h-5" />
          </div>
        </div>

        <div className="glass-panel p-4 rounded-xl flex items-center justify-between border-l-2 border-cyan-500">
          <div>
            <div className="text-xs text-cyan-300 font-medium">Reviewed / Confirmed</div>
            <div className="font-heading text-2xl font-bold text-cyan-400 mt-1">
              {summary.REVIEWED + summary.CONFIRMED_BY_AUTHORITY}
            </div>
            <div className="text-[10px] text-slate-500 mt-0.5">Verified by officer</div>
          </div>
          <div className="p-2.5 rounded-lg bg-cyan-500/15 text-cyan-400 border border-cyan-500/30">
            <FileCheck2 className="w-5 h-5" />
          </div>
        </div>

        <div className="glass-panel p-4 rounded-xl flex items-center justify-between border-l-2 border-slate-700">
          <div>
            <div className="text-xs text-slate-400 font-medium">Dismissed Events</div>
            <div className="font-heading text-2xl font-bold text-slate-300 mt-1">
              {summary.DISMISSED}
            </div>
            <div className="text-[10px] text-slate-500 mt-0.5">Non-contact / Barriers</div>
          </div>
          <div className="p-2.5 rounded-lg bg-slate-800 text-slate-400">
            <XCircle className="w-5 h-5" />
          </div>
        </div>
      </div>

      {/* 4. Interactive Map & Overlap Table Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left 2 Cols: Overlap Events List */}
        <div className="lg:col-span-2 space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-3 glass-panel p-3 rounded-xl border border-slate-800">
            <div className="flex items-center gap-2">
              <Filter className="w-4 h-4 text-slate-400" />
              <span className="text-xs font-semibold text-slate-300">Filter Status:</span>
            </div>
            <div className="flex flex-wrap gap-1.5">
              {(['ALL', 'POTENTIAL', 'REVIEWED', 'DISMISSED'] as const).map((st) => (
                <button
                  key={st}
                  onClick={() => setActiveStatusFilter(st)}
                  className={`px-3 py-1 rounded-lg text-xs font-medium transition-colors ${
                    activeStatusFilter === st
                      ? 'bg-brand-600 text-white shadow-sm'
                      : 'bg-slate-900 hover:bg-slate-800 text-slate-400'
                  }`}
                >
                  {st}
                </button>
              ))}
            </div>
          </div>

          {isLoading ? (
            <div className="glass-panel rounded-2xl p-12 text-center text-slate-400 text-xs flex items-center justify-center gap-2">
              <RefreshCw className="w-4 h-4 animate-spin text-brand-400" />
              <span>Loading potential exposure records...</span>
            </div>
          ) : eventsData && eventsData.items.length === 0 ? (
            <div className="glass-panel rounded-2xl p-12 text-center text-slate-400 text-xs">
              No exposure events matching the active filter.
            </div>
          ) : (
            <div className="space-y-3">
              {eventsData?.items.map((ev) => (
                <div
                  key={ev.id}
                  className={`glass-panel p-4 rounded-xl border transition-all ${
                    selectedEvent?.id === ev.id
                      ? 'border-cyan-500/80 bg-slate-900/90 shadow-lg'
                      : 'border-slate-800 hover:border-slate-700'
                  }`}
                >
                  <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
                    <div className="space-y-1.5 flex-1">
                      <div className="flex flex-wrap items-center gap-2">
                        {getStatusBadge(ev.status)}
                        <span className="text-xs font-mono text-cyan-400 font-bold">
                          {Math.round(ev.confidence_score * 100)}% Heuristic Score
                        </span>
                      </div>

                      <div className="flex items-center gap-2 text-sm font-semibold text-white pt-1">
                        <span className="px-2 py-0.5 rounded bg-brand-950 border border-brand-800 text-brand-300 font-mono text-xs">
                          {ev.patient_a_pseudo_id}
                        </span>
                        <span className="text-slate-400 text-xs">&harr;</span>
                        <span className="px-2 py-0.5 rounded bg-purple-950 border border-purple-800 text-purple-300 font-mono text-xs">
                          {ev.patient_b_pseudo_id}
                        </span>
                        <span className="text-xs text-slate-400 font-normal">
                          ({ev.patient_a_disease} / {ev.patient_b_disease})
                        </span>
                      </div>

                      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-2 text-xs">
                        <div className="bg-slate-950 p-2 rounded-lg border border-slate-800/80">
                          <span className="text-[10px] text-slate-400 block">Spatial Distance</span>
                          <span className="font-mono font-bold text-cyan-300">
                            {ev.distance} meters
                          </span>
                        </div>
                        <div className="bg-slate-950 p-2 rounded-lg border border-slate-800/80">
                          <span className="text-[10px] text-slate-400 block">Time Difference</span>
                          <span className="font-mono font-bold text-purple-300">
                            {ev.time_difference} mins
                          </span>
                        </div>
                        <div className="bg-slate-950 p-2 rounded-lg border border-slate-800/80 col-span-2">
                          <span className="text-[10px] text-slate-400 block">Location Area</span>
                          <span className="text-slate-200 truncate block">
                            {ev.approximate_location}
                          </span>
                        </div>
                      </div>

                      {ev.review_notes && (
                        <div className="text-xs text-slate-300 bg-slate-950/60 p-2 rounded border border-slate-800 mt-2">
                          <strong className="text-slate-400">Officer Note:</strong> {ev.review_notes}
                          {ev.reviewed_by && (
                            <span className="text-[10px] text-slate-500 block mt-0.5">
                              Reviewed by {ev.reviewed_by} on{' '}
                              {ev.reviewed_at ? new Date(ev.reviewed_at).toLocaleDateString() : 'N/A'}
                            </span>
                          )}
                        </div>
                      )}
                    </div>

                    {/* Action Buttons */}
                    <div className="flex flex-col gap-1.5 shrink-0 self-start">
                      <button
                        onClick={() => {
                          setSelectedEvent(ev);
                          setMapCenter([ev.latitude, ev.longitude]);
                          setMapZoom(16);
                        }}
                        className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-slate-200 border border-slate-700 transition-colors flex items-center justify-center gap-1.5"
                      >
                        <MapPin className="w-3.5 h-3.5 text-cyan-400" />
                        <span>Focus Map</span>
                      </button>

                      {ev.status === 'POTENTIAL' && (
                        <>
                          <button
                            onClick={() => handleUpdateStatus(ev.id, 'REVIEWED', 'Officer verified spatial overlap')}
                            disabled={isSubmittingReview}
                            className="px-3 py-1.5 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-xs font-semibold text-white transition-colors flex items-center justify-center gap-1.5"
                          >
                            <CheckCircle2 className="w-3.5 h-3.5" />
                            <span>Mark Reviewed</span>
                          </button>
                          <button
                            onClick={() => handleUpdateStatus(ev.id, 'DISMISSED', 'Officer dismissed: physical separation')}
                            disabled={isSubmittingReview}
                            className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-rose-900/60 text-xs font-semibold text-slate-400 hover:text-rose-200 border border-slate-700 transition-colors flex items-center justify-center gap-1.5"
                          >
                            <XCircle className="w-3.5 h-3.5" />
                            <span>Dismiss</span>
                          </button>
                        </>
                      )}

                      {ev.status === 'REVIEWED' && (
                        <button
                          onClick={() => handleUpdateStatus(ev.id, 'CONFIRMED_BY_AUTHORITY', 'Confirmed for formal contact tracing')}
                          disabled={isSubmittingReview}
                          className="px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-xs font-semibold text-white transition-colors flex items-center justify-center gap-1.5"
                        >
                          <ShieldCheck className="w-3.5 h-3.5" />
                          <span>Confirm Authority</span>
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Right Col: Leaflet Overlap Geometry Map */}
        <div className="glass-panel p-4 rounded-2xl border border-slate-800 flex flex-col space-y-3 min-h-[460px]">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-1.5 text-xs font-bold text-white">
              <MapPin className="w-4 h-4 text-rose-400" />
              <span>Spatial Intersection Visualizer</span>
            </div>
            <span className="text-[10px] font-mono text-slate-400">PostGIS SRID:4326</span>
          </div>

          <div className="flex-1 rounded-xl overflow-hidden border border-slate-800 relative z-0 min-h-[380px]">
            <MapContainer
              center={mapCenter}
              zoom={mapZoom}
              style={{ width: '100%', height: '100%', minHeight: '380px' }}
              className="z-0"
            >
              <MapFlyTo center={mapCenter} zoom={mapZoom} />
              <TileLayer
                className="map-tiles-dark"
                attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              />

              {eventsData?.items?.map((ev) => (
                <React.Fragment key={ev.id}>
                  {/* Proximity buffer radius circle */}
                  <Circle
                    center={[ev.latitude, ev.longitude]}
                    radius={Math.max(ev.distance, 20)}
                    pathOptions={{
                      color: ev.status === 'POTENTIAL' ? '#f59e0b' : ev.status === 'REVIEWED' ? '#06b6d4' : '#64748b',
                      fillColor: ev.status === 'POTENTIAL' ? '#f59e0b' : ev.status === 'REVIEWED' ? '#06b6d4' : '#64748b',
                      fillOpacity: 0.15,
                      weight: 1.5,
                      dashArray: '4, 4',
                    }}
                  />

                  {/* Center overlap marker */}
                  <CircleMarker
                    center={[ev.latitude, ev.longitude]}
                    radius={8}
                    pathOptions={{
                      color: '#ffffff',
                      fillColor: ev.status === 'POTENTIAL' ? '#f59e0b' : ev.status === 'REVIEWED' ? '#06b6d4' : '#64748b',
                      fillOpacity: 0.9,
                      weight: 2,
                    }}
                  >
                    <Popup className="custom-leaflet-popup">
                      <div className="p-2 space-y-1 text-xs text-slate-900">
                        <strong className="block text-amber-700 font-bold">
                          Potential Spatial-Temporal Overlap
                        </strong>
                        <div>
                          <strong>Participants:</strong> {ev.patient_a_pseudo_id} &amp; {ev.patient_b_pseudo_id}
                        </div>
                        <div>
                          <strong>Distance:</strong> {ev.distance}m
                        </div>
                        <div>
                          <strong>Time Delta:</strong> {ev.time_difference} mins
                        </div>
                        <div>
                          <strong>Status:</strong> {ev.status}
                        </div>
                        <div className="text-[10px] text-slate-600 border-t pt-1 mt-1">
                          Decision support heuristic — does not imply clinical transmission.
                        </div>
                      </div>
                    </Popup>
                  </CircleMarker>
                </React.Fragment>
              ))}
            </MapContainer>
          </div>

          <div className="text-[11px] text-slate-400 bg-slate-950 p-2 rounded-lg border border-slate-800/80 flex items-center justify-between">
            <span>Dashed Circle: Proximity Separation Buffer</span>
            <span className="text-amber-400">&le; {spatialThreshold}m</span>
          </div>
        </div>
      </div>
    </div>
  );
};
