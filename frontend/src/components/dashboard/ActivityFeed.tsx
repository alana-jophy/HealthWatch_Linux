import React from 'react';
import { ShieldAlert, Clock } from 'lucide-react';
import { AlertIncident } from '../../types';

export const ActivityFeed: React.FC = () => {
  const incidents: AlertIncident[] = [
    {
      id: 'INC-8902',
      disease: 'Dengue Fever Cluster',
      location: 'South District (Sector 4)',
      severity: 'high',
      timestamp: '12 mins ago',
      status: 'active',
    },
    {
      id: 'INC-8901',
      disease: 'Viral Hepatitis Type-A',
      location: 'East Ward #12',
      severity: 'medium',
      timestamp: '45 mins ago',
      status: 'investigating',
    },
    {
      id: 'INC-8900',
      disease: 'Influenza Surveillance',
      location: 'Central Corridor',
      severity: 'low',
      timestamp: '2 hours ago',
      status: 'resolved',
    },
  ];

  return (
    <div className="glass-panel rounded-xl p-5 flex flex-col justify-between">
      <div className="flex items-center justify-between border-b border-slate-800 pb-3">
        <div className="flex items-center gap-2">
          <ShieldAlert className="w-4 h-4 text-amber-400" />
          <h2 className="font-heading font-semibold text-sm text-slate-200">
            Surveillance Telemetry Feed
          </h2>
        </div>
        <span className="text-xs text-brand-400 font-medium">Real-time Stream</span>
      </div>

      <div className="space-y-3 my-4">
        {incidents.map((incident) => (
          <div
            key={incident.id}
            className="p-3 rounded-lg bg-slate-900/60 border border-slate-800/80 hover:border-slate-700 transition-colors flex items-start justify-between gap-3"
          >
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <span className="text-xs font-semibold text-white">{incident.disease}</span>
                <span
                  className={`
                    text-[10px] uppercase font-bold px-1.5 py-0.2 rounded
                    ${
                      incident.severity === 'high'
                        ? 'bg-rose-500/20 text-rose-300 border border-rose-500/30'
                        : incident.severity === 'medium'
                        ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                        : 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                    }
                  `}
                >
                  {incident.severity}
                </span>
              </div>
              <div className="text-xs text-slate-400">{incident.location}</div>
            </div>

            <div className="text-[11px] text-slate-500 flex items-center gap-1 shrink-0">
              <Clock className="w-3 h-3" />
              <span>{incident.timestamp}</span>
            </div>
          </div>
        ))}
      </div>

      <div className="pt-2 border-t border-slate-800/80 text-center">
        <button className="text-xs font-medium text-brand-400 hover:text-brand-300 transition-colors">
          View All Monitored Incidents &rarr;
        </button>
      </div>
    </div>
  );
};
