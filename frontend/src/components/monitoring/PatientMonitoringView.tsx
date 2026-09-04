import React, { useState, useEffect } from 'react';
import { 
  fetchMonitoringStatus, 
  grantLocationConsent, 
  revokeLocationConsent, 
  startMonitoringSession, 
  stopMonitoringSession,
  submitLocationObservation 
} from '../../services/api';
import { PatientMonitoringStatus } from '../../types';
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
  Navigation
} from 'lucide-react';

export const PatientMonitoringView: React.FC = () => {
  const [statusData, setStatusData] = useState<PatientMonitoringStatus | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [actionLoading, setActionLoading] = useState<boolean>(false);
  const [devicePermissionGranted, setDevicePermissionGranted] = useState<boolean>(false);
  const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' | 'info' } | null>(null);

  // Monitoring Period Datetime Selectors
  const [customStart, setCustomStart] = useState<string>('');
  const [customEnd, setCustomEnd] = useState<string>('');

  // Observation submission simulator state
  const [simLat, setSimLat] = useState<number>(8.5241);
  const [simLng, setSimLng] = useState<number>(76.9366);
  const [simLoading, setSimLoading] = useState<boolean>(false);

  const loadStatus = async () => {
    setIsLoading(true);
    try {
      const data = await fetchMonitoringStatus();
      setStatusData(data);
    } catch (err) {
      console.error('Failed to load patient monitoring status:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadStatus();
  }, []);

  // Check browser OS geolocation permission
  const handleRequestOSPermission = () => {
    if ('geolocation' in navigator) {
      navigator.geolocation.getCurrentPosition(
        (pos) => {
          setDevicePermissionGranted(true);
          setSimLat(pos.coords.latitude);
          setSimLng(pos.coords.longitude);
          setMessage({ text: 'Device GPS permission authorized.', type: 'success' });
        },
        (err) => {
          setDevicePermissionGranted(false);
          setMessage({ text: `Device location permission notice: ${err.message}`, type: 'error' });
        }
      );
    } else {
      setMessage({ text: 'Geolocation is not supported by this browser.', type: 'error' });
    }
  };

  // Step 1: Grant Consent
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
    try {
      await startMonitoringSession(
        customStart ? new Date(customStart).toISOString() : undefined,
        customEnd ? new Date(customEnd).toISOString() : undefined,
        24
      );
      setMessage({ text: 'Authorized monitoring session started. Telemetry active.', type: 'success' });
      await loadStatus();
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
      setMessage({ text: 'Monitoring session stopped.', type: 'info' });
      await loadStatus();
    } catch (err: any) {
      setMessage({ text: err.response?.data?.detail || 'Failed to stop session.', type: 'error' });
    } finally {
      setActionLoading(false);
    }
  };

  // Step 5: Test Periodic Location Submission
  const handleTestSubmitLocation = async () => {
    if (!statusData?.active_session) {
      setMessage({ text: 'Cannot submit location: No active monitoring session exists.', type: 'error' });
      return;
    }
    setSimLoading(true);
    setMessage(null);
    try {
      const res = await submitLocationObservation(
        statusData.active_session.id,
        simLat,
        simLng,
        5.0
      );
      setMessage({ text: `Observation accepted & verified: (${simLat.toFixed(4)}, ${simLng.toFixed(4)})`, type: 'success' });
    } catch (err: any) {
      const errMsg = err.response?.data?.error?.message || err.response?.data?.detail || 'Location submission rejected.';
      setMessage({ text: `Submission Rejected: ${errMsg}`, type: 'error' });
    } finally {
      setSimLoading(false);
    }
  };

  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      {/* Title & Header Banner */}
      <div className="glass-panel rounded-2xl p-6 md:p-8 space-y-3 border border-slate-800">
        <div className="flex items-center gap-2 text-xs font-semibold text-brand-400">
          <UserCheck className="w-4 h-4" />
          <span>Patient Surveillance Node &bull; Strict Consent Verification</span>
        </div>
        <h1 className="font-heading text-2xl md:text-3xl font-bold text-white tracking-tight">
          My Monitoring Dashboard
        </h1>
        <p className="text-sm text-slate-400 leading-relaxed">
          Manage your authorized surveillance observation windows. Every observation stream requires active patient consent and an authorized monitoring session.
        </p>

        {/* Patient Identity Header */}
        <div className="flex flex-wrap items-center gap-4 pt-2 border-t border-slate-800 text-xs text-slate-300">
          <div>
            <span className="text-slate-500">Authenticated Patient:</span>{' '}
            <strong className="text-white font-mono">{statusData?.patient_pseudo_id || 'PAT-SYNTH-101'}</strong>
          </div>
          <div>
            <span className="text-slate-500">Sampling Interval:</span>{' '}
            <span className="text-cyan-400 font-medium">Approximately 15 minutes</span>
          </div>
          <div>
            <span className="text-slate-500">Telemetry Engine:</span>{' '}
            <span className="text-emerald-400 font-mono">PostGIS SRID:4326</span>
          </div>
        </div>
      </div>

      {/* Mandatory Explanation Notice Alert Box */}
      <div className="bg-brand-950/40 border border-brand-500/30 rounded-xl p-5 text-slate-200 space-y-2">
        <div className="flex items-center gap-2 text-brand-400 font-semibold text-sm">
          <Info className="w-4 h-4" />
          <span>Surveillance Frequency Disclosure</span>
        </div>
        <p className="text-sm font-medium text-slate-200">
          &ldquo;{statusData?.explanation_notice || 'HealthWatch will collect your location approximately every 15 minutes during the authorized monitoring period.'}&rdquo;
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

      {/* Main Monitoring Status & Session Card */}
      <div className="glass-panel rounded-2xl p-6 space-y-6 border border-slate-800">
        <div className="flex items-center justify-between border-b border-slate-800 pb-4">
          <div className="flex items-center gap-3">
            <div className={`w-3 h-3 rounded-full ${statusData?.has_active_session ? 'bg-emerald-400 animate-ping' : 'bg-slate-600'}`}></div>
            <div>
              <div className="text-xs text-slate-400 uppercase font-mono">Monitoring Status</div>
              <div className="font-heading text-xl font-extrabold text-white">
                {statusData?.has_active_session ? (
                  <span className="text-emerald-400">ACTIVE</span>
                ) : (
                  <span className="text-slate-400">INACTIVE</span>
                )}
              </div>
            </div>
          </div>

          <button
            onClick={loadStatus}
            className="flex items-center gap-1.5 text-xs text-slate-400 hover:text-white bg-slate-800/80 px-3 py-1.5 rounded-lg border border-slate-700"
          >
            <RefreshCw className="w-3.5 h-3.5 text-brand-400" />
            <span>Sync Status</span>
          </button>
        </div>

        {/* Monitoring Metrics Matrix */}
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4 text-xs">
          <div className="bg-slate-950 p-3.5 rounded-xl border border-slate-800 space-y-1">
            <span className="text-slate-400 font-medium">Monitoring Start</span>
            <div className="font-mono text-sm text-slate-200 font-semibold">
              {statusData?.active_session ? new Date(statusData.active_session.start_time).toLocaleString() : '—'}
            </div>
          </div>

          <div className="bg-slate-950 p-3.5 rounded-xl border border-slate-800 space-y-1">
            <span className="text-slate-400 font-medium">Monitoring End</span>
            <div className="font-mono text-sm text-cyan-400 font-semibold">
              {statusData?.active_session ? new Date(statusData.active_session.end_time).toLocaleString() : '—'}
            </div>
          </div>

          <div className="bg-slate-950 p-3.5 rounded-xl border border-slate-800 space-y-1">
            <span className="text-slate-400 font-medium">Sampling Interval</span>
            <div className="font-mono text-sm text-emerald-400 font-semibold">
              Approximately 15 minutes
            </div>
          </div>
        </div>

        {/* Action Buttons: START / STOP */}
        <div className="space-y-4 pt-2">
          {statusData?.has_active_session ? (
            <div className="flex flex-col sm:flex-row gap-3">
              <button
                onClick={handleStopSession}
                disabled={actionLoading}
                className="flex-1 flex items-center justify-center gap-2 px-6 py-3 rounded-xl bg-rose-600 hover:bg-rose-500 text-white text-sm font-bold shadow-lg shadow-rose-600/20 transition-all uppercase tracking-wider"
              >
                <Power className="w-4 h-4" />
                <span>STOP MONITORING</span>
              </button>
              <button
                onClick={handleRevokeConsent}
                disabled={actionLoading}
                className="px-4 py-3 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold border border-slate-700 transition-colors"
              >
                <span>Revoke Consent</span>
              </button>
            </div>
          ) : (
            <div className="space-y-4">
              {/* Optional Custom Monitoring Period Selectors */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 p-4 bg-slate-950 rounded-xl border border-slate-800/80">
                <div className="space-y-1">
                  <label className="text-[11px] font-semibold text-slate-400">Custom Start Date/Time (Optional)</label>
                  <input
                    type="datetime-local"
                    value={customStart}
                    onChange={(e) => setCustomStart(e.target.value)}
                    className="w-full bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-brand-500"
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-[11px] font-semibold text-slate-400">Custom End Date/Time (Optional)</label>
                  <input
                    type="datetime-local"
                    value={customEnd}
                    onChange={(e) => setCustomEnd(e.target.value)}
                    className="w-full bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-brand-500"
                  />
                </div>
              </div>

              {!statusData?.has_active_consent ? (
                <div className="flex flex-col sm:flex-row gap-3">
                  <button
                    onClick={handleRequestOSPermission}
                    className="flex-1 flex items-center justify-center gap-2 px-4 py-3 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold border border-slate-700 transition-colors"
                  >
                    <Navigation className="w-4 h-4 text-brand-400" />
                    <span>Allow Location Permission</span>
                  </button>
                  <button
                    onClick={handleGrantConsent}
                    disabled={actionLoading}
                    className="flex-1 flex items-center justify-center gap-2 px-4 py-3 rounded-xl bg-brand-600 hover:bg-brand-500 text-white text-xs font-semibold shadow-lg shadow-brand-500/20 transition-colors"
                  >
                    <ShieldCheck className="w-4 h-4" />
                    <span>Grant Explicit Consent (14 Days)</span>
                  </button>
                </div>
              ) : (
                <button
                  onClick={handleStartSession}
                  disabled={actionLoading}
                  className="w-full flex items-center justify-center gap-2 px-6 py-3.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-bold shadow-lg shadow-emerald-500/20 transition-all uppercase tracking-wider"
                >
                  <Power className="w-4 h-4" />
                  <span>START MONITORING</span>
                </button>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Observation Telemetry Ingestion Simulator Panel */}
      <div className="glass-panel rounded-2xl p-5 border border-slate-800 space-y-3">
        <div className="flex items-center justify-between border-b border-slate-800 pb-2">
          <div className="flex items-center gap-2 font-heading font-semibold text-xs text-slate-200">
            <Radio className="w-4 h-4 text-cyan-400" />
            <span>Mobile Location Telemetry Ingestion Simulator</span>
          </div>
          <span className="text-[10px] font-mono text-slate-500">Android Client Endpoint: /api/v1/monitoring/locations/submit</span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
          <div className="space-y-1">
            <label className="text-[11px] text-slate-400">Simulated Latitude</label>
            <input
              type="number"
              step="0.0001"
              value={simLat}
              onChange={(e) => setSimLat(parseFloat(e.target.value))}
              className="w-full bg-slate-950 border border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-slate-200"
            />
          </div>
          <div className="space-y-1">
            <label className="text-[11px] text-slate-400">Simulated Longitude</label>
            <input
              type="number"
              step="0.0001"
              value={simLng}
              onChange={(e) => setSimLng(parseFloat(e.target.value))}
              className="w-full bg-slate-950 border border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-slate-200"
            />
          </div>
          <div className="flex items-end">
            <button
              onClick={handleTestSubmitLocation}
              disabled={simLoading}
              className="w-full flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white font-medium transition-colors"
            >
              <Send className="w-3.5 h-3.5" />
              <span>Send Location Observation</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
