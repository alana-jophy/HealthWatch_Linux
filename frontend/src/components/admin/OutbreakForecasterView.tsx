import React, { useState, useEffect } from 'react';
import { fetchOutbreakPredictions, fetchDiseases, fetchDistricts } from '../../services/api';
import { OutbreakPredictionResponse, AreaOutbreakPrediction, DiseaseItem, DistrictGIS } from '../../types';
import {
  BrainCircuit,
  TrendingUp,
  AlertTriangle,
  RefreshCw,
  AlertCircle,
  ShieldAlert,
  Info,
  CheckCircle2,
  Activity,
  Layers,
  Filter
} from 'lucide-react';

export const OutbreakForecasterView: React.FC = () => {
  const [data, setData] = useState<OutbreakPredictionResponse | null>(null);
  const [diseases, setDiseases] = useState<DiseaseItem[]>([]);
  const [districts, setDistricts] = useState<DistrictGIS[]>([]);
  const [selectedDisease, setSelectedDisease] = useState<string>('');
  const [selectedDistrict, setSelectedDistrict] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const loadPredictions = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [disRes, distRes, predRes] = await Promise.all([
        fetchDiseases().catch(() => []),
        fetchDistricts().catch(() => []),
        fetchOutbreakPredictions(selectedDisease || undefined, selectedDistrict || undefined),
      ]);
      setDiseases(disRes);
      setDistricts(distRes);
      setData(predRes);
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to compute AI outbreak risk predictions.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadPredictions();
  }, [selectedDisease, selectedDistrict]);

  const getRiskBadge = (level: string) => {
    switch (level) {
      case 'CRITICAL':
        return 'bg-rose-500/20 text-rose-300 border-rose-500/40 font-extrabold animate-pulse';
      case 'HIGH':
        return 'bg-amber-500/20 text-amber-300 border-amber-500/40 font-bold';
      case 'MEDIUM':
        return 'bg-yellow-500/15 text-yellow-300 border-yellow-500/30 font-semibold';
      case 'LOW':
      default:
        return 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30 font-medium';
    }
  };

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 glass-panel p-6 rounded-2xl">
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-2xl bg-brand-500/15 border border-brand-500/30 flex items-center justify-center text-brand-400">
            <BrainCircuit className="w-6 h-6" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="font-heading text-xl font-bold text-white">AI-Assisted Outbreak Risk Forecaster</h2>
              <span className="px-2.5 py-0.5 rounded-full text-xs font-mono font-bold bg-purple-500/15 text-purple-400 border border-purple-500/30">
                scikit-learn Decision Support
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-0.5">
              Multi-area epidemiological outbreak risk forecasting using case growth rate, density, $R_0$, and spatial-temporal overlap metrics
            </p>
          </div>
        </div>

        <button
          onClick={loadPredictions}
          disabled={isLoading}
          className="inline-flex items-center gap-2 px-3.5 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold border border-slate-700 transition-colors disabled:opacity-50"
        >
          <RefreshCw className={`w-3.5 h-3.5 text-brand-400 ${isLoading ? 'animate-spin' : ''}`} />
          <span>Re-compute Forecast</span>
        </button>
      </div>

      {/* Decision-Support Mandatory Disclaimer Banner */}
      <div className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/20 text-xs text-amber-300 flex items-start gap-3">
        <Info className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
        <div className="space-y-1">
          <strong className="block font-semibold">Public Health Decision-Support Disclaimer</strong>
          <p className="text-[11px] text-amber-300/80 leading-relaxed font-sans">
            {data?.disclaimer ||
              'This AI/ML module estimates geographic outbreak risk for public-health planning. It does NOT diagnose patients or establish individual transmission.'}
          </p>
        </div>
      </div>

      {/* Filter Toolbar */}
      <div className="glass-panel p-4 rounded-2xl flex flex-col md:flex-row items-center justify-between gap-4">
        <div className="flex items-center gap-2 text-xs text-slate-300">
          <Filter className="w-4 h-4 text-brand-400" />
          <span className="font-semibold">Target Parameters:</span>
        </div>

        <div className="flex flex-col sm:flex-row items-center gap-3 w-full md:w-auto">
          <select
            value={selectedDisease}
            onChange={(e) => setSelectedDisease(e.target.value)}
            className="w-full sm:w-auto bg-slate-900/80 border border-slate-800 text-xs text-slate-200 rounded-xl px-3 py-2 focus:outline-none focus:border-brand-500"
          >
            <option value="">All Surveillance Diseases</option>
            {diseases.map((d) => (
              <option key={d.id} value={d.id}>
                {d.name} ({d.code})
              </option>
            ))}
          </select>

          <select
            value={selectedDistrict}
            onChange={(e) => setSelectedDistrict(e.target.value)}
            className="w-full sm:w-auto bg-slate-900/80 border border-slate-800 text-xs text-slate-200 rounded-xl px-3 py-2 focus:outline-none focus:border-brand-500"
          >
            <option value="">All Kerala Districts</option>
            {districts.map((d) => (
              <option key={d.id} value={d.id}>
                {d.name}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* State Handlers */}
      {isLoading ? (
        <div className="glass-panel p-12 rounded-2xl text-center space-y-3">
          <RefreshCw className="w-8 h-8 text-brand-400 animate-spin mx-auto" />
          <p className="text-sm font-medium text-slate-300">Evaluating outbreak risk features across zones...</p>
        </div>
      ) : error ? (
        <div className="glass-panel p-8 rounded-2xl border-rose-500/30 bg-rose-950/10 text-center space-y-3">
          <AlertCircle className="w-8 h-8 text-rose-400 mx-auto" />
          <h3 className="text-base font-semibold text-rose-300">Failed to Compute Outbreak Forecast</h3>
          <p className="text-xs text-slate-400 max-w-md mx-auto">{error}</p>
          <button
            onClick={loadPredictions}
            className="px-4 py-2 rounded-xl bg-rose-600 hover:bg-rose-500 text-white text-xs font-semibold"
          >
            Retry Forecast
          </button>
        </div>
      ) : !data || data.predictions.length === 0 ? (
        <div className="glass-panel p-12 rounded-2xl text-center space-y-3">
          <BrainCircuit className="w-10 h-10 text-slate-600 mx-auto" />
          <h3 className="text-base font-bold text-white">No Area Risk Forecasts Generated</h3>
        </div>
      ) : (
        <div className="space-y-6">
          {/* Summary Metric Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="glass-panel p-5 rounded-2xl space-y-1">
              <span className="text-[10px] font-mono uppercase text-slate-500">Evaluated Zones</span>
              <div className="text-2xl font-bold text-white">{data.total_areas_evaluated} Areas</div>
            </div>

            <div className="glass-panel p-5 rounded-2xl space-y-1 border-rose-500/30 bg-rose-950/10">
              <span className="text-[10px] font-mono uppercase text-rose-400 font-bold">High / Critical Risk Areas</span>
              <div className="text-2xl font-bold text-rose-300">{data.high_or_critical_risk_areas} Areas</div>
            </div>

            <div className="glass-panel p-5 rounded-2xl space-y-1">
              <span className="text-[10px] font-mono uppercase text-slate-500">ML Framework</span>
              <div className="text-sm font-mono font-bold text-brand-400">{data.model_type || 'Random Forest Classifier'}</div>
            </div>
          </div>

          {/* Area Prediction Cards */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {data.predictions.map((pred, idx) => (
              <div key={idx} className="glass-panel p-6 rounded-2xl space-y-4 flex flex-col justify-between">
                <div className="space-y-3">
                  <div className="flex items-start justify-between gap-3 border-b border-slate-800 pb-3">
                    <div>
                      <h3 className="font-heading text-lg font-bold text-white">{pred.area_name}</h3>
                      <span className="text-xs text-slate-400 font-medium">Pathogen: {pred.disease_name}</span>
                    </div>

                    <div className="text-right space-y-1">
                      <span className={`px-3 py-1 rounded-full text-xs font-mono border block ${getRiskBadge(pred.risk_level)}`}>
                        {pred.risk_level} RISK
                      </span>
                      <span className="text-[10px] font-mono text-slate-500 block">
                        Score: {(pred.risk_score * 100).toFixed(1)}%
                      </span>
                    </div>
                  </div>

                  <div className="grid grid-cols-3 gap-2 text-xs">
                    <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800">
                      <span className="text-[10px] text-slate-500 block">Recent Cases (7d)</span>
                      <span className="font-mono font-bold text-white text-sm">{pred.recent_cases}</span>
                    </div>

                    <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800">
                      <span className="text-[10px] text-slate-500 block">Historical Cases (30d)</span>
                      <span className="font-mono font-bold text-slate-300 text-sm">{pred.historical_cases}</span>
                    </div>

                    <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800">
                      <span className="text-[10px] text-slate-500 block">Case Growth Rate</span>
                      <span className={`font-mono font-bold text-sm ${pred.case_growth_rate > 1 ? 'text-rose-400' : 'text-emerald-400'}`}>
                        {pred.case_growth_rate.toFixed(2)}x
                      </span>
                    </div>
                  </div>

                  {/* Explainability / Feature Importances */}
                  {pred.feature_contributions && (
                    <div className="p-4 rounded-xl bg-slate-950/80 border border-slate-800 space-y-2">
                      <span className="text-[11px] font-semibold text-slate-400 block font-mono">
                        Explainable Risk Feature Contributions:
                      </span>
                      <div className="space-y-1.5 text-xs">
                        {Object.entries(pred.feature_contributions).map(([feat, val]) => (
                          <div key={feat} className="flex items-center justify-between text-[11px]">
                            <span className="text-slate-400 capitalize">{feat.replace(/_/g, ' ')}</span>
                            <div className="flex items-center gap-2">
                              <div className="w-24 h-1.5 rounded-full bg-slate-800 overflow-hidden">
                                <div
                                  className="h-full bg-brand-500 rounded-full"
                                  style={{ width: `${Math.min(100, Math.max(0, val * 100))}%` }}
                                ></div>
                              </div>
                              <span className="font-mono text-slate-300 w-10 text-right">
                                {(val * 100).toFixed(0)}%
                              </span>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
