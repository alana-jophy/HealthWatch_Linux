import React, { useState } from 'react';
import { PatientMovementRoadmap } from '../monitoring/PatientMovementRoadmap';
import {
  Route,
  Search,
  Filter,
  User,
  ShieldCheck,
  Calendar,
  Layers,
  ChevronRight
} from 'lucide-react';

export const MovementAnalysisView: React.FC = () => {
  const [selectedPatientId, setSelectedPatientId] = useState<string>('PAT-SYNTH-101');
  const [inputPseudoId, setInputPseudoId] = useState<string>('PAT-SYNTH-101');
  const [filterDate, setFilterDate] = useState<string>('');

  const handleApplyFilter = (e: React.FormEvent) => {
    e.preventDefault();
    if (inputPseudoId.trim()) {
      setSelectedPatientId(inputPseudoId.trim());
    }
  };

  const samplePatients = [
    { pseudo: 'PAT-SYNTH-101', name: 'Synthetic Patient 101 (Palayam Cluster)' },
    { pseudo: 'PAT-SYNTH-102', name: 'Synthetic Patient 102 (Medical College)' },
    { pseudo: 'PAT-SYNTH-103', name: 'Synthetic Patient 103 (Marine Drive)' },
    { pseudo: 'PAT-SYNTH-104', name: 'Synthetic Patient 104 (Pattom)' },
  ];

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
              <h2 className="font-heading text-xl font-bold text-white">Movement Analysis Portal</h2>
              <span className="px-2.5 py-0.5 rounded-full text-xs font-mono font-bold bg-brand-500/15 text-brand-400 border border-brand-500/30">
                Epidemiological Contact Tracing
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-0.5">
              Inspect time-stamped location observation roadmaps and polyline trajectory for authorized patient surveillance
            </p>
          </div>
        </div>
      </div>

      {/* Patient Selection Toolbar */}
      <div className="glass-panel p-5 rounded-2xl space-y-4">
        <div className="text-xs font-semibold text-slate-300 flex items-center gap-2">
          <Filter className="w-4 h-4 text-brand-400" />
          <span>Patient Selection & Date Controls</span>
        </div>

        <form onSubmit={handleApplyFilter} className="flex flex-col md:flex-row items-center gap-3">
          <div className="flex-1 w-full flex items-center gap-2">
            <div className="relative flex-1">
              <Search className="w-4 h-4 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                value={inputPseudoId}
                onChange={(e) => setInputPseudoId(e.target.value)}
                placeholder="Enter Patient Pseudo ID (e.g. PAT-SYNTH-101)..."
                className="w-full pl-9 pr-4 py-2.5 bg-slate-900/80 border border-slate-800 rounded-xl text-xs text-white placeholder-slate-500 focus:outline-none focus:border-brand-500 transition-colors font-mono"
              />
            </div>

            <input
              type="date"
              value={filterDate}
              onChange={(e) => setFilterDate(e.target.value)}
              className="py-2.5 px-3 bg-slate-900/80 border border-slate-800 rounded-xl text-xs text-slate-200 focus:outline-none focus:border-brand-500"
            />
          </div>

          <button
            type="submit"
            className="w-full md:w-auto px-5 py-2.5 bg-brand-600 hover:bg-brand-500 text-white rounded-xl text-xs font-semibold shadow-md transition-colors shrink-0 flex items-center justify-center gap-2"
          >
            <span>Analyze Patient Route</span>
            <ChevronRight className="w-4 h-4" />
          </button>
        </form>

        {/* Quick Sample Patient Buttons */}
        <div className="flex items-center gap-2 overflow-x-auto pt-2 border-t border-slate-800/80">
          <span className="text-[10px] font-mono text-slate-500 uppercase shrink-0">Sample Cohort:</span>
          {samplePatients.map((sp) => (
            <button
              key={sp.pseudo}
              onClick={() => {
                setInputPseudoId(sp.pseudo);
                setSelectedPatientId(sp.pseudo);
              }}
              className={`px-3 py-1 rounded-lg text-xs font-mono font-medium transition-colors shrink-0 border ${
                selectedPatientId === sp.pseudo
                  ? 'bg-brand-500/20 text-brand-300 border-brand-500/40'
                  : 'bg-slate-900 text-slate-400 border-slate-800 hover:bg-slate-800 hover:text-white'
              }`}
            >
              {sp.pseudo}
            </button>
          ))}
        </div>
      </div>

      {/* Embed PatientMovementRoadmap Component */}
      <PatientMovementRoadmap
        isOfficerMode={true}
        officerPatientPseudoId={selectedPatientId}
        officerFilterDate={filterDate || undefined}
      />
    </div>
  );
};
