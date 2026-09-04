import React, { useState, useEffect } from 'react';
import { fetchPatientsList, fetchDistricts, createPatientRecord } from '../../services/api';
import { PatientProfile, DistrictGIS } from '../../types';
import {
  Users,
  Search,
  Filter,
  RefreshCw,
  AlertCircle,
  UserCheck,
  MapPin,
  CheckCircle2,
  XCircle,
  Eye,
  Building,
  Calendar,
  Plus,
  UserPlus,
  X
} from 'lucide-react';

export const PatientManagementView: React.FC = () => {
  const [patients, setPatients] = useState<PatientProfile[]>([]);
  const [total, setTotal] = useState<number>(0);
  const [districts, setDistricts] = useState<DistrictGIS[]>([]);
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [selectedDistrict, setSelectedDistrict] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const [selectedPatient, setSelectedPatient] = useState<PatientProfile | null>(null);
  const [showAddModal, setShowAddModal] = useState<boolean>(false);
  const [addLoading, setAddLoading] = useState<boolean>(false);
  const [addError, setAddError] = useState<string | null>(null);
  const [addSuccess, setAddSuccess] = useState<string | null>(null);

  const [formData, setFormData] = useState({
    pseudo_id: `PAT-USER-${Math.floor(100 + Math.random() * 900)}`,
    full_name: '',
    age: 28,
    gender: 'FEMALE',
    contact_number: '+91-98470-',
    address: 'Kerala Residency, Ward 1',
    district_name: 'Thiruvananthapuram',
    local_body_name: 'Thiruvananthapuram Municipal Corporation',
    ward_number: 1,
  });

  const loadData = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [distRes, patRes] = await Promise.all([
        fetchDistricts().catch(() => []),
        fetchPatientsList(searchQuery, selectedDistrict || undefined),
      ]);
      setDistricts(distRes);
      setPatients(patRes.items);
      setTotal(patRes.total);
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to fetch patient registry records.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [selectedDistrict]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    loadData();
  };

  const handleCreatePatient = async (e: React.FormEvent) => {
    e.preventDefault();
    setAddLoading(true);
    setAddError(null);
    setAddSuccess(null);
    try {
      const newPatient = await createPatientRecord({
        pseudo_id: formData.pseudo_id.trim(),
        full_name: formData.full_name.trim(),
        age: Number(formData.age),
        gender: formData.gender,
        contact_number: formData.contact_number.trim(),
        address: formData.address.trim(),
        district_name: formData.district_name,
        local_body_name: formData.local_body_name,
        ward_number: Number(formData.ward_number),
      });

      setAddSuccess(`Patient record ${newPatient.pseudo_id} (${newPatient.full_name}) registered successfully!`);
      // Reset form ID for next entry
      setFormData((prev) => ({
        ...prev,
        pseudo_id: `PAT-USER-${Math.floor(100 + Math.random() * 900)}`,
        full_name: '',
      }));
      await loadData();
      setTimeout(() => {
        setShowAddModal(false);
        setAddSuccess(null);
      }, 1500);
    } catch (err: any) {
      setAddError(err?.response?.data?.detail || 'Failed to register patient record. Please verify fields.');
    } finally {
      setAddLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 glass-panel p-6 rounded-2xl">
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-2xl bg-brand-500/15 border border-brand-500/30 flex items-center justify-center text-brand-400">
            <Users className="w-6 h-6" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="font-heading text-xl font-bold text-white">Patient Management Registry</h2>
              <span className="px-2.5 py-0.5 rounded-full text-xs font-mono font-bold bg-brand-500/15 text-brand-400 border border-brand-500/30">
                {total} Records
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-0.5">
              Public health surveillance patient directory, demographic records, and field worker assignments
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => setShowAddModal(true)}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-brand-600 hover:bg-brand-500 text-white text-xs font-semibold shadow-md transition-colors"
          >
            <UserPlus className="w-4 h-4" />
            <span>Add Patient Record</span>
          </button>

          <button
            onClick={loadData}
            disabled={isLoading}
            className="inline-flex items-center gap-2 px-3.5 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold border border-slate-700 transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 text-brand-400 ${isLoading ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* Filter and Search Toolbar */}
      <div className="glass-panel p-4 rounded-2xl flex flex-col md:flex-row items-center justify-between gap-4">
        <form onSubmit={handleSearchSubmit} className="flex-1 w-full flex items-center gap-2">
          <div className="relative flex-1">
            <Search className="w-4 h-4 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search by Pseudo ID, patient name, address..."
              className="w-full pl-9 pr-4 py-2 bg-slate-900/80 border border-slate-800 rounded-xl text-xs text-white placeholder-slate-500 focus:outline-none focus:border-brand-500 transition-colors"
            />
          </div>
          <button
            type="submit"
            className="px-4 py-2 bg-brand-600 hover:bg-brand-500 text-white rounded-xl text-xs font-semibold shadow-sm transition-colors shrink-0"
          >
            Search
          </button>
        </form>

        <div className="flex items-center gap-3 w-full md:w-auto shrink-0">
          <div className="flex items-center gap-2 text-xs text-slate-400">
            <Filter className="w-3.5 h-3.5 text-brand-400" />
            <span>District:</span>
          </div>
          <select
            value={selectedDistrict}
            onChange={(e) => setSelectedDistrict(e.target.value)}
            className="bg-slate-900/80 border border-slate-800 text-xs text-slate-200 rounded-xl px-3 py-2 focus:outline-none focus:border-brand-500 transition-colors"
          >
            <option value="">All Districts in Kerala</option>
            {districts.map((d) => (
              <option key={d.id} value={d.name}>
                {d.name}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* State Handlers */}
      {isLoading ? (
        <div className="glass-panel p-12 rounded-2xl text-center space-y-3">
          <RefreshCw className="w-8 h-8 text-brand-400 animate-spin mx-auto" />
          <p className="text-sm font-medium text-slate-300">Loading patient registry records...</p>
        </div>
      ) : error ? (
        <div className="glass-panel p-8 rounded-2xl border-rose-500/30 bg-rose-950/10 text-center space-y-3">
          <AlertCircle className="w-8 h-8 text-rose-400 mx-auto" />
          <h3 className="text-base font-semibold text-rose-300">Failed to Load Patients</h3>
          <p className="text-xs text-slate-400 max-w-md mx-auto">{error}</p>
          <button
            onClick={loadData}
            className="px-4 py-2 rounded-xl bg-rose-600 hover:bg-rose-500 text-white text-xs font-semibold"
          >
            Retry
          </button>
        </div>
      ) : patients.length === 0 ? (
        <div className="glass-panel p-12 rounded-2xl text-center space-y-3">
          <Users className="w-10 h-10 text-slate-600 mx-auto" />
          <h3 className="text-base font-bold text-white">No Patient Records Found</h3>
          <p className="text-xs text-slate-400 max-w-sm mx-auto">
            No patient records matched your filter or search criteria.
          </p>
        </div>
      ) : (
        <div className="glass-panel rounded-2xl overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-900/80 border-b border-slate-800 text-slate-400 font-mono uppercase text-[10px]">
                <tr>
                  <th className="py-3.5 px-4">Pseudo ID</th>
                  <th className="py-3.5 px-4">Patient Name</th>
                  <th className="py-3.5 px-4">Age / Gender</th>
                  <th className="py-3.5 px-4">District</th>
                  <th className="py-3.5 px-4">Local Body / Ward</th>
                  <th className="py-3.5 px-4">Assigned Worker</th>
                  <th className="py-3.5 px-4">Status</th>
                  <th className="py-3.5 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-mono text-slate-300">
                {patients.map((p) => (
                  <tr key={p.id} className="hover:bg-slate-800/40 transition-colors">
                    <td className="py-3.5 px-4 font-bold text-brand-400">{p.pseudo_id}</td>
                    <td className="py-3.5 px-4 text-white font-semibold">{p.full_name}</td>
                    <td className="py-3.5 px-4 text-slate-300">
                      {p.age} YRS &bull; {p.gender}
                    </td>
                    <td className="py-3.5 px-4 text-slate-300">{p.district_name}</td>
                    <td className="py-3.5 px-4 text-slate-400 font-sans text-[11px]">
                      {p.local_body_name} (Ward #{p.ward_number})
                    </td>
                    <td className="py-3.5 px-4 text-slate-300 font-sans text-[11px]">
                      {p.assigned_worker_name || 'Rajesh Kumar'}
                    </td>
                    <td className="py-3.5 px-4">
                      {p.is_active ? (
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
                          ACTIVE
                        </span>
                      ) : (
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-slate-800 text-slate-500 border border-slate-700">
                          INACTIVE
                        </span>
                      )}
                    </td>
                    <td className="py-3.5 px-4 text-right">
                      <button
                        onClick={() => setSelectedPatient(p)}
                        className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-brand-400 text-[11px] font-semibold border border-slate-700 transition-colors"
                      >
                        <Eye className="w-3.5 h-3.5" /> View
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Add Patient Modal */}
      {showAddModal && (
        <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="glass-panel max-w-lg w-full rounded-2xl p-6 space-y-5 border border-slate-700 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2.5">
                <UserPlus className="w-5 h-5 text-brand-400" />
                <h3 className="text-base font-bold text-white">Register Patient in Surveillance Registry</h3>
              </div>
              <button
                onClick={() => setShowAddModal(false)}
                className="p-1 rounded-lg text-slate-400 hover:text-white bg-slate-800"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {addSuccess && (
              <div className="p-3 rounded-xl bg-emerald-500/15 border border-emerald-500/30 text-emerald-300 text-xs flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                <span>{addSuccess}</span>
              </div>
            )}

            {addError && (
              <div className="p-3 rounded-xl bg-rose-500/15 border border-rose-500/30 text-rose-300 text-xs flex items-center gap-2">
                <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
                <span>{addError}</span>
              </div>
            )}

            <form onSubmit={handleCreatePatient} className="space-y-4 text-xs">
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1">
                  <label className="text-slate-400 text-[11px] font-semibold">Pseudo ID *</label>
                  <input
                    type="text"
                    required
                    value={formData.pseudo_id}
                    onChange={(e) => setFormData({ ...formData, pseudo_id: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-900 border border-slate-800 rounded-xl text-white font-mono"
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-slate-400 text-[11px] font-semibold">Full Name *</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. Alana P J"
                    value={formData.full_name}
                    onChange={(e) => setFormData({ ...formData, full_name: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-900 border border-slate-800 rounded-xl text-white"
                  />
                </div>
              </div>

              <div className="grid grid-cols-3 gap-3">
                <div className="space-y-1">
                  <label className="text-slate-400 text-[11px] font-semibold">Age *</label>
                  <input
                    type="number"
                    min="1"
                    max="120"
                    required
                    value={formData.age}
                    onChange={(e) => setFormData({ ...formData, age: Number(e.target.value) })}
                    className="w-full px-3 py-2 bg-slate-900 border border-slate-800 rounded-xl text-white font-mono"
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-slate-400 text-[11px] font-semibold">Gender *</label>
                  <select
                    value={formData.gender}
                    onChange={(e) => setFormData({ ...formData, gender: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-900 border border-slate-800 rounded-xl text-white"
                  >
                    <option value="FEMALE">Female</option>
                    <option value="MALE">Male</option>
                    <option value="OTHER">Other</option>
                  </select>
                </div>
                <div className="space-y-1">
                  <label className="text-slate-400 text-[11px] font-semibold">Ward Number *</label>
                  <input
                    type="number"
                    min="1"
                    max="100"
                    required
                    value={formData.ward_number}
                    onChange={(e) => setFormData({ ...formData, ward_number: Number(e.target.value) })}
                    className="w-full px-3 py-2 bg-slate-900 border border-slate-800 rounded-xl text-white font-mono"
                  />
                </div>
              </div>

              <div className="space-y-1">
                <label className="text-slate-400 text-[11px] font-semibold">Contact Phone Number *</label>
                <input
                  type="text"
                  required
                  placeholder="+91-98470-12345"
                  value={formData.contact_number}
                  onChange={(e) => setFormData({ ...formData, contact_number: e.target.value })}
                  className="w-full px-3 py-2 bg-slate-900 border border-slate-800 rounded-xl text-white font-mono"
                />
              </div>

              <div className="space-y-1">
                <label className="text-slate-400 text-[11px] font-semibold">Residential Address *</label>
                <input
                  type="text"
                  required
                  placeholder="Street / Residence Details"
                  value={formData.address}
                  onChange={(e) => setFormData({ ...formData, address: e.target.value })}
                  className="w-full px-3 py-2 bg-slate-900 border border-slate-800 rounded-xl text-white"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1">
                  <label className="text-slate-400 text-[11px] font-semibold">District *</label>
                  <select
                    value={formData.district_name}
                    onChange={(e) => setFormData({ ...formData, district_name: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-900 border border-slate-800 rounded-xl text-white"
                  >
                    <option value="Thiruvananthapuram">Thiruvananthapuram</option>
                    <option value="Ernakulam">Ernakulam</option>
                    <option value="Kozhikode">Kozhikode</option>
                  </select>
                </div>

                <div className="space-y-1">
                  <label className="text-slate-400 text-[11px] font-semibold">Local Body *</label>
                  <input
                    type="text"
                    required
                    value={formData.local_body_name}
                    onChange={(e) => setFormData({ ...formData, local_body_name: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-900 border border-slate-800 rounded-xl text-white text-[11px]"
                  />
                </div>
              </div>

              <div className="flex justify-end gap-3 pt-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={addLoading}
                  className="px-5 py-2 rounded-xl bg-brand-600 hover:bg-brand-500 text-white text-xs font-semibold shadow-md disabled:opacity-50 flex items-center gap-2"
                >
                  {addLoading && <RefreshCw className="w-3.5 h-3.5 animate-spin" />}
                  <span>Save Patient Record</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Patient Detail Modal */}
      {selectedPatient && (
        <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="glass-panel max-w-lg w-full rounded-2xl p-6 space-y-5 border border-slate-700">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div>
                <span className="text-[10px] font-mono uppercase text-slate-500">Patient File</span>
                <h3 className="text-lg font-bold text-white">{selectedPatient.pseudo_id}</h3>
              </div>
              <button
                onClick={() => setSelectedPatient(null)}
                className="p-1 rounded-lg text-slate-400 hover:text-white bg-slate-800"
              >
                &times;
              </button>
            </div>

            <div className="space-y-3 text-xs">
              <div className="p-3.5 rounded-xl bg-slate-900/60 border border-slate-800">
                <span className="text-slate-500 block text-[10px] uppercase font-mono">Full Name</span>
                <span className="font-semibold text-white text-sm">{selectedPatient.full_name}</span>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800">
                  <span className="text-slate-500 block text-[10px] uppercase font-mono">Demographics</span>
                  <span className="font-semibold text-slate-200">{selectedPatient.age} Yrs &bull; {selectedPatient.gender}</span>
                </div>
                <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800">
                  <span className="text-slate-500 block text-[10px] uppercase font-mono">Contact</span>
                  <span className="font-mono font-semibold text-slate-200">{selectedPatient.contact_number}</span>
                </div>
              </div>

              <div className="p-3.5 rounded-xl bg-slate-900/60 border border-slate-800 space-y-1">
                <span className="text-slate-500 block text-[10px] uppercase font-mono">Residence & Ward</span>
                <div className="text-slate-200">{selectedPatient.address}</div>
                <div className="text-[11px] text-brand-300 font-mono pt-1">
                  {selectedPatient.district_name} &bull; {selectedPatient.local_body_name} (Ward #{selectedPatient.ward_number})
                </div>
              </div>
            </div>

            <div className="flex justify-end pt-2">
              <button
                onClick={() => setSelectedPatient(null)}
                className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
