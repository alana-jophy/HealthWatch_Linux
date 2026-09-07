import React from 'react';
import { useAuth } from '../../context/AuthContext';
import { 
  Bell, 
  Menu,
  Radio,
  Server,
  LogOut,
  ShieldCheck,
  UserCheck
} from 'lucide-react';
import { SystemHealth } from '../../types';
import { InstallAppButton } from '../common/InstallAppButton';

interface HeaderProps {
  systemHealth: SystemHealth | null;
  isLoadingHealth: boolean;
  onRefreshHealth: () => void;
  onToggleSidebar: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  systemHealth,
  isLoadingHealth,
  onRefreshHealth,
  onToggleSidebar,
}) => {
  const { user, role, logout } = useAuth();
  const isBackendUp = systemHealth?.status === 'ok';
  const isDbConnected = systemHealth?.database?.status === 'connected';
  const isPatient = role === 'PATIENT';

  return (
    <header className="h-16 bg-slate-900/80 backdrop-blur-md border-b border-slate-800 sticky top-0 z-30 px-4 lg:px-6 flex items-center justify-between">
      {/* Left section: Mobile menu trigger & Platform Title */}
      <div className="flex items-center gap-3">
        <button
          onClick={onToggleSidebar}
          className="lg:hidden p-2 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors"
          title="Toggle Navigation"
        >
          <Menu className="w-5 h-5" />
        </button>

        <div className="flex items-center gap-2">
          <span className="font-heading font-bold text-white tracking-wide text-sm sm:text-base hidden sm:inline">
            Health<span className="text-brand-400">Watch</span>
          </span>
          <span className={`text-[10px] font-mono px-2 py-0.5 rounded-full font-bold uppercase tracking-wider ${
            isPatient
              ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30'
              : 'bg-brand-500/15 text-brand-400 border border-brand-500/30'
          }`}>
            {isPatient ? 'Patient Portal' : 'Surveillance Officer'}
          </span>
        </div>
      </div>

      {/* Right section: System Telemetry & User Controls */}
      <div className="flex items-center gap-3">
        {/* Backend & PostGIS Health Status Badge */}
        <button
          onClick={onRefreshHealth}
          disabled={isLoadingHealth}
          title="Click to re-check backend & PostGIS telemetry"
          className="hidden md:flex items-center gap-2 px-3 py-1.5 rounded-full bg-slate-950/70 border border-slate-800 hover:border-slate-700 text-xs transition-all"
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

          <span className="text-slate-300 font-medium hidden lg:inline text-[11px]">
            {isBackendUp && isDbConnected ? 'PostGIS Online' : 'Connecting DB...'}
          </span>
          <Server className={`w-3 h-3 text-slate-400 ${isLoadingHealth ? 'animate-spin' : ''}`} />
        </button>

        {/* PWA Install Button for mobile/phone access */}
        <InstallAppButton variant="header" />

        {/* User Identity Details */}
        <div className="flex items-center gap-2.5 pl-2 border-l border-slate-800">
          <div className={`w-8 h-8 rounded-full flex items-center justify-center text-white font-semibold text-xs shadow-md shrink-0 ${
            isPatient
              ? 'bg-gradient-to-tr from-emerald-600 to-brand-500'
              : 'bg-gradient-to-tr from-brand-600 to-cyan-500'
          }`}>
            {user?.full_name ? user.full_name.substring(0, 2).toUpperCase() : 'HW'}
          </div>

          <div className="hidden sm:block text-left">
            <div className="text-xs font-semibold text-slate-200 truncate max-w-[140px]">
              {user?.full_name || 'User'}
            </div>
            <div className="text-[10px] text-slate-400 font-mono truncate max-w-[140px]">
              {user?.email}
            </div>
          </div>

          {/* Logout Button */}
          <button
            onClick={logout}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-slate-800 hover:bg-rose-950/40 text-slate-300 hover:text-rose-300 border border-slate-700 hover:border-rose-500/30 text-xs font-semibold transition-all shadow-sm"
            title="Sign out of HealthWatch"
          >
            <LogOut className="w-3.5 h-3.5 text-rose-400" />
            <span className="hidden sm:inline">Logout</span>
          </button>
        </div>
      </div>
    </header>
  );
};
