import React, { useState, useEffect } from 'react';
import { fetchMyLocationHistory } from '../../services/api';
import { PatientLocationHistoryItem } from '../../types';
import {
  MapPin,
  Clock,
  RefreshCw,
  AlertCircle,
  Database,
  Radio,
  FileSpreadsheet,
  ChevronLeft,
  ChevronRight
} from 'lucide-react';

export const PatientLocationHistoryView: React.FC = () => {
  const [history, setHistory] = useState<PatientLocationHistoryItem[]>([]);
  const [total, setTotal] = useState<number>(0);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [limit] = useState<number>(20);
  const [skip, setSkip] = useState<number>(0);

  const loadHistory = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const res = await fetchMyLocationHistory(limit, skip);
      setHistory(res.items);
      setTotal(res.total);
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to load location history records.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadHistory();
  }, [skip]);

  const totalPages = Math.ceil(total / limit) || 1;
  const currentPage = Math.floor(skip / limit) + 1;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 glass-panel p-6 rounded-2xl">
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-2xl bg-brand-500/15 border border-brand-500/30 flex items-center justify-center text-brand-400">
            <Clock className="w-6 h-6" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="font-heading text-xl font-bold text-white">My Location History</h2>
              <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-brand-500/15 text-brand-400 border border-brand-500/30">
                {total} Observations
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-0.5">
              Tabular spatial-temporal observations recorded during consented surveillance sessions (approx. every 15 mins)
            </p>
          </div>
        </div>

        <button
          onClick={loadHistory}
          disabled={isLoading}
          className="inline-flex items-center gap-2 px-3.5 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold border border-slate-700 transition-colors disabled:opacity-50"
        >
          <RefreshCw className={`w-3.5 h-3.5 text-brand-400 ${isLoading ? 'animate-spin' : ''}`} />
          <span>Refresh History</span>
        </button>
      </div>

      {/* State Handlers */}
      {isLoading ? (
        <div className="glass-panel p-12 rounded-2xl text-center space-y-3">
          <RefreshCw className="w-8 h-8 text-brand-400 animate-spin mx-auto" />
          <p className="text-sm font-medium text-slate-300">Loading location history records...</p>
        </div>
      ) : error ? (
        <div className="glass-panel p-8 rounded-2xl border-rose-500/30 bg-rose-950/10 text-center space-y-3">
          <AlertCircle className="w-8 h-8 text-rose-400 mx-auto" />
          <h3 className="text-base font-semibold text-rose-300">Unable to Fetch History</h3>
          <p className="text-xs text-slate-400 max-w-md mx-auto">{error}</p>
          <button
            onClick={loadHistory}
            className="px-4 py-2 rounded-xl bg-rose-600 hover:bg-rose-500 text-white text-xs font-semibold"
          >
            Retry
          </button>
        </div>
      ) : history.length === 0 ? (
        <div className="glass-panel p-12 rounded-2xl text-center space-y-3">
          <MapPin className="w-10 h-10 text-slate-600 mx-auto" />
          <h3 className="text-base font-bold text-white">No Location History Recorded</h3>
          <p className="text-xs text-slate-400 max-w-sm mx-auto">
            No spatial-temporal observations have been logged yet for your active monitoring session.
          </p>
        </div>
      ) : (
        <div className="glass-panel rounded-2xl overflow-hidden space-y-0">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-900/80 border-b border-slate-800 text-slate-400 font-mono uppercase text-[10px]">
                <tr>
                  <th className="py-3.5 px-4">#</th>
                  <th className="py-3.5 px-4">Timestamp</th>
                  <th className="py-3.5 px-4">Latitude</th>
                  <th className="py-3.5 px-4">Longitude</th>
                  <th className="py-3.5 px-4">Accuracy</th>
                  <th className="py-3.5 px-4">Source Provider</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-mono text-slate-300">
                {history.map((loc, idx) => (
                  <tr key={loc.id || idx} className="hover:bg-slate-800/40 transition-colors">
                    <td className="py-3 px-4 text-slate-500">{skip + idx + 1}</td>
                    <td className="py-3 px-4 text-white font-medium">
                      {new Date(loc.recorded_at).toLocaleString()}
                    </td>
                    <td className="py-3 px-4 text-brand-300">{loc.latitude.toFixed(6)}</td>
                    <td className="py-3 px-4 text-brand-300">{loc.longitude.toFixed(6)}</td>
                    <td className="py-3 px-4">
                      <span className="px-2 py-0.5 rounded bg-slate-800 text-emerald-400 border border-slate-700">
                        &plusmn;{loc.accuracy ? loc.accuracy.toFixed(1) : '5.0'}m
                      </span>
                    </td>
                    <td className="py-3 px-4">
                      <span
                        className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                          loc.source === 'PATIENT_GPS'
                            ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30'
                            : 'bg-amber-500/15 text-amber-400 border border-amber-500/30'
                        }`}
                      >
                        {loc.source}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination Bar */}
          <div className="p-4 bg-slate-900/60 border-t border-slate-800 flex items-center justify-between text-xs text-slate-400">
            <div>
              Showing <span className="text-white font-semibold">{skip + 1}</span> to{' '}
              <span className="text-white font-semibold">{Math.min(skip + limit, total)}</span> of{' '}
              <span className="text-white font-semibold">{total}</span> observations
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={() => setSkip(Math.max(0, skip - limit))}
                disabled={skip === 0 || isLoading}
                className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 disabled:opacity-40 border border-slate-700"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
              <span className="text-xs font-mono px-2">
                Page {currentPage} of {totalPages}
              </span>
              <button
                onClick={() => setSkip(skip + limit)}
                disabled={skip + limit >= total || isLoading}
                className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 disabled:opacity-40 border border-slate-700"
              >
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
