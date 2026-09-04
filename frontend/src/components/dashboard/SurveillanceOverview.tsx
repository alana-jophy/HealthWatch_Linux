import React from 'react';
import { TrendingUp, BarChart3, AlertCircle } from 'lucide-react';

export const SurveillanceOverview: React.FC = () => {
  return (
    <div className="glass-panel rounded-xl p-5 flex flex-col justify-between">
      <div className="flex items-center justify-between border-b border-slate-800 pb-3">
        <div className="flex items-center gap-2">
          <TrendingUp className="w-4 h-4 text-emerald-400" />
          <h2 className="font-heading font-semibold text-sm text-slate-200">
            Outbreak Trajectory & Incidence
          </h2>
        </div>
        <span className="text-xs text-slate-400">7-Day Moving Avg</span>
      </div>

      <div className="my-6 flex flex-col items-center justify-center text-center p-6 border border-dashed border-slate-800 rounded-lg bg-slate-950/40">
        <BarChart3 className="w-10 h-10 text-slate-600 mb-2" />
        <div className="text-sm font-medium text-slate-300">
          Epidemiological Analytics Engine
        </div>
        <p className="text-xs text-slate-500 max-w-xs mt-1">
          Time-series incidence rates and reproduction rate estimates (Rt) generated via Recharts will be rendered here.
        </p>
      </div>

      <div className="grid grid-cols-3 gap-2 text-center pt-2 border-t border-slate-800/80">
        <div className="bg-slate-900/50 p-2 rounded-lg">
          <div className="text-[10px] text-slate-400 uppercase">R(t) Factor</div>
          <div className="text-sm font-bold text-amber-400 font-mono">1.18</div>
        </div>
        <div className="bg-slate-900/50 p-2 rounded-lg">
          <div className="text-[10px] text-slate-400 uppercase">Surveillance Rate</div>
          <div className="text-sm font-bold text-emerald-400 font-mono">94.2%</div>
        </div>
        <div className="bg-slate-900/50 p-2 rounded-lg">
          <div className="text-[10px] text-slate-400 uppercase">AI Hotspots</div>
          <div className="text-sm font-bold text-purple-400 font-mono">03</div>
        </div>
      </div>
    </div>
  );
};
