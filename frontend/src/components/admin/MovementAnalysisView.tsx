import React, { useState, useEffect } from 'react';
import { PatientMovementRoadmap } from '../monitoring/PatientMovementRoadmap';
import { fetchPatientsList } from '../../services/api';
import { PatientProfile } from '../../types';
import {
  Route,
  Filter,
  User,
  Calendar,
  AlertCircle
} from 'lucide-react';

export const MovementAnalysisView: React.FC = () => {
  const [patients, setPatients] = useState<PatientProfile[]>([]);
  const [selectedPatientPseudoId, setSelectedPatientPseudoId] = useState<string>('');
  const [filterDate, setFilterDate] = useState<string>('');
  const [isLoadingPatients, setIsLoadingPatients] = useState<boolean>(true);

  useEffect(() => {
    const loadPatients = async () => {
      try {
        setIsLoadingPatients(true);
        const res = await fetchPatientsList();
        if (res && res.items) {
          setPatients(res.items);
        }
      } catch (err) {
        console.error('Error loading patient list for movement analysis:', err);
      } finally {
        setIsLoadingPatients(false);
      }
    };
    loadPatients();
  }, []);

  const selectedPatient = patients.find(p => p.pseudo_id === selectedPatientPseudoId);

  return (
    <div className="space-y-6">
      {/* Officer Movement Analysis Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 glass-panel p-6 rounded-2xl">
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-2xl bg-brand-500/15 border border-brand-500/30 flex items-center justify-center text-brand-400">
            <Route className="w-6 h-6" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="font-heading text-xl font-bold text-white">Movement Analysis</h2>
              <span className="px-2.5 py-0.5 rounded-full text-xs font-mono font-bold bg-brand-500/15 text-brand-400 border border-brand-500/30">
                Epidemiological Surveillance
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-0.5">
              Inspect time-stamped location observation roadmaps and discrete movement sequences for registered patients
            </p>
          </div>
        </div>
      </div>

      {/* Patient Selection & Date Toolbar */}
      <div className="glass-panel p-5 rounded-2xl space-y-4">
        <div className="text-xs font-semibold text-slate-300 flex items-center gap-2">
          <Filter className="w-4 h-4 text-brand-400" />
          <span>Patient & Date Selection</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Patient Dropdown */}
          <div className="space-y-1.5">
            <label className="block text-[11px] font-medium text-slate-400 flex items-center gap-1.5">
              <User className="w-3.5 h-3.5 text-brand-400" />
              <span>Select Registered Patient</span>
            </label>
            <select
              value={selectedPatientPseudoId}
              onChange={(e) => setSelectedPatientPseudoId(e.target.value)}
              disabled={isLoadingPatients}
              className="w-full py-2.5 px-3 bg-slate-900/80 border border-slate-800 rounded-xl text-xs text-white focus:outline-none focus:border-brand-500 transition-colors"
            >
              {isLoadingPatients ? (
                <option value="">Loading registered patients...</option>
              ) : patients.length === 0 ? (
                <option value="">No registered patients found</option>
              ) : (
                <>
                  <option value="">-- Select a patient to inspect --</option>
                  {patients.map((p) => (
                    <option key={p.id} value={p.pseudo_id}>
                      {p.full_name} ({p.pseudo_id}) — {p.disease_name || 'Case'} | {p.has_phone ? 'GPS Telemetry' : 'No Phone (Centroid)'}
                    </option>
                  ))}
                </>
              )}
            </select>
          </div>

          {/* Date Filter */}
          <div className="space-y-1.5">
            <label className="block text-[11px] font-medium text-slate-400 flex items-center gap-1.5">
              <Calendar className="w-3.5 h-3.5 text-brand-400" />
              <span>Filter by Date (Optional)</span>
            </label>
            <div className="flex items-center gap-2">
              <input
                type="date"
                value={filterDate}
                onChange={(e) => setFilterDate(e.target.value)}
                className="flex-1 py-2.5 px-3 bg-slate-900/80 border border-slate-800 rounded-xl text-xs text-slate-200 focus:outline-none focus:border-brand-500"
              />
              {filterDate && (
                <button
                  type="button"
                  onClick={() => setFilterDate('')}
                  className="px-3 py-2.5 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs rounded-xl font-medium transition-colors"
                >
                  Clear
                </button>
              )}
            </div>
          </div>
        </div>

        {selectedPatient && !selectedPatient.has_phone && (
          <div className="p-3 bg-amber-500/10 border border-amber-500/30 rounded-xl text-xs text-amber-300 flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0 text-amber-400" />
            <span>
              This patient is registered without a smartphone. Showing official administrative centroid for their registered location.
            </span>
          </div>
        )}
      </div>

      {/* Embed PatientMovementRoadmap Component */}
      {selectedPatientPseudoId ? (
        <PatientMovementRoadmap
          isOfficerMode={true}
          officerPatientPseudoId={selectedPatientPseudoId}
          officerFilterDate={filterDate || undefined}
        />
      ) : (
        <div className="glass-panel p-12 rounded-2xl text-center text-slate-400">
          <Route className="w-8 h-8 mx-auto mb-2 text-slate-600" />
          <p className="text-sm">Select a patient to view movement observations.</p>
        </div>
      )}
    </div>
  );
};
