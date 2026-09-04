import React from 'react';
import { 
  MapPin, 
  Layers, 
  Maximize2, 
  Compass, 
  Radar, 
  ShieldAlert,
  Crosshair
} from 'lucide-react';

export const MapPlaceholder: React.FC = () => {
  return (
    <div className="glass-panel rounded-xl overflow-hidden flex flex-col h-[460px]">
      {/* Map Control Toolbar */}
      <div className="px-5 py-3.5 border-b border-slate-800 bg-slate-900/60 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <MapPin className="w-4 h-4 text-brand-400" />
          <h2 className="font-heading font-semibold text-sm text-slate-200">
            Geographic Surveillance & Outbreak Radar
          </h2>
          <span className="text-[10px] font-mono bg-brand-500/20 text-brand-400 px-2 py-0.5 rounded border border-brand-500/30">
            Leaflet + PostGIS Engine
          </span>
        </div>

        <div className="flex items-center gap-2 text-xs">
          <button className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700/60 transition-colors">
            <Layers className="w-3.5 h-3.5 text-slate-400" />
            <span>Layers</span>
          </button>
          <button className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700/60 transition-colors">
            <Crosshair className="w-3.5 h-3.5 text-brand-400" />
            <span>Recenter</span>
          </button>
        </div>
      </div>

      {/* Map Viewport Placeholder */}
      <div className="relative flex-1 bg-slate-950/90 radar-grid flex items-center justify-center p-6 overflow-hidden">
        {/* Animated Radar Rings */}
        <div className="absolute w-80 h-80 rounded-full border border-brand-500/20 animate-ping opacity-25"></div>
        <div className="absolute w-96 h-96 rounded-full border border-brand-500/10"></div>
        <div className="absolute w-64 h-64 rounded-full border border-brand-500/25"></div>
        <div className="absolute w-32 h-32 rounded-full border border-cyan-500/30"></div>

        {/* Center Target Marker */}
        <div className="relative z-10 flex flex-col items-center text-center max-w-md space-y-4">
          <div className="w-16 h-16 rounded-2xl bg-gradient-to-tr from-brand-600/30 to-cyan-500/30 border border-brand-500/40 flex items-center justify-center shadow-xl shadow-brand-950">
            <Radar className="w-8 h-8 text-brand-400 animate-pulse" />
          </div>

          <div>
            <h3 className="font-heading font-semibold text-base text-slate-100">
              Spatial-Temporal Surveillance Grid
            </h3>
            <p className="text-xs text-slate-400 mt-1.5 leading-relaxed">
              Geographic coordinates, patient location trails, and spatial hotspot clustering will be visualized here using <span className="text-slate-300 font-semibold">Leaflet</span> and <span className="text-slate-300 font-semibold">PostGIS ST_Point</span> layers.
            </p>
          </div>

          <div className="flex flex-wrap gap-2 justify-center text-[11px] text-slate-400">
            <span className="px-2.5 py-1 rounded-full bg-slate-900 border border-slate-800 flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-emerald-400"></span>
              Monitored Patient Zone
            </span>
            <span className="px-2.5 py-1 rounded-full bg-slate-900 border border-slate-800 flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-amber-400"></span>
              Exposure Corridor
            </span>
            <span className="px-2.5 py-1 rounded-full bg-slate-900 border border-slate-800 flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-rose-400"></span>
              High-Risk Cluster
            </span>
          </div>
        </div>

        {/* Coordinate HUD */}
        <div className="absolute bottom-3 left-3 bg-slate-900/90 backdrop-blur-md px-3 py-1.5 rounded-lg border border-slate-800 text-[11px] font-mono text-slate-400 flex items-center gap-3">
          <span>LAT: 12.9716° N</span>
          <span>LNG: 77.5946° E</span>
          <span className="text-brand-400 font-semibold">EPSG:4326</span>
        </div>

        <div className="absolute top-3 right-3 bg-slate-900/90 backdrop-blur-md px-3 py-1.5 rounded-lg border border-slate-800 text-[11px] font-medium text-slate-400 flex items-center gap-2">
          <Compass className="w-3.5 h-3.5 text-cyan-400" />
          <span>Spatial Zoom: 13x</span>
        </div>
      </div>
    </div>
  );
};
