import React, { useState } from 'react';
import { Header } from './Header';
import { Sidebar } from './Sidebar';
import { SystemHealth } from '../../types';

interface LayoutProps {
  children: React.ReactNode;
  systemHealth: SystemHealth | null;
  isLoadingHealth: boolean;
  onRefreshHealth: () => void;
  activeTab: string;
  onSelectTab: (tabId: string) => void;
  currentRole?: 'PATIENT' | 'OFFICER';
  onToggleRole?: () => void;
}

export const Layout: React.FC<LayoutProps> = ({
  children,
  systemHealth,
  isLoadingHealth,
  onRefreshHealth,
  activeTab,
  onSelectTab,
  currentRole = 'PATIENT',
  onToggleRole,
}) => {
  const [isSidebarOpenMobile, setIsSidebarOpenMobile] = useState(false);

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col antialiased">
      {/* Sidebar navigation */}
      <Sidebar
        activeTab={activeTab}
        onSelectTab={onSelectTab}
        isOpenMobile={isSidebarOpenMobile}
        onCloseMobile={() => setIsSidebarOpenMobile(false)}
        currentRole={currentRole}
        onToggleRole={onToggleRole}
      />

      {/* Main Container shifted right on large viewports */}
      <div className="lg:pl-72 flex flex-col flex-1 min-w-0">
        <Header
          systemHealth={systemHealth}
          isLoadingHealth={isLoadingHealth}
          onRefreshHealth={onRefreshHealth}
          onToggleSidebar={() => setIsSidebarOpenMobile(!isSidebarOpenMobile)}
          currentRole={currentRole}
          onToggleRole={onToggleRole}
        />

        <main className="flex-1 p-4 md:p-6 lg:p-8 max-w-7xl w-full mx-auto space-y-6">
          {children}
        </main>

        <footer className="border-t border-slate-800/80 px-6 py-4 text-center text-xs text-slate-500">
          HealthWatch Intelligent Disease Surveillance System &copy; {new Date().getFullYear()} — MCA Project Framework
        </footer>
      </div>
    </div>
  );
};
