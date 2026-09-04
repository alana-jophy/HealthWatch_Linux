import React from 'react';
import { 
  Bell, 
  Search, 
  Menu,
  Radio,
  UserCheck,
  Server
} from 'lucide-react';
import { SystemHealth } from '../../types';

interface HeaderProps {
  systemHealth: SystemHealth | null;
  isLoadingHealth: boolean;
  onRefreshHealth: () => void;
  onToggleSidebar: () => void;
  currentRole?: 'PATIENT' | 'OFFICER';
  onToggleRole?: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  systemHealth,
  isLoadingHealth,
  onRefreshHealth,
  onToggleSidebar,
  currentRole = 'PATIENT',
  onToggleRole,
}) => {
  const isBackendUp = systemHealth?.status === 'ok';
  const isDbConnected = systemHealth?.database?.status === 'connected';

  return (
    <header className="h-16 bg-slate-900/80 backdrop-blur-md border-b border-slate-800 sticky top-0 z-30 px-4 lg:px-6 flex items-center justify-between">
      {/* Left section: Mobile menu trigger & Search */}
      <div className="flex items-center gap-4 flex-1">
        <button
          onClick={onToggleSidebar}
          className="lg:hidden p-2 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors"
          title="Toggle Navigation"
        >
          <Menu className="w-5 h-5" />
        </button>

        <div className="relative max-w-md w-full hidden sm:block">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search disease outbreaks, patients, geofences, or zone IDs..."
            className="w-full pl-9 pr-4 py-1.5 bg-slate-950/60 border border-slate-700/60 rounded-lg text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:border-brand-500 focus:ring-1 focus:ring-brand-500 transition-all"
          />
        </div>
      </div>

      {/* Right section: System Telemetry, Notifications & User */}
      <div className="flex items-center gap-3 md:gap-5">
        {/* Backend & PostGIS Health Status Badge */}
        <button
          onClick={onRefreshHealth}
          disabled={isLoadingHealth}
          title="Click to re-check backend & PostGIS telemetry"
          className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-slate-950/70 border border-slate-800 hover:border-slate-700 text-xs transition-all"
        >
          <span className="relative flex h-2 w-2">
            {isBackendUp && isDbConnected ? (
              <>
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
              </>
            ) : (
              <span className="relative inline-flex rounded-full h-2 w-2 bg-rose-500"></span>
            )}
          </span>

          <span className="text-slate-300 font-medium hidden md:inline">
            {isBackendUp && isDbConnected ? 'System Online (PostGIS Active)' : isBackendUp ? 'DB Connecting...' : 'Backend Offline'}
          </span>
          <Server className={`w-3.5 h-3.5 text-slate-400 ${isLoadingHealth ? 'animate-spin' : ''}`} />
        </button>

        {/* Region / Node tag */}
        <div className="hidden lg:flex items-center gap-1.5 text-xs text-slate-400 bg-slate-800/50 px-2.5 py-1 rounded-md border border-slate-700/40">
          <Radio className="w-3 h-3 text-brand-400 animate-pulse" />
          <span>Surveillance Node #01</span>
        </div>

        {/* Alerts Notification Bell */}
        <div className="relative">
          <button className="p-2 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors relative">
            <Bell className="w-5 h-5" />
            <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-amber-500 rounded-full"></span>
          </button>
        </div>

        {/* Role & User Profile */}
        <div className="flex items-center gap-3 pl-2 border-l border-slate-800">
          <div className={`w-8 h-8 rounded-full flex items-center justify-center text-white font-semibold text-xs shadow-md ${
            currentRole === 'PATIENT'
              ? 'bg-gradient-to-tr from-emerald-600 to-brand-500 shadow-emerald-900/30'
              : 'bg-gradient-to-tr from-brand-600 to-cyan-500 shadow-brand-900/30'
          }`}>
            {currentRole === 'PATIENT' ? 'PT' : 'PH'}
          </div>
          <div className="hidden sm:block text-left">
            <div className="text-xs font-medium text-slate-200">
              {currentRole === 'PATIENT' ? 'Synthetic Patient 101' : 'Dr. Sarah Mitchell'}
            </div>
            <div className="text-[11px] flex items-center gap-1">
              <span className={`font-mono font-semibold ${currentRole === 'PATIENT' ? 'text-emerald-400' : 'text-brand-400'}`}>
                {currentRole === 'PATIENT' ? 'PATIENT PORTAL' : 'OFFICER'}
              </span>
              <span className="text-slate-600">&bull;</span>
              <span className="text-slate-400">
                {currentRole === 'PATIENT' ? 'PAT-SYNTH-101' : 'Surveillance'}
              </span>
            </div>
          </div>

          {onToggleRole && (
            <button
              onClick={onToggleRole}
              title={`Switch role to ${currentRole === 'PATIENT' ? 'OFFICER' : 'PATIENT'}`}
              className="hidden md:flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-[11px] font-medium text-slate-300 border border-slate-700 transition-colors"
            >
              <UserCheck className="w-3 h-3 text-brand-400" />
              <span>{currentRole === 'PATIENT' ? 'Officer View' : 'Patient View'}</span>
            </button>
          )}
        </div>
      </div>
    </header>
  );
};
