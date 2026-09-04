import React, { useState, useEffect } from 'react';
import { fetchMyDiseaseCases } from '../../services/api';
import { PatientDiseaseCase } from '../../types';
import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  Clock,
  FileText,
  RefreshCw,
  ShieldAlert,
  Info,
  Calendar
} from 'lucide-react';

export const MyDiseaseCaseView: React.FC = () => {
  const [cases, setCases] = useState<PatientDiseaseCase[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const loadCases = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const res = await fetchMyDiseaseCases();
      setCases(res.items);
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to load disease cases.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadCases();
  }, []);

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'CONFIRMED':
        return 'bg-rose-500/15 text-rose-400 border-rose-500/30';
      case 'SUSPECTED':
        return 'bg-amber-500/15 text-amber-400 border-amber-500/30';
      case 'RECOVERED':
        return 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30';
      default:
        return 'bg-slate-800 text-slate-400 border-slate-700';
    }
  };

  const getSeverityBadge = (severity: string) => {
    switch (severity) {
      case 'CRITICAL':
      case 'SEVERE':
        return 'bg-rose-500/20 text-rose-300 font-bold';
      case 'MODERATE':
        return 'bg-amber-500/20 text-amber-300 font-bold';
      case 'MILD':
        return 'bg-emerald-500/20 text-emerald-300 font-medium';
      default:
        return 'bg-slate-800 text-slate-300';
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 glass-panel p-6 rounded-2xl">
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-2xl bg-brand-500/15 border border-brand-500/30 flex items-center justify-center text-brand-400">
            <Activity className="w-6 h-6" />
          </div>
          <div>
            <h2 className="font-heading text-xl font-bold text-white">My Disease Case Surveillance</h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Personal disease diagnosis records, status trajectory, and clinical observations
            </p>
          </div>
        </div>

        <button
          onClick={loadCases}
          disabled={isLoading}
          className="inline-flex items-center gap-2 px-3.5 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold border border-slate-700 transition-colors disabled:opacity-50"
        >
          <RefreshCw className={`w-3.5 h-3.5 text-brand-400 ${isLoading ? 'animate-spin' : ''}`} />
          <span>Refresh Records</span>
        </button>
      </div>

      {/* Loading / Error / Empty States */}
      {isLoading ? (
        <div className="glass-panel p-12 rounded-2xl text-center space-y-3">
          <RefreshCw className="w-8 h-8 text-brand-400 animate-spin mx-auto" />
          <p className="text-sm font-medium text-slate-300">Retrieving disease cases...</p>
        </div>
      ) : error ? (
        <div className="glass-panel p-8 rounded-2xl border-rose-500/30 bg-rose-950/10 text-center space-y-3">
          <ShieldAlert className="w-8 h-8 text-rose-400 mx-auto" />
          <h3 className="text-base font-semibold text-rose-300">Unable to Fetch Disease Cases</h3>
          <p className="text-xs text-slate-400 max-w-md mx-auto">{error}</p>
          <button
            onClick={loadCases}
            className="px-4 py-2 rounded-xl bg-rose-600 hover:bg-rose-500 text-white text-xs font-semibold"
          >
            Retry
          </button>
        </div>
      ) : cases.length === 0 ? (
        <div className="glass-panel p-12 rounded-2xl text-center space-y-3">
          <CheckCircle2 className="w-12 h-12 text-emerald-400 mx-auto" />
          <h3 className="text-base font-bold text-white">No Active Disease Cases</h3>
          <p className="text-xs text-slate-400 max-w-sm mx-auto">
            You currently have no active or historical disease cases recorded in HealthWatch.
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {cases.map((c) => (
            <div key={c.id} className="glass-panel p-6 rounded-2xl space-y-4">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-800 pb-4">
                <div>
                  <div className="flex items-center gap-3">
                    <h3 className="font-heading text-lg font-bold text-white">
                      {c.disease?.name || 'Dengue Fever'}
                    </h3>
                    <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-slate-800 text-slate-300 border border-slate-700">
                      {c.disease?.code || 'DISEASE'}
                    </span>
                  </div>
                  <div className="text-xs text-slate-400 mt-1 flex items-center gap-2">
                    <span>Category: {c.disease?.category || 'Surveillance'}</span>
                    <span>&bull;</span>
                    <span>
                      Contagion:{' '}
                      <strong className={c.disease?.contagion_type === 'CONTAGIOUS' ? 'text-amber-400' : 'text-emerald-400'}>
                        {c.disease?.contagion_type || 'CONTAGIOUS'}
                      </strong>
                    </span>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <span className={`px-3 py-1 rounded-full text-xs font-semibold border ${getStatusBadge(c.case_status)}`}>
                    {c.case_status}
                  </span>
                  <span className={`px-3 py-1 rounded-full text-xs ${getSeverityBadge(c.severity)}`}>
                    {c.severity} Severity
                  </span>
                </div>
              </div>

              {/* Case Attributes */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-xs">
                <div className="p-3.5 rounded-xl bg-slate-900/60 border border-slate-800">
                  <span className="text-slate-500 block text-[10px] uppercase font-mono mb-1">
                    Diagnosis Date
                  </span>
                  <span className="font-semibold text-slate-200 flex items-center gap-1.5">
                    <Calendar className="w-3.5 h-3.5 text-brand-400" />
                    {c.diagnosis_date ? new Date(c.diagnosis_date).toLocaleDateString() : 'N/A'}
                  </span>
                </div>

                <div className="p-3.5 rounded-xl bg-slate-900/60 border border-slate-800">
                  <span className="text-slate-500 block text-[10px] uppercase font-mono mb-1">
                    Incubation Period
                  </span>
                  <span className="font-semibold text-slate-200 flex items-center gap-1.5">
                    <Clock className="w-3.5 h-3.5 text-brand-400" />
                    {c.disease?.incubation_period_days || 7} Days
                  </span>
                </div>

                <div className="p-3.5 rounded-xl bg-slate-900/60 border border-slate-800">
                  <span className="text-slate-500 block text-[10px] uppercase font-mono mb-1">
                    Estimated R0 Repro Rate
                  </span>
                  <span className="font-mono font-bold text-brand-400">
                    {c.disease?.r0_estimate !== undefined ? c.disease.r0_estimate : '1.8'}
                  </span>
                </div>
              </div>

              {/* Clinical Notes */}
              {c.clinical_notes && (
                <div className="p-4 rounded-xl bg-slate-950/80 border border-slate-800 space-y-1.5">
                  <span className="text-[11px] font-semibold text-slate-400 flex items-center gap-1.5">
                    <FileText className="w-3.5 h-3.5 text-brand-400" /> Clinical Surveillance Notes
                  </span>
                  <p className="text-xs text-slate-300 leading-relaxed font-mono">
                    {c.clinical_notes}
                  </p>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
