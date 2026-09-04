import React, { useState, useEffect } from 'react';
import { fetchDiseases } from '../../services/api';
import { DiseaseItem } from '../../types';
import {
  Activity,
  ShieldAlert,
  Clock,
  RefreshCw,
  AlertCircle,
  TrendingUp,
  Tag,
  CheckCircle2,
  Biohazard
} from 'lucide-react';

export const DiseaseManagementView: React.FC = () => {
  const [diseases, setDiseases] = useState<DiseaseItem[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const loadDiseases = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await fetchDiseases();
      setDiseases(data);
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to fetch disease catalog.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadDiseases();
  }, []);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 glass-panel p-6 rounded-2xl">
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-2xl bg-brand-500/15 border border-brand-500/30 flex items-center justify-center text-brand-400">
            <Biohazard className="w-6 h-6" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="font-heading text-xl font-bold text-white">Disease Management Catalog</h2>
              <span className="px-2.5 py-0.5 rounded-full text-xs font-mono font-bold bg-brand-500/15 text-brand-400 border border-brand-500/30">
                {diseases.length} Pathogens
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-0.5">
              Epidemiological pathogen classifications, contagion thresholds, R0 reproduction estimates, and incubation parameters
            </p>
          </div>
        </div>

        <button
          onClick={loadDiseases}
          disabled={isLoading}
          className="inline-flex items-center gap-2 px-3.5 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold border border-slate-700 transition-colors disabled:opacity-50"
        >
          <RefreshCw className={`w-3.5 h-3.5 text-brand-400 ${isLoading ? 'animate-spin' : ''}`} />
          <span>Refresh Catalog</span>
        </button>
      </div>

      {/* State Handlers */}
      {isLoading ? (
        <div className="glass-panel p-12 rounded-2xl text-center space-y-3">
          <RefreshCw className="w-8 h-8 text-brand-400 animate-spin mx-auto" />
          <p className="text-sm font-medium text-slate-300">Loading disease catalog...</p>
        </div>
      ) : error ? (
        <div className="glass-panel p-8 rounded-2xl border-rose-500/30 bg-rose-950/10 text-center space-y-3">
          <AlertCircle className="w-8 h-8 text-rose-400 mx-auto" />
          <h3 className="text-base font-semibold text-rose-300">Failed to Load Catalog</h3>
          <p className="text-xs text-slate-400 max-w-md mx-auto">{error}</p>
          <button
            onClick={loadDiseases}
            className="px-4 py-2 rounded-xl bg-rose-600 hover:bg-rose-500 text-white text-xs font-semibold"
          >
            Retry
          </button>
        </div>
      ) : diseases.length === 0 ? (
        <div className="glass-panel p-12 rounded-2xl text-center space-y-3">
          <Activity className="w-10 h-10 text-slate-600 mx-auto" />
          <h3 className="text-base font-bold text-white">No Diseases Cataloged</h3>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {diseases.map((d) => (
            <div key={d.id} className="glass-panel p-6 rounded-2xl space-y-4 flex flex-col justify-between">
              <div className="space-y-3">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-slate-800 text-slate-300 border border-slate-700">
                      {d.code}
                    </span>
                    <h3 className="font-heading text-lg font-bold text-white mt-1">{d.name}</h3>
                  </div>

                  <span
                    className={`px-2.5 py-1 rounded-full text-[10px] font-mono font-bold border shrink-0 ${
                      d.contagion_type === 'CONTAGIOUS'
                        ? 'bg-rose-500/15 text-rose-400 border-rose-500/30'
                        : 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30'
                    }`}
                  >
                    {d.contagion_type}
                  </span>
                </div>

                <p className="text-xs text-slate-400 leading-relaxed min-h-[36px]">
                  {d.description || 'No descriptive notes registered.'}
                </p>
              </div>

              <div className="space-y-3 pt-3 border-t border-slate-800">
                <div className="grid grid-cols-3 gap-2 text-center text-xs">
                  <div className="p-2 rounded-xl bg-slate-900/60 border border-slate-800">
                    <span className="text-[10px] text-slate-500 block">Category</span>
                    <span className="font-semibold text-slate-300 truncate block">{d.category}</span>
                  </div>

                  <div className="p-2 rounded-xl bg-slate-900/60 border border-slate-800">
                    <span className="text-[10px] text-slate-500 block">Incubation</span>
                    <span className="font-semibold text-slate-200">{d.incubation_period_days} Days</span>
                  </div>

                  <div className="p-2 rounded-xl bg-slate-900/60 border border-slate-800">
                    <span className="text-[10px] text-slate-500 block">R0 Est.</span>
                    <span className="font-mono font-bold text-brand-400">
                      {d.r0_estimate !== undefined ? d.r0_estimate : '1.8'}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
