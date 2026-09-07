import React, { useState, useEffect, useRef } from 'react';
import { 
  fetchMonitoringStatus, 
  grantLocationConsent, 
  revokeLocationConsent, 
  startMonitoringSession, 
  stopMonitoringSession,
  submitLocationObservation,
  fetchMyLocationHistory,
  fetchMyPatientProfile
} from '../../services/api';
import { PatientMonitoringStatus, PatientLocationHistoryItem, PatientProfile } from '../../types';
import { 
  ShieldCheck, 
  ShieldAlert, 
  MapPin, 
  Clock, 
  CheckCircle2, 
  AlertCircle, 
  Radio, 
  Power, 
  RefreshCw, 
  Info, 
  Lock, 
  UserCheck, 
  Send, 
  Navigation,
  Smartphone,
  Compass,
  AlertTriangle,
  ChevronDown,
  ChevronUp
} from 'lucide-react';

export const PatientMonitoringView: React.FC = () => {
  const [statusData, setStatusData] = useState<PatientMonitoringStatus | null>(null);
  const [patientProfile, setPatientProfile] = useState<PatientProfile | null>(null);
  const [lastObservation, setLastObservation] = useState<PatientLocationHistoryItem | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [actionLoading, setActionLoading] = useState<boolean>(false);
  const [liveGpsLoading, setLiveGpsLoading] = useState<boolean>(false);
  const [devicePermissionState, setDevicePermissionState] = useState<'prompt' | 'granted' | 'denied' | 'unsupported'>('prompt');
  const [showPermissionModal, setShowPermissionModal] = useState<boolean>(false);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);
  const [showSimulatorSection, setShowSimulatorSection] = useState<boolean>(false);

  // Demonstration Simulation State (strictly labeled as SIMULATED)
  const [simLat, setSimLat] = useState<number>(8.5241);
  const [simLng, setSimLng] = useState<number>(76.9366);
  const [simLoading, setSimLoading] = useState<boolean>(false);

  // Interval reference for periodic phone background telemetry while tab is active
  const telemetryIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const statusDataRef = useRef<PatientMonitoringStatus | null>(null);

  useEffect(() => {
    statusDataRef.current = statusData;
  }, [statusData]);

  const loadStatus = async (): Promise<PatientMonitoringStatus | null> => {
    setIsLoading(true);
    try {
      const [statusRes, historyRes, profileRes] = await Promise.all([
        fetchMonitoringStatus().catch(() => null),
        fetchMyLocationHistory(1, 0).catch(() => null),
        fetchMyPatientProfile().catch(() => null),
      ]);
      setStatusData(statusRes);
      statusDataRef.current = statusRes;
      setPatientProfile(profileRes);
      if (historyRes && historyRes.items && historyRes.items.length > 0) {
        setLastObservation(historyRes.items[0]);
      } else {
        setLastObservation(null);
      }
      return statusRes;
    } catch (err) {
      console.error('Failed to load patient monitoring status:', err);
      return null;
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadStatus();

    // Check device geolocation availability
    if (!('geolocation' in navigator)) {
      setDevicePermissionState('unsupported');
    } else if (navigator.permissions && navigator.permissions.query) {
      navigator.permissions.query({ name: 'geolocation' as PermissionName })
        .then((res) => {
          if (res.state === 'granted') setDevicePermissionState('granted');
          else if (res.state === 'denied') setDevicePermissionState('denied');
          else setDevicePermissionState('prompt');
        })
        .catch(() => setDevicePermissionState('prompt'));
    }

    return () => {
      if (telemetryIntervalRef.current) {
        clearInterval(telemetryIntervalRef.current);
      }
    };
  }, []);

  // Compute minutes since last observation
  const getMinutesAgo = (): number | null => {
    if (!lastObservation) return null;
    const diffMs = Date.now() - new Date(lastObservation.recorded_at).getTime();
    return Math.max(0, Math.floor(diffMs / 60000));
  };

  // Step 1: Grant Explicit Consent (14 Days)
  const handleGrantConsent = async () => {
    setActionLoading(true);
    setMessage(null);
    try {
      await grantLocationConsent(14);
      setMessage({ text: 'Location surveillance consent successfully granted for 14 days.', type: 'success' });
      await loadStatus();
    } catch (err: any) {
      setMessage({ text: err.response?.data?.detail || 'Failed to grant consent.', type: 'error' });
    } finally {
      setActionLoading(false);
    }
  };

  // Step 2: Revoke Consent
  const handleRevokeConsent = async () => {
    setActionLoading(true);
    setMessage(null);
    try {
      await revokeLocationConsent();
      setMessage({ text: 'Location consent revoked. All active monitoring sessions terminated.', type: 'info' });
      if (telemetryIntervalRef.current) clearInterval(telemetryIntervalRef.current);
      await loadStatus();
    } catch (err: any) {
      setMessage({ text: err.response?.data?.detail || 'Failed to revoke consent.', type: 'error' });
    } finally {
      setActionLoading(false);
    }
  };

  // Step 3: Start Monitoring Session
  const handleStartSession = async () => {
    setActionLoading(true);
    setMessage(null);
    const intervalMins = statusDataRef.current?.sampling_interval_minutes || statusData?.sampling_interval_minutes || 15;
    try {
      const sessionRes = await startMonitoringSession(
        undefined,
        undefined,
        24,
        intervalMins
      );
      setMessage({ text: 'Authorized monitoring session started. Real GPS telemetry active.', type: 'success' });
      const updatedStatus = await loadStatus();

      const activeSessionId = sessionRes?.id || updatedStatus?.active_session?.id || statusDataRef.current?.active_session?.id;

      // Immediately attempt to capture initial GPS observation using newly activated session
      if (activeSessionId) {
        setTimeout(() => {
          handleCaptureRealGpsObservation(activeSessionId);
        }, 500);
      }

      // Start periodic collection interval matching configured sampling interval
      if (telemetryIntervalRef.current) clearInterval(telemetryIntervalRef.current);
      telemetryIntervalRef.current = setInterval(() => {
        handleCaptureRealGpsObservation(activeSessionId);
      }, intervalMins * 60 * 1000);

    } catch (err: any) {
      const errMsg = err.response?.data?.error?.message || err.response?.data?.detail || 'Failed to start monitoring session.';
      setMessage({ text: errMsg, type: 'error' });
    } finally {
      setActionLoading(false);
    }
  };

  // Step 4: Stop Monitoring Session
  const handleStopSession = async () => {
    setActionLoading(true);
    setMessage(null);
    try {
      await stopMonitoringSession();
      if (telemetryIntervalRef.current) clearInterval(telemetryIntervalRef.current);
      setMessage({ text: 'Monitoring session stopped. Telemetry collection suspended.', type: 'info' });
      await loadStatus();
    } catch (err: any) {
      setMessage({ text: err.response?.data?.detail || 'Failed to stop session.', type: 'error' });
    } finally {
      setActionLoading(false);
    }
  };

  // Step 5: Capture REAL Phone GPS Location via Device Browser
  const handleCaptureRealGpsObservation = (overrideSessionId?: string) => {
    const activeSessionId = overrideSessionId || statusDataRef.current?.active_session?.id || statusData?.active_session?.id;
    if (!activeSessionId) {
      setMessage({ 
        text: 'Cannot capture GPS: No active monitoring session exists. Please click START MONITORING first.', 
        type: 'error' 
      });
      return;
    }

    if (!('geolocation' in navigator)) {
      setMessage({ 
        text: 'Geolocation is not supported by your mobile browser. Please use Chrome/Firefox on Android or iOS Safari.', 
        type: 'error' 
      });
      return;
    }

    setLiveGpsLoading(true);
    setMessage(null);

    navigator.geolocation.getCurrentPosition(
      async (pos) => {
        setDevicePermissionState('granted');
        const lat = pos.coords.latitude;
        const lng = pos.coords.longitude;
        const accuracy = pos.coords.accuracy || 5.0;

        try {
          // Strictly submitted as source = PATIENT_GPS
          await submitLocationObservation(
            activeSessionId,
            lat,
            lng,
            accuracy,
            'PATIENT_GPS'
          );

          setMessage({
            text: `Real Phone GPS Observation Recorded: (${lat.toFixed(5)}, ${lng.toFixed(5)}) ±${accuracy.toFixed(1)}m [Source: PATIENT_GPS]`,
            type: 'success'
          });

          await loadStatus();
        } catch (err: any) {
          const detail = err.response?.data?.detail || err.response?.data?.error?.message || 'Backend rejected location observation.';
          setMessage({ text: `Observation Rejected: ${detail}`, type: 'error' });
        } finally {
          setLiveGpsLoading(false);
        }
      },
      (err) => {
        setLiveGpsLoading(false);
        let reason = 'Failed to retrieve location from phone hardware.';
        if (err.code === 1) {
          setDevicePermissionState('denied');
          reason = 'Location permission denied by browser. Please tap the lock icon in the address bar and allow location access.';
        } else if (err.code === 2) {
          reason = 'Position unavailable. Ensure Phone GPS / Location Services is turned ON in your phone settings.';
        } else if (err.code === 3) {
          reason = 'GPS acquisition request timed out. Please try again.';
        }
        setMessage({ text: `GPS Error: ${reason}`, type: 'error' });
      },
      {
        enableHighAccuracy: true,
        timeout: 15000,
        maximumAge: 0
      }
    );
  };

  // Step 6: Test Simulated Location Submission (Clearly marked as DEMONSTRATION)
  const handleTestSubmitLocation = async () => {
    if (!statusData?.active_session) {
      setMessage({ text: 'Cannot submit simulated location: No active monitoring session exists.', type: 'error' });
      return;
    }
    setSimLoading(true);
    setMessage(null);
    try {
      await submitLocationObservation(
        statusData.active_session.id,
        simLat,
        simLng,
        5.0,
        'SIMULATED'
      );
      setMessage({ text: `Demonstration Observation recorded: (${simLat.toFixed(4)}, ${simLng.toFixed(4)}) [Source: SIMULATED]`, type: 'info' });
      await loadStatus();
    } catch (err: any) {
      const errMsg = err.response?.data?.error?.message || err.response?.data?.detail || 'Location submission rejected.';
      setMessage({ text: `Submission Rejected: ${errMsg}`, type: 'error' });
    } finally {
      setSimLoading(false);
    }
  };

  const minutesAgo = getMinutesAgo();
  const sessionStatus = statusData?.has_active_session 
    ? 'ACTIVE' 
    : statusData?.active_session?.status || 'NOT ACTIVE';

  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      {/* Title & Header Banner */}
      <div className="glass-panel rounded-2xl p-6 md:p-8 space-y-3 border border-slate-800">
        <div className="flex items-center gap-2 text-xs font-semibold text-brand-400">
          <Smartphone className="w-4 h-4" />
          <span>Patient Surveillance Node &bull; Real Phone GPS Testing</span>
        </div>
        <h1 className="font-heading text-2xl md:text-3xl font-bold text-white tracking-tight">
          My Location Monitoring
        </h1>
        <p className="text-sm text-slate-400 leading-relaxed">
          Authorized spatial surveillance and epidemiological contact tracing observation stream. 
          Uses authentic mobile GPS hardware telemetry collected approximately every {statusData?.sampling_interval_minutes || 15} minutes during an active session.
        </p>

        {/* Patient Identity Header */}
        <div className="flex flex-wrap items-center gap-4 pt-2 border-t border-slate-800 text-xs text-slate-300">
          <div>
            <span className="text-slate-500">Authenticated Patient:</span>{' '}
            <strong className="text-white font-mono">{statusData?.patient_pseudo_id || patientProfile?.pseudo_id || 'PATIENT'}</strong>
          </div>
          <div>
            <span className="text-slate-500">Sampling Cadence:</span>{' '}
            <span className="text-cyan-400 font-medium">Approximately {statusData?.sampling_interval_minutes || 15} minutes</span>
          </div>
          <div>
            <span className="text-slate-500">Telemetry Engine:</span>{' '}
            <span className="text-emerald-400 font-mono">PostgreSQL / PostGIS SRID:4326</span>
          </div>
        </div>
      </div>

      {/* Notice for Patient without mobile phone */}
      {patientProfile?.has_phone === false && (
        <div className="glass-panel p-5 rounded-2xl border border-amber-500/30 bg-amber-950/20 text-amber-200 text-xs flex items-start gap-3">
          <Smartphone className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
          <div className="space-y-1">
            <h4 className="font-bold text-amber-300 text-sm">Mobile Phone GPS Telemetry Inactive</h4>
            <p className="text-slate-300 leading-relaxed">
              Your registered patient record indicates that you do not possess a mobile phone. Direct GPS tracking and active mobile telemetry are disabled for your profile. Your public health case management is handled directly through field visits by your assigned surveillance officer.
            </p>
          </div>
        </div>
      )}

      {/* Mandatory Statutory Permission Explanation Box */}
      <div className="bg-brand-950/40 border border-brand-500/30 rounded-xl p-5 text-slate-200 space-y-2">
        <div className="flex items-center gap-2 text-brand-400 font-semibold text-sm">
          <Info className="w-4 h-4" />
          <span>Statutory Location Permission Notice</span>
        </div>
        <p className="text-sm font-medium text-slate-200 leading-relaxed">
          &ldquo;HealthWatch requires your location during an active authorized monitoring session. Location observations are collected approximately every 15 minutes to support disease surveillance and movement analysis.&rdquo;
        </p>
      </div>

      {/* Notifications Toast */}
      {message && (
        <div className={`p-4 rounded-xl border text-xs flex items-center gap-2.5 ${
          message.type === 'success' ? 'bg-emerald-950/40 border-emerald-500/40 text-emerald-200' :
          message.type === 'error' ? 'bg-rose-950/40 border-rose-500/40 text-rose-200' :
          'bg-slate-800/80 border-slate-700 text-slate-200'
        }`}>
          {message.type === 'success' ? <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" /> : <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />}
          <span>{message.text}</span>
        </div>
      )}

      {/* Permission Explanation Modal Dialog */}
      {showPermissionModal && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="glass-panel border border-brand-500/40 max-w-md w-full p-6 rounded-2xl space-y-4 shadow-2xl">
            <div className="flex items-center gap-3 text-brand-400">
              <Navigation className="w-6 h-6" />
              <h3 className="font-heading font-bold text-lg text-white">Device Location Authorization</h3>
            </div>
            <p className="text-xs text-slate-300 leading-relaxed">
              HealthWatch requires your device&apos;s real GPS location during an active authorized monitoring session. 
              Location observations are collected <strong>approximately every 15 minutes</strong> to support disease surveillance and movement analysis.
            </p>
            <div className="p-3 bg-slate-900 rounded-xl border border-slate-800 text-[11px] text-slate-400 space-y-1">
              <div>&bull; Observations are tagged with source: <span className="text-emerald-400 font-mono font-bold">PATIENT_GPS</span></div>
              <div>&bull; You can revoke consent or stop monitoring at any time</div>
              <div>&bull; Real device coordinates are stored in PostGIS SRID:4326</div>
            </div>
            <div className="flex justify-end gap-3 pt-2">
              <button
                onClick={() => setShowPermissionModal(false)}
                className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold"
              >
                Cancel
              </button>
              <button
                onClick={() => {
                  setShowPermissionModal(false);
                  handleCaptureRealGpsObservation();
                }}
                className="px-5 py-2 rounded-xl bg-brand-600 hover:bg-brand-500 text-white text-xs font-semibold shadow-md flex items-center gap-2"
              >
                <Compass className="w-4 h-4" />
                <span>Authorize & Capture GPS</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ========================================================================= */}
      {/* Required MY LOCATION MONITORING Dashboard Card */}
      {/* ========================================================================= */}
      <div className="glass-panel rounded-2xl p-6 space-y-6 border border-slate-800">
        <div className="flex items-center justify-between border-b border-slate-800 pb-4">
          <div>
            <div className="text-[10px] text-brand-400 uppercase font-mono tracking-wider">Surveillance Telemetry Console</div>
            <h2 className="font-heading text-xl font-bold text-white">
              MY LOCATION MONITORING
            </h2>
          </div>

          <button
            onClick={loadStatus}
            disabled={isLoading}
            className="flex items-center gap-1.5 text-xs text-slate-400 hover:text-white bg-slate-800/80 px-3 py-1.5 rounded-lg border border-slate-700"
          >
            <RefreshCw className={`w-3.5 h-3.5 text-brand-400 ${isLoading ? 'animate-spin' : ''}`} />
            <span>Sync</span>
          </button>
        </div>

        {/* Monitoring Metrics Matrix */}
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4 text-xs">
          {/* Status */}
          <div className="bg-slate-950 p-3.5 rounded-xl border border-slate-800 space-y-1">
            <span className="text-slate-400 font-medium">Status</span>
            <div className="font-heading text-sm font-bold">
              {sessionStatus === 'ACTIVE' ? (
                <span className="text-emerald-400 flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping inline-block"></span>
                  ACTIVE
                </span>
              ) : (
                <span className="text-slate-400">{sessionStatus}</span>
              )}
            </div>
          </div>

          {/* Consent */}
          <div className="bg-slate-950 p-3.5 rounded-xl border border-slate-800 space-y-1">
            <span className="text-slate-400 font-medium">Consent</span>
            <div className="font-heading text-sm font-bold">
              {statusData?.has_active_consent ? (
                <span className="text-emerald-400">GRANTED</span>
              ) : (
                <span className="text-rose-400">NOT GRANTED</span>
              )}
            </div>
          </div>

          {/* Monitoring Start */}
          <div className="bg-slate-950 p-3.5 rounded-xl border border-slate-800 space-y-1">
            <span className="text-slate-400 font-medium">Monitoring Start</span>
            <div className="font-mono text-xs text-slate-200 font-semibold truncate">
              {statusData?.active_session ? new Date(statusData.active_session.start_time).toLocaleString() : '—'}
            </div>
          </div>

          {/* Monitoring End */}
          <div className="bg-slate-950 p-3.5 rounded-xl border border-slate-800 space-y-1">
            <span className="text-slate-400 font-medium">Monitoring End</span>
            <div className="font-mono text-xs text-cyan-400 font-semibold truncate">
              {statusData?.active_session ? new Date(statusData.active_session.end_time).toLocaleString() : '—'}
            </div>
          </div>
        </div>

        {/* Observation Status & Real GPS Metrics */}
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4 text-xs">
          {/* Sampling */}
          <div className="bg-slate-950 p-3.5 rounded-xl border border-slate-800 space-y-1">
            <span className="text-slate-400 font-medium">Sampling Cadence</span>
            <div className="font-mono text-xs text-emerald-400 font-semibold">
              Approximately {statusData?.sampling_interval_minutes || 15} minutes
            </div>
          </div>

          {/* Last GPS Observation */}
          <div className="bg-slate-950 p-3.5 rounded-xl border border-slate-800 space-y-1">
            <span className="text-slate-400 font-medium">Last GPS Observation</span>
            <div className="font-mono text-xs text-white font-semibold truncate">
              {lastObservation 
                ? `${new Date(lastObservation.recorded_at).toLocaleTimeString()}`
                : 'Waiting for first observation'}
            </div>
          </div>

          {/* GPS Accuracy */}
          <div className="bg-slate-950 p-3.5 rounded-xl border border-slate-800 space-y-1">
            <span className="text-slate-400 font-medium">GPS Accuracy</span>
            <div className="font-mono text-xs text-cyan-400 font-semibold">
              {lastObservation ? `±${(lastObservation.accuracy || 5.0).toFixed(1)} m` : '—'}
            </div>
          </div>

          {/* Source */}
          <div className="bg-slate-950 p-3.5 rounded-xl border border-slate-800 space-y-1">
            <span className="text-slate-400 font-medium">Source</span>
            <div>
              <span className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold ${
                lastObservation?.source === 'PATIENT_GPS' 
                  ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30'
                  : 'bg-indigo-500/15 text-indigo-400 border border-indigo-500/30'
              }`}>
                {lastObservation?.source || 'PATIENT_GPS'}
              </span>
            </div>
          </div>
        </div>

        {/* Real-time Location Reception Banner */}
        <div className="p-4 rounded-xl bg-slate-900/90 border border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs">
          <div className="flex items-center gap-3">
            <div className={`w-3 h-3 rounded-full shrink-0 ${lastObservation ? 'bg-emerald-400' : 'bg-amber-400 animate-pulse'}`}></div>
            <div>
              <div className="font-semibold text-slate-200">
                {lastObservation ? (
                  <span>
                    Last location received: <strong className="text-white">{minutesAgo !== null ? `${minutesAgo} minute${minutesAgo === 1 ? '' : 's'} ago` : 'just now'}</strong>
                  </span>
                ) : (
                  <span className="text-amber-300 font-medium">
                    Waiting for the first GPS observation.
                  </span>
                )}
              </div>
              {lastObservation && (
                <div className="text-[11px] text-slate-400 font-mono mt-0.5">
                  Coordinates: ({lastObservation.latitude.toFixed(5)}, {lastObservation.longitude.toFixed(5)}) &bull; PostGIS Geometry SRID:4326
                </div>
              )}
            </div>
          </div>

          {statusData?.has_active_session && (
            <button
              onClick={handleCaptureRealGpsObservation}
              disabled={liveGpsLoading}
              className="inline-flex items-center justify-center gap-2 px-4 py-2 rounded-xl bg-cyan-600 hover:bg-cyan-500 text-white font-semibold transition-all shadow-md text-xs shrink-0 disabled:opacity-50"
            >
              <Compass className={`w-3.5 h-3.5 ${liveGpsLoading ? 'animate-spin' : ''}`} />
              <span>{liveGpsLoading ? 'Acquiring GPS...' : 'Record Phone GPS Now'}</span>
            </button>
          )}
        </div>

        {/* Action Controls: START / STOP */}
        <div className="space-y-4 pt-2">
          {statusData?.has_active_session ? (
            <div className="flex flex-col sm:flex-row gap-3">
              <button
                onClick={handleStopSession}
                disabled={actionLoading}
                className="flex-1 flex items-center justify-center gap-2 px-6 py-3.5 rounded-xl bg-rose-600 hover:bg-rose-500 text-white text-sm font-bold shadow-lg shadow-rose-600/20 transition-all uppercase tracking-wider disabled:opacity-50"
              >
                <Power className="w-4 h-4" />
                <span>STOP MONITORING</span>
              </button>
              <button
                onClick={handleRevokeConsent}
                disabled={actionLoading}
                className="px-4 py-3.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold border border-slate-700 transition-colors"
              >
                <span>Revoke Consent</span>
              </button>
            </div>
          ) : (
            <div className="space-y-4">
              {!statusData?.has_active_consent ? (
                <div className="flex flex-col sm:flex-row gap-3">
                  <button
                    onClick={() => setShowPermissionModal(true)}
                    className="flex-1 flex items-center justify-center gap-2 px-4 py-3.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold border border-slate-700 transition-colors"
                  >
                    <Navigation className="w-4 h-4 text-brand-400" />
                    <span>Authorize Location Permission</span>
                  </button>
                  <button
                    onClick={handleGrantConsent}
                    disabled={actionLoading}
                    className="flex-1 flex items-center justify-center gap-2 px-4 py-3.5 rounded-xl bg-brand-600 hover:bg-brand-500 text-white text-xs font-semibold shadow-lg shadow-brand-500/20 transition-colors disabled:opacity-50"
                  >
                    <ShieldCheck className="w-4 h-4" />
                    <span>Grant Explicit Consent (14 Days)</span>
                  </button>
                </div>
              ) : (
                <button
                  onClick={handleStartSession}
                  disabled={actionLoading}
                  className="w-full flex items-center justify-center gap-2 px-6 py-3.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-bold shadow-lg shadow-emerald-500/20 transition-all uppercase tracking-wider disabled:opacity-50"
                >
                  <Power className="w-4 h-4" />
                  <span>START MONITORING</span>
                </button>
              )}
            </div>
          )}
        </div>
      </div>

      {/* ========================================================================= */}
      {/* SEPARATE DEMONSTRATION SIMULATION SECTION (Clearly identified as SIMULATED) */}
      {/* ========================================================================= */}
      <div className="glass-panel rounded-2xl border border-slate-800 overflow-hidden">
        <button
          onClick={() => setShowSimulatorSection(!showSimulatorSection)}
          className="w-full p-4 flex items-center justify-between text-left hover:bg-slate-900/50 transition-colors"
        >
          <div className="flex items-center gap-2 text-xs font-semibold text-slate-400">
            <Radio className="w-4 h-4 text-indigo-400" />
            <span>Demonstration Simulator Mode (Classroom / Mock Coordinates Only)</span>
          </div>
          {showSimulatorSection ? <ChevronUp className="w-4 h-4 text-slate-400" /> : <ChevronDown className="w-4 h-4 text-slate-400" />}
        </button>

        {showSimulatorSection && (
          <div className="p-5 border-t border-slate-800 space-y-4 bg-slate-950/50">
            <div className="p-3 bg-indigo-950/30 border border-indigo-500/30 rounded-xl text-indigo-200 text-xs flex items-start gap-2.5">
              <AlertTriangle className="w-4 h-4 text-indigo-400 shrink-0 mt-0.5" />
              <p className="leading-relaxed">
                <strong>Demonstration Mode:</strong> Use this panel only for offline academic demonstration when a physical GPS device is not present. 
                Submissions from this simulator will be explicitly tagged as <strong className="font-mono text-white">source = SIMULATED</strong> in PostgreSQL/PostGIS. 
                Do not use this panel for real phone live GPS testing.
              </p>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
              <div className="space-y-1">
                <label className="text-[11px] text-slate-400">Simulated Latitude</label>
                <input
                  type="number"
                  step="0.0001"
                  value={simLat}
                  onChange={(e) => setSimLat(parseFloat(e.target.value))}
                  className="w-full bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 font-mono"
                />
              </div>
              <div className="space-y-1">
                <label className="text-[11px] text-slate-400">Simulated Longitude</label>
                <input
                  type="number"
                  step="0.0001"
                  value={simLng}
                  onChange={(e) => setSimLng(parseFloat(e.target.value))}
                  className="w-full bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 font-mono"
                />
              </div>
              <div className="flex items-end">
                <button
                  onClick={handleTestSubmitLocation}
                  disabled={simLoading}
                  className="w-full flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-medium transition-colors disabled:opacity-50"
                >
                  <Send className="w-3.5 h-3.5" />
                  <span>Send Simulated Observation</span>
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
