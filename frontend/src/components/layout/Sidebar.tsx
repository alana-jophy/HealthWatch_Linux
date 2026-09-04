import React from 'react';
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
  ShieldAlert
} from 'lucide-react';

interface SidebarProps {
  activeTab: string;
  onSelectTab: (tabId: string) => void;
  isOpenMobile: boolean;
  onCloseMobile: () => void;
  currentRole?: 'PATIENT' | 'OFFICER';
  onToggleRole?: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  activeTab,
  onSelectTab,
  isOpenMobile,
  onCloseMobile,
  currentRole = 'PATIENT',
  onToggleRole,
}) => {
  const isPatient = currentRole === 'PATIENT';

  const patientMenuItems = [
    { id: 'patient-dashboard', label: 'My Dashboard', icon: LayoutDashboard },
    { id: 'patient-profile', label: 'My Profile', icon: User },
    { id: 'patient-disease-case', label: 'My Disease Case', icon: Activity },
    { id: 'patient-monitoring', label: 'My Monitoring', icon: UserCheck, badge: 'Consent' },
    { id: 'patient-location-history', label: 'My Location History', icon: Clock },
    { id: 'patient-roadmap', label: 'My Movement Roadmap', icon: Route, badge: '15-min' },
  ];

  const officerMenuItems = [
    { id: 'dashboard', label: 'Surveillance Dashboard', icon: LayoutDashboard },
    { id: 'patient-management', label: 'Patient Management', icon: Users },
    { id: 'disease-management', label: 'Disease Management', icon: Biohazard },
    { id: 'gis', label: 'Geographic Map (GIS)', icon: MapPin },
    { id: 'heatmap', label: 'Disease Hotspot Heatmap', icon: Flame },
    { id: 'movement-analysis', label: 'Movement Analysis', icon: Route },
    { id: 'exposure-analysis', label: 'Exposure Analysis', icon: ShieldAlert },
    { id: 'ai-predictions', label: 'Outbreak Forecaster', icon: BrainCircuit, badge: 'ML' },
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

        {/* Role Switcher */}
        <div className="p-4 border-t border-slate-800 bg-slate-950/60">
          <div className="text-[10px] font-mono uppercase text-slate-500 mb-2 flex items-center justify-between">
            <span>Session Role</span>
            <span className="text-emerald-400 font-bold">{currentRole}</span>
          </div>
          {onToggleRole && (
            <button
              onClick={onToggleRole}
              className="w-full py-2 px-3 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 text-xs font-semibold flex items-center justify-center gap-2 transition-colors"
            >
              <Users className="w-3.5 h-3.5 text-brand-400" />
              <span>Switch to {isPatient ? 'Officer View' : 'Patient View'}</span>
            </button>
          )}
        </div>

        {/* System Node Information Footer */}
        <div className="p-4 border-t border-slate-800 bg-slate-950/40">
          <div className="flex items-center gap-3">
            <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></div>
            <div className="text-xs">
              <div className="font-semibold text-slate-300">{isPatient ? 'Patient Session Active' : 'Node KL-SURV-01'}</div>
              <div className="text-[10px] text-slate-500 font-mono">
                {isPatient ? 'RBAC &bull; Isolated Records' : 'PostGIS SRID:4326 &bull; FastAPI'}
              </div>
            </div>
          </div>
        </div>
      </aside>
    </>
  );
};
