import React, { useState, useEffect } from 'react';
import { fetchMyPatientProfile } from '../../services/api';
import { PatientProfile } from '../../types';
import {
  User,
  Shield,
  Phone,
  Home,
  MapPin,
  Calendar,
  UserCheck,
  RefreshCw,
  AlertCircle,
  CheckCircle2,
  Lock
} from 'lucide-react';

export const PatientProfileView: React.FC = () => {
  const [profile, setProfile] = useState<PatientProfile | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const loadProfile = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await fetchMyPatientProfile();
      setProfile(data);
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to retrieve patient profile record.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadProfile();
  }, []);

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 glass-panel p-6 rounded-2xl">
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-2xl bg-brand-500/15 border border-brand-500/30 flex items-center justify-center text-brand-400">
            <User className="w-6 h-6" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="font-heading text-xl font-bold text-white">My Patient Profile</h2>
              <span className="px-2 py-0.5 rounded-md text-[10px] font-mono font-bold bg-emerald-500/15 border border-emerald-500/30 text-emerald-400">
                VERIFIED PATIENT
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-0.5">
              Personal demographic, residence, and assigned field worker information
            </p>
          </div>
        </div>

        <button
          onClick={loadProfile}
          disabled={isLoading}
          className="inline-flex items-center gap-2 px-3.5 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold border border-slate-700 transition-colors disabled:opacity-50"
        >
          <RefreshCw className={`w-3.5 h-3.5 text-brand-400 ${isLoading ? 'animate-spin' : ''}`} />
          <span>Refresh Profile</span>
        </button>
      </div>

      {/* State Handlers */}
      {isLoading ? (
        <div className="glass-panel p-12 rounded-2xl text-center space-y-3">
          <RefreshCw className="w-8 h-8 text-brand-400 animate-spin mx-auto" />
          <p className="text-sm font-medium text-slate-300">Retrieving patient record...</p>
        </div>
      ) : error ? (
        <div className="glass-panel p-8 rounded-2xl border-rose-500/30 bg-rose-950/10 text-center space-y-3">
          <AlertCircle className="w-8 h-8 text-rose-400 mx-auto" />
          <h3 className="text-base font-semibold text-rose-300">Profile Loading Error</h3>
          <p className="text-xs text-slate-400 max-w-md mx-auto">{error}</p>
          <button
            onClick={loadProfile}
            className="px-4 py-2 rounded-xl bg-rose-600 hover:bg-rose-500 text-white text-xs font-semibold"
          >
            Retry
          </button>
        </div>
      ) : !profile ? (
        <div className="glass-panel p-12 rounded-2xl text-center space-y-3">
          <User className="w-10 h-10 text-slate-600 mx-auto" />
          <p className="text-sm font-medium text-slate-400">No active patient profile found.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Main Card */}
          <div className="lg:col-span-2 glass-panel p-6 rounded-2xl space-y-6">
            <div className="flex items-center justify-between border-b border-slate-800 pb-4">
              <div>
                <span className="text-[10px] font-mono font-semibold uppercase text-slate-500">
                  Pseudo Identity Code
                </span>
                <div className="text-2xl font-mono font-extrabold text-brand-400 mt-0.5">
                  {profile.pseudo_id}
                </div>
              </div>
              <div className="text-right">
                <span className="text-[10px] font-mono font-semibold uppercase text-slate-500">
                  Account Status
                </span>
                <div className="flex items-center gap-1.5 text-emerald-400 font-semibold text-xs mt-1">
                  <CheckCircle2 className="w-4 h-4" />
                  <span>Active Surveillance</span>
                </div>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 space-y-1">
                <span className="text-[11px] font-medium text-slate-400 flex items-center gap-1.5">
                  <User className="w-3.5 h-3.5 text-brand-400" /> Full Name
                </span>
                <div className="text-sm font-bold text-white">{profile.full_name}</div>
              </div>

              <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 space-y-1">
                <span className="text-[11px] font-medium text-slate-400 flex items-center gap-1.5">
                  <Calendar className="w-3.5 h-3.5 text-brand-400" /> Age & Gender
                </span>
                <div className="text-sm font-bold text-white">
                  {profile.age} Years &bull; {profile.gender}
                </div>
              </div>

              <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 space-y-1">
                <span className="text-[11px] font-medium text-slate-400 flex items-center gap-1.5">
                  <Phone className="w-3.5 h-3.5 text-brand-400" /> Contact Number
                </span>
                <div className="text-sm font-mono font-bold text-white">{profile.contact_number}</div>
              </div>

              <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 space-y-1">
                <span className="text-[11px] font-medium text-slate-400 flex items-center gap-1.5">
                  <UserCheck className="w-3.5 h-3.5 text-brand-400" /> Assigned Health Worker
                </span>
                <div className="text-sm font-bold text-white">
                  {profile.assigned_worker_name || 'Rajesh Kumar (Field Surveillance Officer)'}
                </div>
              </div>
            </div>

            {/* Address & Geographic Hierarchy */}
            <div className="p-5 rounded-xl bg-slate-900/60 border border-slate-800 space-y-3">
              <div className="flex items-center gap-2 text-xs font-semibold text-slate-300">
                <Home className="w-4 h-4 text-brand-400" />
                <span>Residence & Administrative Boundaries</span>
              </div>
              <div className="text-sm text-slate-200">{profile.address}</div>
              <div className="grid grid-cols-3 gap-2 pt-2 border-t border-slate-800/80 text-xs">
                <div>
                  <span className="text-[10px] text-slate-500 block">District</span>
                  <span className="font-semibold text-slate-300">{profile.district_name}</span>
                </div>
                <div>
                  <span className="text-[10px] text-slate-500 block">Local Body</span>
                  <span className="font-semibold text-slate-300">{profile.local_body_name}</span>
                </div>
                <div>
                  <span className="text-[10px] text-slate-500 block">Ward Number</span>
                  <span className="font-mono font-semibold text-brand-400">Ward #{profile.ward_number}</span>
                </div>
              </div>
            </div>
          </div>

          {/* Side Info & Privacy Guarantee */}
          <div className="space-y-6">
            <div className="glass-panel p-6 rounded-2xl space-y-4">
              <div className="flex items-center gap-2.5 text-sm font-bold text-white">
                <Shield className="w-4 h-4 text-emerald-400" />
                <span>Privacy & Governance</span>
              </div>
              <p className="text-xs text-slate-400 leading-relaxed">
                Your personal health data is protected under HealthWatch role-based access rules (RBAC). 
                Administrative access is restricted to authorized public health officers for contact tracing.
              </p>
              <div className="p-3.5 rounded-xl bg-slate-950/80 border border-slate-800 space-y-2 text-xs">
                <div className="flex items-center justify-between text-slate-300">
                  <span className="flex items-center gap-1.5">
                    <Lock className="w-3.5 h-3.5 text-brand-400" /> Identity Protection
                  </span>
                  <span className="font-mono text-emerald-400 font-bold">Pseudo-ID</span>
                </div>
                <div className="flex items-center justify-between text-slate-300">
                  <span className="flex items-center gap-1.5">
                    <MapPin className="w-3.5 h-3.5 text-brand-400" /> Telemetry Scope
                  </span>
                  <span className="font-mono text-brand-300 font-bold">15-min Interval</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
