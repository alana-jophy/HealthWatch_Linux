import React, { useState } from 'react';
import { Header } from './Header';
import { Sidebar } from './Sidebar';
import { SystemHealth } from '../../types';
import { useAuth } from '../../context/AuthContext';
import { 
  LayoutDashboard, 
  UserCheck, 
  Route, 
  User, 
  LogOut 
} from 'lucide-react';

interface LayoutProps {
  children: React.ReactNode;
  systemHealth: SystemHealth | null;
  isLoadingHealth: boolean;
  onRefreshHealth: () => void;
  activeTab: string;
  onSelectTab: (tabId: string) => void;
}

export const Layout: React.FC<LayoutProps> = ({
  children,
  systemHealth,
  isLoadingHealth,
  onRefreshHealth,
  activeTab,
  onSelectTab,
}) => {
  const [isSidebarOpenMobile, setIsSidebarOpenMobile] = useState(false);
  const { role, logout } = useAuth();
  const isPatient = role === 'PATIENT';

  const patientMobileNavItems = [
    { id: 'patient-dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { id: 'patient-monitoring', label: 'Monitoring', icon: UserCheck },
    { id: 'patient-roadmap', label: 'Roadmap', icon: Route },
    { id: 'patient-profile', label: 'Profile', icon: User },
  ];

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col antialiased">
      {/* Sidebar navigation for desktop / slide-over mobile */}
      <Sidebar
        activeTab={activeTab}
        onSelectTab={onSelectTab}
        isOpenMobile={isSidebarOpenMobile}
        onCloseMobile={() => setIsSidebarOpenMobile(false)}
      />

      {/* Main Content Area */}
      <div className="lg:pl-72 flex flex-col flex-1 min-w-0">
        <Header
          systemHealth={systemHealth}
          isLoadingHealth={isLoadingHealth}
          onRefreshHealth={onRefreshHealth}
          onToggleSidebar={() => setIsSidebarOpenMobile(!isSidebarOpenMobile)}
        />

        {/* Content with bottom padding on mobile for sticky bottom navigation */}
        <main className={`flex-1 p-3 sm:p-5 md:p-6 lg:p-8 max-w-7xl w-full mx-auto space-y-6 ${
          isPatient ? 'pb-24 sm:pb-8' : 'pb-8'
        }`}>
          {children}
        </main>

        <footer className="border-t border-slate-800/80 px-6 py-4 text-center text-xs text-slate-500 hidden sm:block">
          HealthWatch Intelligent Disease Surveillance System &copy; {new Date().getFullYear()} — MCA Academic Project
        </footer>
      </div>

      {/* ------------------------------------------------------------------ */}
      {/* Mobile-First Sticky Bottom Navigation Bar for Patient on Phone */}
      {/* ------------------------------------------------------------------ */}
      {isPatient && (
        <nav className="sm:hidden fixed bottom-0 left-0 right-0 z-40 bg-slate-900/95 backdrop-blur-xl border-t border-slate-800 px-2 py-1.5 flex items-center justify-around shadow-2xl">
          {patientMobileNavItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => onSelectTab(item.id)}
                className={`flex flex-col items-center justify-center py-1 px-3 rounded-xl transition-all ${
                  isActive
                    ? 'text-emerald-400 font-semibold'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                <div className={`p-1 rounded-lg ${isActive ? 'bg-emerald-500/15' : ''}`}>
                  <Icon className="w-5 h-5" />
                </div>
                <span className="text-[10px] mt-0.5 font-medium tracking-tight">{item.label}</span>
              </button>
            );
          })}

          {/* Quick mobile logout */}
          <button
            onClick={logout}
            className="flex flex-col items-center justify-center py-1 px-3 rounded-xl text-slate-400 hover:text-rose-400 transition-all"
            title="Sign out"
          >
            <div className="p-1 rounded-lg">
              <LogOut className="w-5 h-5" />
            </div>
            <span className="text-[10px] mt-0.5 font-medium tracking-tight">Logout</span>
          </button>
        </nav>
      )}
    </div>
  );
};
