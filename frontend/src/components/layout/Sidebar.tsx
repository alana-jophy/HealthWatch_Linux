import React from 'react';
import { useAuth } from '../../context/AuthContext';
import {
  LayoutDashboard,
  MapPin,
  Flame,
  Users,
  Route,
  FileText,
  BrainCircuit,
  Shield,
  ShieldCheck,
  X,
  UserCheck,
  User,
  Activity,
  Clock,
  Biohazard,
  ShieldAlert,
  LogOut
} from 'lucide-react';

interface SidebarProps {
  activeTab: string;
  onSelectTab: (tabId: string) => void;
  isOpenMobile: boolean;
  onCloseMobile: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  activeTab,
  onSelectTab,
  isOpenMobile,
  onCloseMobile,
}) => {
  const { user, role, logout } = useAuth();
  const isPatient = role === 'PATIENT';

  const patientMenuItems = [
    { id: 'patient-dashboard', label: 'My Dashboard', icon: LayoutDashboard },
    { id: 'patient-profile', label: 'My Profile', icon: User },
    { id: 'patient-disease-case', label: 'My Health Info', icon: Activity },
    { id: 'patient-monitoring', label: 'My Monitoring', icon: UserCheck, badge: 'Real GPS' },
    { id: 'patient-location-history', label: 'My Location History', icon: Clock },
    { id: 'patient-roadmap', label: 'My Movement Roadmap', icon: Route, badge: '15-min' },
  ];

  const officerMenuItems = [
    { id: 'dashboard', label: 'Surveillance Dashboard', icon: LayoutDashboard },
    { id: 'patient-management', label: 'Patient Management', icon: Users, badge: 'CRUD' },
    { id: 'disease-management', label: 'Disease Management', icon: Biohazard },
    { id: 'movement-analysis', label: 'Movement Analysis', icon: Route },
    { id: 'reports', label: 'Surveillance Reports', icon: FileText },
    { id: 'user-management', label: 'User Management', icon: ShieldCheck },
  ];

  const menuItems = isPatient ? patientMenuItems : officerMenuItems;

  return (
    <>
      {/* Mobile Backdrop */}
      {isOpenMobile && (
        <div
          onClick={onCloseMobile}
          className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm z-40 lg:hidden"
        />
      )}

      {/* Sidebar Container */}
      <aside
        className={`
          fixed top-0 bottom-0 left-0 z-50 w-72 bg-slate-900 border-r border-slate-800 
          flex flex-col transition-transform duration-300 ease-in-out
          lg:translate-x-0 ${isOpenMobile ? 'translate-x-0' : '-translate-x-full'}
        `}
      >
        {/* Brand Header */}
        <div className="h-16 px-6 border-b border-slate-800 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-brand-500/20 border border-brand-500/40 flex items-center justify-center text-brand-400">
              <Shield className="w-4 h-4" />
            </div>
            <div>
              <span className="font-heading font-bold text-base text-white tracking-wide">
                Health<span className="text-brand-400">Watch</span>
              </span>
              <span className="block text-[10px] text-slate-500 font-mono tracking-tighter">
                {isPatient ? 'PATIENT PORTAL' : 'SURVEILLANCE NODE v1.0'}
              </span>
            </div>
          </div>

          <button
            onClick={onCloseMobile}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 lg:hidden"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Navigation Menu */}
        <div className="flex-1 overflow-y-auto px-4 py-6 space-y-1">
          <div className="px-3 pb-2 text-[11px] font-semibold text-slate-500 tracking-wider uppercase font-mono">
            {isPatient ? 'Patient Services' : 'Surveillance Core'}
          </div>

          {menuItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;

            return (
              <button
                key={item.id}
                onClick={() => {
                  onSelectTab(item.id);
                  onCloseMobile();
                }}
                className={`
                  w-full flex items-center justify-between px-3 py-2.5 rounded-xl text-xs font-medium 
                  transition-all duration-150 group
                  ${
                    isActive
                      ? 'bg-brand-500/15 text-brand-400 border border-brand-500/30 shadow-sm shadow-brand-500/10'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
                  }
                `}
              >
                <div className="flex items-center gap-3">
                  <Icon
                    className={`w-4 h-4 transition-colors ${
                      isActive ? 'text-brand-400' : 'text-slate-500 group-hover:text-slate-300'
                    }`}
                  />
                  <span>{item.label}</span>
                </div>

                {item.badge && (
                  <span
                    className={`
                      text-[10px] px-1.5 py-0.5 rounded font-mono font-medium tracking-tight
                      ${
                        isActive
                          ? 'bg-brand-500/30 text-brand-300'
                          : 'bg-slate-800 text-slate-400 group-hover:bg-slate-700 text-slate-300'
                      }
                    `}
                  >
                    {item.badge}
                  </span>
                )}
              </button>
            );
          })}
        </div>

        {/* User Profile & Sign Out Footer */}
        <div className="p-4 border-t border-slate-800 bg-slate-950/60 space-y-3">
          <div className="flex items-center gap-3">
            <div className={`w-8 h-8 rounded-full flex items-center justify-center text-white font-semibold text-xs shrink-0 ${
              isPatient
                ? 'bg-gradient-to-tr from-emerald-600 to-brand-500'
                : 'bg-gradient-to-tr from-brand-600 to-cyan-500'
            }`}>
              {user?.full_name ? user.full_name.substring(0, 2).toUpperCase() : 'HW'}
            </div>
            <div className="min-w-0 flex-1">
              <div className="text-xs font-semibold text-white truncate">
                {user?.full_name || 'Authenticated User'}
              </div>
              <div className="text-[10px] font-mono text-slate-400 truncate">
                {user?.email || 'user@healthwatch.org'}
              </div>
            </div>
          </div>

          <button
            onClick={logout}
            className="w-full py-2 px-3 rounded-xl bg-slate-800 hover:bg-rose-950/40 text-slate-300 hover:text-rose-300 border border-slate-700 hover:border-rose-500/30 text-xs font-semibold flex items-center justify-center gap-2 transition-all shadow-sm"
          >
            <LogOut className="w-3.5 h-3.5 text-rose-400" />
            <span>Sign Out</span>
          </button>
        </div>
      </aside>
    </>
  );
};
