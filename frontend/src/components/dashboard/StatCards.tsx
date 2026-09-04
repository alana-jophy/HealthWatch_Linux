import React from 'react';
import { 
  Users, 
  MapPin, 
  Flame, 
  Database,
  ArrowUpRight,
  ArrowDownRight,
  ShieldCheck,
  AlertTriangle
} from 'lucide-react';
import { SystemHealth } from '../../types';

interface StatCardsProps {
  systemHealth: SystemHealth | null;
}

export const StatCards: React.FC<StatCardsProps> = ({ systemHealth }) => {
  const isDbReady = systemHealth?.database?.status === 'connected';
  const postgisVersion = systemHealth?.database?.postgis_version || 'Ready for migration';

  const stats = [
    {
      title: 'Active Monitored Cases',
      value: '24',
      change: '+3 new today',
      isPositive: false,
      icon: Users,
      color: 'emerald',
      subtitle: 'Registered patient surveillance',
    },
    {
      title: 'Active Geofenced Zones',
      value: '12',
      change: 'Spatial bounds active',
      isPositive: true,
      icon: MapPin,
      color: 'cyan',
      subtitle: 'PostGIS ST_DWithin telemetry',
    },
    {
      title: 'High-Risk Hotspots',
      value: '3',
      change: 'DBSCAN cluster alert',
      isPositive: false,
      icon: Flame,
      color: 'amber',
      subtitle: 'Spatial-temporal anomaly',
    },
    {
      title: 'PostgreSQL + PostGIS',
      value: isDbReady ? 'ONLINE' : 'PENDING',
      change: isDbReady ? 'Spatial engine v3.4' : 'Awaiting Docker start',
      isPositive: isDbReady,
      icon: Database,
      color: isDbReady ? 'emerald' : 'rose',
      subtitle: isDbReady ? postgisVersion : 'Connect via docker-compose up',
    },
  ];

  const getColorClasses = (color: string) => {
    switch (color) {
      case 'emerald':
        return {
          bg: 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400',
          iconBg: 'bg-emerald-500/20 text-emerald-400',
        };
      case 'cyan':
        return {
          bg: 'bg-cyan-500/10 border-cyan-500/30 text-cyan-400',
          iconBg: 'bg-cyan-500/20 text-cyan-400',
        };
      case 'amber':
        return {
          bg: 'bg-amber-500/10 border-amber-500/30 text-amber-400',
          iconBg: 'bg-amber-500/20 text-amber-400',
        };
      case 'rose':
        return {
          bg: 'bg-rose-500/10 border-rose-500/30 text-rose-400',
          iconBg: 'bg-rose-500/20 text-rose-400',
        };
      default:
        return {
          bg: 'bg-slate-800/40 border-slate-700 text-slate-300',
          iconBg: 'bg-slate-700 text-slate-300',
        };
    }
  };

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      {stats.map((stat, idx) => {
        const Icon = stat.icon;
        const colorStyles = getColorClasses(stat.color);

        return (
          <div
            key={idx}
            className="glass-panel glass-panel-hover rounded-xl p-5 relative overflow-hidden"
          >
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-slate-400">{stat.title}</span>
              <div className={`p-2 rounded-lg ${colorStyles.iconBg}`}>
                <Icon className="w-4 h-4" />
              </div>
            </div>

            <div className="mt-3 flex items-baseline gap-2">
              <span className="font-heading text-2xl font-bold text-white tracking-tight">
                {stat.value}
              </span>
            </div>

            <div className="mt-2 text-xs flex items-center justify-between text-slate-400 border-t border-slate-800/80 pt-2">
              <span className="truncate">{stat.subtitle}</span>
              <span className={`text-[11px] font-semibold flex items-center gap-0.5 ${stat.isPositive ? 'text-emerald-400' : 'text-amber-400'}`}>
                {stat.change}
              </span>
            </div>
          </div>
        );
      })}
    </div>
  );
};
