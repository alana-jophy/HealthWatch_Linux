import React, { useState, useEffect } from 'react';
import { Layout } from './components/layout/Layout';
import { GISView } from './components/gis/GISView';
import { PatientMonitoringView } from './components/monitoring/PatientMonitoringView';
import { PatientMovementRoadmap } from './components/monitoring/PatientMovementRoadmap';
import { PatientDashboard } from './components/dashboard/PatientDashboard';
import { PatientProfileView } from './components/patient/PatientProfileView';
import { MyDiseaseCaseView } from './components/patient/MyDiseaseCaseView';
import { PatientLocationHistoryView } from './components/patient/PatientLocationHistoryView';
import { PatientManagementView } from './components/admin/PatientManagementView';
import { DiseaseManagementView } from './components/admin/DiseaseManagementView';
import { MovementAnalysisView } from './components/admin/MovementAnalysisView';
import { UserManagementView } from './components/admin/UserManagementView';
import { OutbreakForecasterView } from './components/admin/OutbreakForecasterView';
import { DiseaseHotspotHeatmap } from './components/gis/DiseaseHotspotHeatmap';
import { SpatialExposureView } from './components/exposure/SpatialExposureView';
import { PublicHealthSurveillanceDashboard } from './components/dashboard/PublicHealthSurveillanceDashboard';
import { SurveillanceReportsView } from './components/reports/SurveillanceReportsView';
import { fetchSystemHealth } from './services/api';
import { SystemHealth } from './types';
import { 
  ShieldCheck, 
  Terminal, 
  Layers
} from 'lucide-react';

export const App: React.FC = () => {
  const [currentRole, setCurrentRole] = useState<'PATIENT' | 'OFFICER'>('PATIENT');
  const [activeTab, setActiveTab] = useState<string>('patient-dashboard');
  const [systemHealth, setSystemHealth] = useState<SystemHealth | null>(null);
  const [isLoadingHealth, setIsLoadingHealth] = useState<boolean>(true);
  const [lastCheckTime, setLastCheckTime] = useState<string>('');

  const loadHealth = async () => {
    setIsLoadingHealth(true);
    try {
      const data = await fetchSystemHealth();
      setSystemHealth(data);
      setLastCheckTime(new Date().toLocaleTimeString());
    } catch (err) {
      console.error('Error querying health:', err);
    } finally {
      setIsLoadingHealth(false);
    }
  };

  useEffect(() => {
    loadHealth();
    // Re-check backend health periodically every 30 seconds
    const interval = setInterval(loadHealth, 30000);
    return () => clearInterval(interval);
  }, []);

  const handleToggleRole = () => {
    if (currentRole === 'PATIENT') {
      setCurrentRole('OFFICER');
      setActiveTab('dashboard');
    } else {
      setCurrentRole('PATIENT');
      setActiveTab('patient-dashboard');
    }
  };

  const isPatient = currentRole === 'PATIENT';

  return (
    <Layout
      systemHealth={systemHealth}
      isLoadingHealth={isLoadingHealth}
      onRefreshHealth={loadHealth}
      activeTab={activeTab}
      onSelectTab={setActiveTab}
      currentRole={currentRole}
      onToggleRole={handleToggleRole}
    >
      {/* Platform Title Banner */}
      <div className="relative overflow-hidden rounded-2xl bg-gradient-to-r from-slate-900 via-slate-900 to-slate-950 border border-slate-800 p-6 md:p-8">
        <div className="absolute right-0 top-0 bottom-0 w-1/3 bg-gradient-to-l from-brand-500/10 to-transparent pointer-events-none"></div>
        <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div className="space-y-2 max-w-2xl">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-brand-500/10 border border-brand-500/20 text-xs font-semibold text-brand-400">
              <ShieldCheck className="w-3.5 h-3.5" />
              <span>
                {isPatient
                  ? 'Patient Surveillance Mode (Role: PATIENT)'
                  : 'Officer Surveillance Mode Active (Role: PUBLIC_HEALTH_OFFICER)'}
              </span>
            </div>
            <h1 className="font-heading text-2xl md:text-3xl font-extrabold text-white tracking-tight">
              {isPatient
                ? 'HealthWatch Patient Surveillance Portal'
                : 'HealthWatch Disease Surveillance & Privacy Framework'}
            </h1>
            <p className="text-sm text-slate-400 leading-relaxed">
              {isPatient
                ? 'Authorized personal health registry, consented periodic location telemetry (approx. 15 mins), and discrete movement observations under strict patient privacy protections.'
                : 'Transparent, patient-consented location monitoring, PostGIS spatial telemetry, and epidemic hotspot surveillance under strict ethical consent controls.'}
            </p>
          </div>

          {/* Telemetry Quick Pill */}
          <div className="bg-slate-950/80 border border-slate-800 p-4 rounded-xl shrink-0 flex flex-col gap-2 min-w-[240px]">
            <div className="flex items-center justify-between text-xs text-slate-400">
              <span className="flex items-center gap-1.5">
                <Terminal className="w-3.5 h-3.5 text-brand-400" />
                <span>Backend Telemetry</span>
              </span>
              <span className="text-[11px] font-mono text-slate-500">{lastCheckTime || 'Syncing...'}</span>
            </div>

            <div className="flex items-center gap-2">
              <div className={`w-2.5 h-2.5 rounded-full ${systemHealth?.status === 'ok' ? 'bg-emerald-500 animate-pulse' : 'bg-rose-500'}`}></div>
              <span className="text-sm font-semibold text-slate-200">
                {systemHealth?.status === 'ok' ? 'FastAPI Gateway Active' : 'Connecting to Gateway...'}
              </span>
            </div>

            <div className="text-[11px] text-slate-400 flex items-center justify-between border-t border-slate-800/80 pt-2">
              <span>Security RBAC:</span>
              <span className="font-mono text-emerald-400 font-semibold">
                {isPatient ? 'Patient Isolated' : 'Officer Authorized'}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content Area based on Role and Tab */}
      {isPatient ? (
        activeTab === 'patient-profile' ? (
          <PatientProfileView />
        ) : activeTab === 'patient-disease-case' ? (
          <MyDiseaseCaseView />
        ) : activeTab === 'patient-monitoring' ? (
          <PatientMonitoringView />
        ) : activeTab === 'patient-location-history' ? (
          <PatientLocationHistoryView />
        ) : activeTab === 'patient-roadmap' ? (
          <PatientMovementRoadmap />
        ) : activeTab === 'patient-dashboard' ? (
          <PatientDashboard onNavigateToRoadmap={() => setActiveTab('patient-roadmap')} />
        ) : (
          /* Restricted Administrative View for Patients */
          <div className="glass-panel rounded-2xl p-10 text-center flex flex-col items-center justify-center space-y-4">
            <div className="w-14 h-14 rounded-2xl bg-rose-500/10 border border-rose-500/30 flex items-center justify-center text-rose-400">
              <ShieldCheck className="w-7 h-7" />
            </div>
            <div className="max-w-md">
              <h2 className="font-heading text-lg font-bold text-white">
                Restricted to Health Officers
              </h2>
              <p className="text-xs text-slate-400 mt-1">
                This administrative module is not accessible in Patient mode. When authenticated as PATIENT, only patient-specific information is shown.
              </p>
            </div>
            <button
              onClick={() => setActiveTab('patient-dashboard')}
              className="px-4 py-2 bg-brand-600 hover:bg-brand-500 text-white rounded-xl text-xs font-semibold shadow-md transition-colors"
            >
              Return to My Dashboard
            </button>
          </div>
        )
      ) : (
        /* OFFICER / ADMIN Views */
        activeTab === 'dashboard' ? (
          <PublicHealthSurveillanceDashboard />
        ) : activeTab === 'patient-management' ? (
          <PatientManagementView />
        ) : activeTab === 'disease-management' ? (
          <DiseaseManagementView />
        ) : activeTab === 'gis font-bold' || activeTab === 'gis' ? (
          <GISView />
        ) : activeTab === 'heatmap font-bold' || activeTab === 'heatmap' || activeTab === 'hotspots' ? (
          <DiseaseHotspotHeatmap />
        ) : activeTab === 'movement-analysis' ? (
          <MovementAnalysisView />
        ) : activeTab === 'exposure-analysis' || activeTab === 'exposure-tracking' ? (
          <SpatialExposureView />
        ) : activeTab === 'ai-predictions' ? (
          <OutbreakForecasterView />
        ) : activeTab === 'reports' ? (
          <SurveillanceReportsView />
        ) : activeTab === 'user-management' ? (
          <UserManagementView />
        ) : (
          <PublicHealthSurveillanceDashboard />
        )
      )}
    </Layout>
  );
};
