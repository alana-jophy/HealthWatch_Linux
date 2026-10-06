import React, { useState, useEffect } from 'react';
import { 
  fetchPatientsList, 
  fetchDistricts, 
  fetchLocalBodies,
  fetchWards,
  fetchDiseases,
  createPatientRecord,
  updatePatientRecord,
  deletePatientRecord
} from '../../services/api';
import { PatientProfile, DistrictGIS, LocalBodyGIS, WardGIS, DiseaseItem } from '../../types';
import {
  Users,
  Search,
  RefreshCw,
  AlertCircle,
  MapPin,
  CheckCircle2,
  Eye,
  EyeOff,
  Plus,
  UserPlus,
  X,
  Edit2,
  Trash2,
  AlertTriangle,
  Mail,
  Lock,
  Navigation,
  KeyRound,
  Activity,
  Phone,
  Clock,
  Calendar,
  Info
} from 'lucide-react';
import { SearchableSelect } from '../common/SearchableSelect';

export const PatientManagementView: React.FC = () => {
  const [patients, setPatients] = useState<PatientProfile[]>([]);
  const [total, setTotal] = useState<number>(0);
  const [districts, setDistricts] = useState<DistrictGIS[]>([]);
  const [diseases, setDiseases] = useState<DiseaseItem[]>([]);
  
  // Toolbar filter states
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [filterDistrictId, setFilterDistrictId] = useState<string>('');
  const [filterLocalBodies, setFilterLocalBodies] = useState<LocalBodyGIS[]>([]);
  const [filterLocalBodyId, setFilterLocalBodyId] = useState<string>('');
  const [filterWards, setFilterWards] = useState<WardGIS[]>([]);
  const [filterWardId, setFilterWardId] = useState<string>('');
  const [filterDiseaseId, setFilterDiseaseId] = useState<string>('');
  const [filterHasPhone, setFilterHasPhone] = useState<string>('ALL');
  const [selectedGender, setSelectedGender] = useState<string>('');
  const [selectedStatus, setSelectedStatus] = useState<string>('');
  const [samplingInterval, setSamplingInterval] = useState<number>(15);
  
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Modals state
  const [selectedPatient, setSelectedPatient] = useState<PatientProfile | null>(null);
  const [showAddModal, setShowAddModal] = useState<boolean>(false);
  const [editingPatient, setEditingPatient] = useState<PatientProfile | null>(null);
  const [deletingPatient, setDeletingPatient] = useState<PatientProfile | null>(null);

  // Action states
  const [actionLoading, setActionLoading] = useState<boolean>(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);

  // Form states for Add Modal
  const [addLocalBodies, setAddLocalBodies] = useState<LocalBodyGIS[]>([]);
  const [addWards, setAddWards] = useState<WardGIS[]>([]);
  const [phoneError, setPhoneError] = useState<string | null>(null);
  const [showInitialPassword, setShowInitialPassword] = useState<boolean>(false);
  const [formData, setFormData] = useState({
    pseudo_id: '',
    full_name: '',
    email: '',
    initial_password: '',
    date_of_birth: '',
    age: '' as number | '',
    gender: '',
    has_phone: true,
    contact_number: '',
    tracking_interval_minutes: 15,
    tracking_days: ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'],
    monitoring_days: 14,
    disease_id: '',
    disease_name: '',
    address: '',
    district_id: '',
    district_name: '',
    local_body_id: '',
    local_body_name: '',
    ward_id: '',
    ward_name: '',
    ward_number: 0,
  });

  // Form states for Edit Modal
  const [editLocalBodies, setEditLocalBodies] = useState<LocalBodyGIS[]>([]);
  const [editWards, setEditWards] = useState<WardGIS[]>([]);
  const [editPhoneError, setEditPhoneError] = useState<string | null>(null);
  const [showEditPassword, setShowEditPassword] = useState<boolean>(false);
  const [editFormData, setEditFormData] = useState({
    full_name: '',
    email: '',
    password: '',
    date_of_birth: '',
    age: '' as number | '',
    gender: '',
    has_phone: true,
    contact_number: '',
    tracking_interval_minutes: 15,
    tracking_days: ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'],
    monitoring_days: 14,
    disease_id: '',
    disease_name: '',
    address: '',
    district_id: '',
    district_name: '',
    local_body_id: '',
    local_body_name: '',
    ward_id: '',
    ward_name: '',
    ward_number: 1,
    is_active: true,
  });

  // Initial load of Kerala Districts and Diseases
  useEffect(() => {
    fetchDistricts()
      .then((res) => setDistricts(res))
      .catch((err) => console.error('Failed to load districts:', err));

    fetchDiseases()
      .then((res) => setDiseases(res))
      .catch((err) => console.error('Failed to load diseases:', err));
  }, []);

  // Update filter local bodies when filter district changes
  useEffect(() => {
    if (filterDistrictId) {
      fetchLocalBodies(filterDistrictId)
        .then((lbs) => setFilterLocalBodies(lbs))
        .catch(() => setFilterLocalBodies([]));
      setFilterLocalBodyId('');
      setFilterWards([]);
      setFilterWardId('');
    } else {
      setFilterLocalBodies([]);
      setFilterLocalBodyId('');
      setFilterWards([]);
      setFilterWardId('');
    }
  }, [filterDistrictId]);

  // Update filter wards when filter local body changes
  useEffect(() => {
    if (filterLocalBodyId) {
      fetchWards(filterLocalBodyId)
        .then((w) => setFilterWards(w))
        .catch(() => setFilterWards([]));
      setFilterWardId('');
    } else {
      setFilterWards([]);
      setFilterWardId('');
    }
  }, [filterLocalBodyId]);

  // Load patients list with all active filters
  const loadData = async () => {
    setIsLoading(true);
    setError(null);
    try {
      let isActiveParam: boolean | undefined = undefined;
      if (selectedStatus === 'ACTIVE') isActiveParam = true;
      if (selectedStatus === 'INACTIVE') isActiveParam = false;

      let hasPhoneParam: boolean | undefined = undefined;
      if (filterHasPhone === 'YES') hasPhoneParam = true;
      if (filterHasPhone === 'NO') hasPhoneParam = false;

      const patRes = await fetchPatientsList(
        searchQuery || undefined,
        undefined,
        undefined,
        filterDistrictId || undefined,
        filterLocalBodyId || undefined,
        filterWardId || undefined,
        isActiveParam,
        filterDiseaseId || undefined,
        hasPhoneParam
      );
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
  }, [filterDistrictId, filterLocalBodyId, filterWardId, selectedStatus, filterDiseaseId, filterHasPhone]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    loadData();
  };

  // -------------------------------------------------------------
  // Add Patient Modal Handlers & Cascading Dropdowns
  // -------------------------------------------------------------
  const handleOpenAddModal = async () => {
    setAddLocalBodies([]);
    setAddWards([]);
    setPhoneError(null);
    setFormData({
      pseudo_id: '',
      full_name: '',
      email: '',
      initial_password: '',
      date_of_birth: '',
      age: '' as number | '',
      gender: '',
      has_phone: true,
      contact_number: '',
      tracking_interval_minutes: 15,
      tracking_days: ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'],
      disease_id: '',
      disease_name: '',
      address: '',
      district_id: '',
      district_name: '',
      local_body_id: '',
      local_body_name: '',
      ward_id: '',
      ward_name: '',
      ward_number: 0,
    });

    setActionError(null);
    setActionSuccess(null);
    setShowAddModal(true);
  };

  const handleDobChange = (dob: string) => {
    let calcAge: number | '' = '';
    if (dob) {
      const bDate = new Date(dob);
      const today = new Date();
      let ageYears = today.getFullYear() - bDate.getFullYear();
      const m = today.getMonth() - bDate.getMonth();
      if (m < 0 || (m === 0 && today.getDate() < bDate.getDate())) {
        ageYears--;
      }
      if (ageYears >= 0 && ageYears <= 125) {
        calcAge = ageYears;
      }
    }
    setFormData((prev) => ({ ...prev, date_of_birth: dob, age: calcAge }));
  };

  const handleEditDobChange = (dob: string) => {
    let calcAge: number | '' = '';
    if (dob) {
      const bDate = new Date(dob);
      const today = new Date();
      let ageYears = today.getFullYear() - bDate.getFullYear();
      const m = today.getMonth() - bDate.getMonth();
      if (m < 0 || (m === 0 && today.getDate() < bDate.getDate())) {
        ageYears--;
      }
      if (ageYears >= 0 && ageYears <= 125) {
        calcAge = ageYears;
      }
    }
    setEditFormData((prev) => ({ ...prev, date_of_birth: dob, age: calcAge !== '' ? calcAge : prev.age }));
  };

  const handlePhoneChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const numericOnly = e.target.value.replace(/\D/g, '').slice(0, 10);
    setFormData((prev) => ({ ...prev, contact_number: numericOnly }));

    if (numericOnly.length > 0) {
      if (numericOnly.length < 10) {
        setPhoneError(`Phone number must be exactly 10 digits (${numericOnly.length}/10 entered)`);
      } else if (!/^[6-9]\d{9}$/.test(numericOnly)) {
        setPhoneError('Indian mobile numbers must start with 6, 7, 8, or 9.');
      } else {
        setPhoneError(null);
      }
    } else {
      setPhoneError(null);
    }
  };

  const handlePhoneBlur = () => {
    if (formData.has_phone && formData.contact_number) {
      if (formData.contact_number.length !== 10) {
        setPhoneError('Phone number must be exactly 10 digits.');
      } else if (!/^[6-9]\d{9}$/.test(formData.contact_number)) {
        setPhoneError('Indian mobile numbers must start with 6, 7, 8, or 9.');
      }
    }
  };

  const handleAddDistrictChange = async (distId: string) => {
    const dist = districts.find((d) => d.id === distId);
    let lbs: LocalBodyGIS[] = [];
    if (distId) {
      try {
        lbs = await fetchLocalBodies(distId);
      } catch (err) {
        console.error(err);
      }
    }
    setAddLocalBodies(lbs);
    setAddWards([]);

    setFormData((prev) => ({
      ...prev,
      district_id: distId,
      district_name: dist ? dist.name : '',
      local_body_id: '',
      local_body_name: '',
      ward_id: '',
      ward_name: '',
      ward_number: 0,
    }));
  };

  const handleAddLocalBodyChange = async (lbId: string) => {
    const lb = addLocalBodies.find((l) => l.id === lbId);
    let wrds: WardGIS[] = [];
    if (lbId) {
      try {
        wrds = await fetchWards(lbId);
      } catch (err) {
        console.error(err);
      }
    }
    setAddWards(wrds);

    setFormData((prev) => ({
      ...prev,
      local_body_id: lbId,
      local_body_name: lb ? lb.name : '',
      ward_id: '',
      ward_name: '',
      ward_number: 0,
    }));
  };

  const handleAddWardChange = (wId: string) => {
    const w = addWards.find((item) => item.id === wId);
    setFormData((prev) => ({
      ...prev,
      ward_id: wId,
      ward_name: w ? w.name : '',
      ward_number: w ? w.ward_number : 0,
    }));
  };

  const handleCreatePatient = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!formData.pseudo_id.trim()) {
      setActionError('Account / Pseudo ID is required.');
      return;
    }
    if (!formData.full_name.trim()) {
      setActionError('Full Name is required.');
      return;
    }
    if (!formData.email.trim()) {
      setActionError('Login Email is required.');
      return;
    }
    if (!formData.initial_password) {
      setActionError('Initial Password is required.');
      return;
    }
    if (!formData.age || Number(formData.age) <= 0) {
      setActionError('Please enter a valid age.');
      return;
    }
    if (!formData.gender) {
      setActionError('Please select a gender.');
      return;
    }
    if (!formData.disease_id) {
      setActionError('Please select a disease condition.');
      return;
    }
    if (formData.has_phone) {
      if (!formData.contact_number || !/^\d{10}$/.test(formData.contact_number.trim())) {
        setPhoneError('Phone number must be exactly 10 digits.');
        setActionError('Phone number must be exactly 10 numeric digits.');
        return;
      }
      if (!/^[6-9]\d{9}$/.test(formData.contact_number.trim())) {
        setPhoneError('Indian mobile numbers must start with 6, 7, 8, or 9.');
        setActionError('Indian mobile numbers must start with 6, 7, 8, or 9.');
        return;
      }
    }
    if (!formData.address.trim()) {
      setActionError('Residential Address is required.');
      return;
    }
    if (!formData.district_id) {
      setActionError('Please select a District.');
      return;
    }
    if (!formData.local_body_id) {
      setActionError('Please select a Local Body.');
      return;
    }
    if (!formData.ward_id) {
      setActionError('Please select a Ward.');
      return;
    }

    setActionLoading(true);
    setActionError(null);
    setActionSuccess(null);
    try {
      const newPatient = await createPatientRecord({
        pseudo_id: formData.pseudo_id.trim(),
        full_name: formData.full_name.trim(),
        email: formData.email.trim(),
        initial_password: formData.initial_password,
        date_of_birth: formData.date_of_birth || undefined,
        age: Number(formData.age),
        gender: formData.gender,
        has_phone: formData.has_phone,
        contact_number: formData.has_phone ? formData.contact_number.trim() : null,
        tracking_interval_minutes: formData.has_phone ? formData.tracking_interval_minutes : 15,
        tracking_days: formData.has_phone ? formData.tracking_days.join(',') : undefined,
        monitoring_days: Number(formData.monitoring_days) || 14,
        disease_id: formData.disease_id || undefined,
        disease_name: formData.disease_name || undefined,
        address: formData.address.trim(),
        district_id: formData.district_id || undefined,
        district_name: formData.district_name,
        local_body_id: formData.local_body_id || undefined,
        local_body_name: formData.local_body_name,
        ward_id: formData.ward_id || undefined,
        ward_name: formData.ward_name,
        ward_number: Number(formData.ward_number),
      });

      setActionSuccess(`Patient ${newPatient.pseudo_id} (${newPatient.full_name}) registered with linked login account!`);
      await loadData();
      setTimeout(() => {
        setShowAddModal(false);
        setActionSuccess(null);
      }, 1500);
    } catch (err: any) {
      setActionError(err?.response?.data?.detail || 'Failed to register patient record. Please verify fields.');
    } finally {
      setActionLoading(false);
    }
  };

  // -------------------------------------------------------------
  // Edit Patient Modal Handlers & Cascading Dropdowns
  // -------------------------------------------------------------
  const handleOpenEdit = async (p: PatientProfile) => {
    setEditingPatient(p);
    setActionError(null);
    setActionSuccess(null);
    setEditPhoneError(null);

    let lbs: LocalBodyGIS[] = [];
    let wrds: WardGIS[] = [];

    const distId = p.district_id || (districts.find((d) => d.name === p.district_name)?.id || '');
    if (distId) {
      try {
        lbs = await fetchLocalBodies(distId);
      } catch (err) {
        console.error(err);
      }
    }

    const lbId = p.local_body_id || (lbs.find((l) => l.name === p.local_body_name)?.id || '');
    if (lbId) {
      try {
        wrds = await fetchWards(lbId);
      } catch (err) {
        console.error(err);
      }
    }

    setEditLocalBodies(lbs);
    setEditWards(wrds);

    setEditFormData({
      full_name: p.full_name,
      email: p.account_email || '',
      password: '',
      date_of_birth: p.date_of_birth || '',
      age: p.age,
      gender: p.gender,
      has_phone: p.has_phone ?? Boolean(p.contact_number),
      contact_number: p.contact_number || '',
      tracking_interval_minutes: p.tracking_interval_minutes || 15,
      tracking_days: p.tracking_days ? p.tracking_days.split(',').map((d) => d.trim()) : ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'],
      monitoring_days: p.monitoring_days || 14,
      disease_id: p.disease_id || '',
      disease_name: p.disease_name || '',
      address: p.address || '',
      district_id: distId,
      district_name: p.district_name,
      local_body_id: lbId,
      local_body_name: p.local_body_name,
      ward_id: p.ward_id || '',
      ward_name: p.ward_name || '',
      ward_number: p.ward_number,
      is_active: p.is_active,
    });
  };

  const handleEditDistrictChange = async (distId: string) => {
    const dist = districts.find((d) => d.id === distId);
    let lbs: LocalBodyGIS[] = [];
    let wrds: WardGIS[] = [];
    if (distId) {
      try {
        lbs = await fetchLocalBodies(distId);
        if (lbs.length > 0) {
          wrds = await fetchWards(lbs[0].id);
        }
      } catch (err) {
        console.error(err);
      }
    }
    setEditLocalBodies(lbs);
    setEditWards(wrds);

    const firstLb = lbs[0] || null;
    const firstW = wrds[0] || null;

    setEditFormData((prev) => ({
      ...prev,
      district_id: distId,
      district_name: dist ? dist.name : '',
      local_body_id: firstLb ? firstLb.id : '',
      local_body_name: firstLb ? firstLb.name : '',
      ward_id: firstW ? firstW.id : '',
      ward_name: firstW ? firstW.name : '',
      ward_number: firstW ? firstW.ward_number : 1,
    }));
  };

  const handleEditLocalBodyChange = async (lbId: string) => {
    const lb = editLocalBodies.find((l) => l.id === lbId);
    let wrds: WardGIS[] = [];
    if (lbId) {
      try {
        wrds = await fetchWards(lbId);
      } catch (err) {
        console.error(err);
      }
    }
    setEditWards(wrds);
    const firstW = wrds[0] || null;

    setEditFormData((prev) => ({
      ...prev,
      local_body_id: lbId,
      local_body_name: lb ? lb.name : '',
      ward_id: firstW ? firstW.id : '',
      ward_name: firstW ? firstW.name : '',
      ward_number: firstW ? firstW.ward_number : 1,
    }));
  };

  const handleEditWardChange = (wId: string) => {
    const w = editWards.find((item) => item.id === wId);
    setEditFormData((prev) => ({
      ...prev,
      ward_id: wId,
      ward_name: w ? w.name : '',
      ward_number: w ? w.ward_number : prev.ward_number,
    }));
  };

  const handleEditPhoneChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const numericOnly = e.target.value.replace(/\D/g, '').slice(0, 10);
    setEditFormData((prev) => ({ ...prev, contact_number: numericOnly }));

    if (numericOnly.length > 0) {
      if (numericOnly.length < 10) {
        setEditPhoneError(`Phone number must be exactly 10 digits (${numericOnly.length}/10 entered)`);
      } else if (!/^[6-9]\d{9}$/.test(numericOnly)) {
        setEditPhoneError('Indian mobile numbers must start with 6, 7, 8, or 9.');
      } else {
        setEditPhoneError(null);
      }
    } else {
      setEditPhoneError(null);
    }
  };

  const handleUpdatePatient = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingPatient) return;

    if (editFormData.has_phone && editFormData.contact_number) {
      if (!/^\d{10}$/.test(editFormData.contact_number.trim())) {
        setEditPhoneError('Phone number must be exactly 10 digits.');
        setActionError('Phone number must be exactly 10 numeric digits.');
        return;
      }
      if (!/^[6-9]\d{9}$/.test(editFormData.contact_number.trim())) {
        setEditPhoneError('Indian mobile numbers must start with 6, 7, 8, or 9.');
        setActionError('Indian mobile numbers must start with 6, 7, 8, or 9.');
        return;
      }
    }

    setActionLoading(true);
    setActionError(null);
    setActionSuccess(null);

    try {
      const updatePayload: any = {
        full_name: editFormData.full_name.trim(),
        date_of_birth: editFormData.date_of_birth || null,
        age: Number(editFormData.age),
        gender: editFormData.gender,
        has_phone: editFormData.has_phone,
        contact_number: editFormData.has_phone ? (editFormData.contact_number ? editFormData.contact_number.trim() : null) : null,
        tracking_interval_minutes: editFormData.has_phone ? editFormData.tracking_interval_minutes : 15,
        tracking_days: editFormData.has_phone ? editFormData.tracking_days.join(',') : undefined,
        monitoring_days: Number(editFormData.monitoring_days) || 14,
        disease_id: editFormData.disease_id || null,
        disease_name: editFormData.disease_name || null,
        address: editFormData.address.trim(),
        district_id: editFormData.district_id || undefined,
        district_name: editFormData.district_name,
        local_body_id: editFormData.local_body_id || undefined,
        local_body_name: editFormData.local_body_name,
        ward_id: editFormData.ward_id || undefined,
        ward_name: editFormData.ward_name,
        ward_number: Number(editFormData.ward_number),
        is_active: editFormData.is_active,
      };

      if (editFormData.email.trim()) {
        updatePayload.email = editFormData.email.trim();
      }
      if (editFormData.password.trim()) {
        updatePayload.password = editFormData.password.trim();
      }

      await updatePatientRecord(editingPatient.id, updatePayload);

      setActionSuccess(`Patient record ${editingPatient.pseudo_id} updated successfully.`);
      await loadData();
      setTimeout(() => {
        setEditingPatient(null);
        setActionSuccess(null);
      }, 1500);
    } catch (err: any) {
      setActionError(err?.response?.data?.detail || 'Failed to update patient record.');
    } finally {
      setActionLoading(false);
    }
  };

  const handleConfirmDelete = async () => {
    if (!deletingPatient) return;
    setActionLoading(true);
    setActionError(null);

    try {
      await deletePatientRecord(deletingPatient.id);
      setActionSuccess(`Patient ${deletingPatient.pseudo_id} and login access deactivated.`);
      await loadData();
      setTimeout(() => {
        setDeletingPatient(null);
        setActionSuccess(null);
      }, 1200);
    } catch (err: any) {
      setActionError(err?.response?.data?.detail || 'Failed to deactivate patient record.');
    } finally {
      setActionLoading(false);
    }
  };

  // Local filtering for gender
  const filteredPatients = patients.filter((p) => {
    if (selectedGender && p.gender !== selectedGender) return false;
    return true;
  });

  // Computed location preview for Create Modal (No Phone Administrative Centroid)
  const createSelectedWard = addWards.find((w) => w.id === formData.ward_id);
  const createSelectedLb = addLocalBodies.find((lb) => lb.id === formData.local_body_id);
  const createSelectedDist = districts.find((d) => d.id === formData.district_id);
  const createAssignedCoords: [number, number] | null = createSelectedWard?.center_latitude && createSelectedWard?.center_longitude
    ? [createSelectedWard.center_latitude, createSelectedWard.center_longitude]
    : (createSelectedLb?.center_latitude && createSelectedLb?.center_longitude
        ? [createSelectedLb.center_latitude, createSelectedLb.center_longitude]
        : (createSelectedDist?.center_latitude && createSelectedDist?.center_longitude
            ? [createSelectedDist.center_latitude, createSelectedDist.center_longitude]
            : null));

  // Computed location preview for Edit Modal (No Phone Administrative Centroid)
  const editSelectedWard = editWards.find((w) => w.id === editFormData.ward_id);
  const editSelectedLb = editLocalBodies.find((lb) => lb.id === editFormData.local_body_id);
  const editSelectedDist = districts.find((d) => d.id === editFormData.district_id);
  const editAssignedCoords: [number, number] | null = editSelectedWard?.center_latitude && editSelectedWard?.center_longitude
    ? [editSelectedWard.center_latitude, editSelectedWard.center_longitude]
    : (editSelectedLb?.center_latitude && editSelectedLb?.center_longitude
        ? [editSelectedLb.center_latitude, editSelectedLb.center_longitude]
        : (editSelectedDist?.center_latitude && editSelectedDist?.center_longitude
            ? [editSelectedDist.center_latitude, editSelectedDist.center_longitude]
            : null));

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 glass-panel p-6 rounded-2xl">
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-2xl bg-brand-500/15 border border-brand-500/30 flex items-center justify-center text-brand-400">
            <Users className="w-6 h-6" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-white tracking-tight">Patient Registry & Accounts</h2>
            <p className="text-xs text-slate-400 font-mono">
              Role Isolation &bull; Individual Patient Credentials &bull; Kerala Administrative Hierarchy &bull; Total: <span className="text-brand-400 font-bold">{total}</span>
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={loadData}
            disabled={isLoading}
            className="p-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition-colors"
            title="Refresh list"
          >
            <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
          </button>
          <button
            onClick={handleOpenAddModal}
            className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-brand-600 hover:bg-brand-500 text-white font-semibold text-xs shadow-lg shadow-brand-600/20 transition-all cursor-pointer"
          >
            <Plus className="w-4 h-4" />
            <span>Add Patient & Account</span>
          </button>
        </div>
      </div>

      {/* Global Alerts */}
      {error && (
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs flex items-center gap-3">
          <AlertCircle className="w-4 h-4 shrink-0 text-rose-400" />
          <span>{error}</span>
        </div>
      )}

      {/* Cascading Filter and Search Bar */}
      <div className="glass-panel p-4 rounded-2xl flex flex-col gap-3">
        <div className="flex flex-col lg:flex-row gap-3 items-stretch lg:items-center justify-between">
          <form onSubmit={handleSearchSubmit} className="relative flex-1">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
            <input
              type="text"
              placeholder="Search by name, pseudo ID, or email..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-9 pr-3 py-2 bg-slate-900/80 border border-slate-800 rounded-xl text-xs text-white placeholder-slate-500 focus:outline-none focus:border-brand-500 font-mono"
            />
          </form>

          <div className="flex flex-wrap items-center gap-2">
            {/* District Filter (14 Kerala Districts) */}
            <select
              value={filterDistrictId}
              onChange={(e) => setFilterDistrictId(e.target.value)}
              className="px-3 py-2 bg-slate-900/80 border border-slate-800 rounded-xl text-xs text-slate-300 focus:outline-none focus:border-brand-500"
            >
              <option value="">All Kerala Districts (14)</option>
              {districts.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.name}
                </option>
              ))}
            </select>

            {/* Local Body Filter (Cascading) */}
            <select
              value={filterLocalBodyId}
              onChange={(e) => setFilterLocalBodyId(e.target.value)}
              disabled={!filterDistrictId || filterLocalBodies.length === 0}
              className="px-3 py-2 bg-slate-900/80 border border-slate-800 rounded-xl text-xs text-slate-300 focus:outline-none focus:border-brand-500 disabled:opacity-50"
            >
              <option value="">All Local Bodies</option>
              {filterLocalBodies.map((lb) => (
                <option key={lb.id} value={lb.id}>
                  {lb.name} ({lb.body_type})
                </option>
              ))}
            </select>

            {/* Ward Filter (Cascading & Searchable) */}
            <div className="w-56">
              <SearchableSelect
                id="patient-filter-ward-select"
                value={filterWardId}
                onChange={(val) => setFilterWardId(val)}
                options={filterWards.map((w) => ({
                  value: w.id,
                  label: `Ward #${w.ward_number} - ${w.name}`,
                  code: w.ward_code,
                  number: w.ward_number,
                  sublabel: w.ward_code ? `Code: ${w.ward_code}` : undefined,
                }))}
                placeholder="All Wards (Search...)"
                disabled={!filterLocalBodyId || filterWards.length === 0}
                disabledPlaceholder={!filterLocalBodyId ? "Select Local Body first" : "No wards found"}
              />
            </div>

            {/* Disease Filter */}
            <select
              value={filterDiseaseId}
              onChange={(e) => setFilterDiseaseId(e.target.value)}
              className="px-3 py-2 bg-slate-900/80 border border-slate-800 rounded-xl text-xs text-slate-300 focus:outline-none focus:border-brand-500"
            >
              <option value="">All Diseases ({diseases.length})</option>
              {diseases.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.name} ({d.code})
                </option>
              ))}
            </select>

            {/* Phone Availability Filter */}
            <select
              value={filterHasPhone}
              onChange={(e) => setFilterHasPhone(e.target.value)}
              className="px-3 py-2 bg-slate-900/80 border border-slate-800 rounded-xl text-xs text-slate-300 focus:outline-none focus:border-brand-500"
            >
              <option value="ALL">All Phone Statuses</option>
              <option value="YES">Has Mobile Phone</option>
              <option value="NO">No Mobile Phone</option>
            </select>

            {/* Status Filter */}
            <select
              value={selectedStatus}
              onChange={(e) => setSelectedStatus(e.target.value)}
              className="px-3 py-2 bg-slate-900/80 border border-slate-800 rounded-xl text-xs text-slate-300 focus:outline-none focus:border-brand-500"
            >
              <option value="">All Statuses</option>
              <option value="ACTIVE">Active Surveillance</option>
              <option value="INACTIVE">Deactivated</option>
            </select>

            {/* Gender Filter */}
            <select
              value={selectedGender}
              onChange={(e) => setSelectedGender(e.target.value)}
              className="px-3 py-2 bg-slate-900/80 border border-slate-800 rounded-xl text-xs text-slate-300 focus:outline-none focus:border-brand-500"
            >
              <option value="">All Genders</option>
              <option value="FEMALE">Female</option>
              <option value="MALE">Male</option>
              <option value="OTHER">Other</option>
            </select>

            {(searchQuery || filterDistrictId || filterLocalBodyId || filterWardId || filterDiseaseId || filterHasPhone !== 'ALL' || selectedGender || selectedStatus) && (
              <button
                onClick={() => {
                  setSearchQuery('');
                  setFilterDistrictId('');
                  setFilterLocalBodyId('');
                  setFilterWardId('');
                  setFilterDiseaseId('');
                  setFilterHasPhone('ALL');
                  setSelectedGender('');
                  setSelectedStatus('');
                }}
                className="px-3 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-[11px] font-semibold text-slate-300 border border-slate-700 cursor-pointer"
              >
                Reset
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Patient Table */}
      {isLoading ? (
        <div className="glass-panel p-12 rounded-2xl flex flex-col items-center justify-center gap-3 text-slate-400">
          <RefreshCw className="w-6 h-6 animate-spin text-brand-400" />
          <span className="text-xs font-mono">Loading patient directory...</span>
        </div>
      ) : filteredPatients.length === 0 ? (
        <div className="glass-panel p-12 rounded-2xl text-center space-y-2">
          <Users className="w-8 h-8 text-slate-500 mx-auto" />
          <p className="text-sm font-semibold text-slate-300">No patient records found.</p>
          <p className="text-xs text-slate-500">Try adjusting your filters or register a new patient account.</p>
        </div>
      ) : (
        <div className="glass-panel rounded-2xl overflow-hidden border border-slate-800">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs font-mono">
              <thead className="bg-slate-950/80 text-slate-400 border-b border-slate-800 uppercase tracking-wider text-[10px]">
                <tr>
                  <th className="py-3.5 px-4">Account / Pseudo ID</th>
                  <th className="py-3.5 px-4">Full Name & Phone</th>
                  <th className="py-3.5 px-4">Diagnosed Condition</th>
                  <th className="py-3.5 px-4">Login Email</th>
                  <th className="py-3.5 px-4">District</th>
                  <th className="py-3.5 px-4">Local Body / Ward</th>
                  <th className="py-3.5 px-4">Location (GPS / Admin)</th>
                  <th className="py-3.5 px-4">Status</th>
                  <th className="py-3.5 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {filteredPatients.map((p) => (
                  <tr key={p.id} className="hover:bg-slate-800/40 transition-colors">
                    <td className="py-3.5 px-4 font-bold text-brand-400">{p.pseudo_id}</td>
                    <td className="py-3.5 px-4 text-white font-semibold">
                      <div>{p.full_name}</div>
                      <div className="text-[10px] text-slate-400 font-sans flex items-center gap-1.5 mt-0.5">
                        <span>{p.age} YRS &bull; {p.gender}</span>
                        <span>&bull;</span>
                        {p.has_phone === false || !p.contact_number ? (
                          <span className="px-1.5 py-0.2 rounded bg-amber-500/15 text-amber-400 border border-amber-500/30 text-[9px] font-mono">
                            NO PHONE
                          </span>
                        ) : (
                          <span className="font-mono text-slate-300 text-[10px] flex items-center gap-0.5">
                            <Phone className="w-2.5 h-2.5 text-slate-500" />
                            {p.contact_number}
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="py-3.5 px-4">
                      <div>
                        <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-rose-500/15 text-rose-300 border border-rose-500/30">
                          {p.disease_name || 'Under Evaluation'}
                        </span>
                      </div>
                      <div className="mt-1">
                        <span className="inline-flex items-center gap-1 px-1.5 py-0.2 rounded text-[9px] font-mono font-medium bg-cyan-950/80 text-cyan-300 border border-cyan-800/60" title="Assigned surveillance monitoring duration">
                          <Clock className="w-2.5 h-2.5 text-cyan-400" />
                          {p.monitoring_days || 14}d Protocol
                        </span>
                      </div>
                    </td>
                    <td className="py-3.5 px-4 text-slate-300 font-mono text-[11px]">
                      {p.account_email || 'Linked User Account'}
                    </td>
                    <td className="py-3.5 px-4 text-slate-300">{p.district_name}</td>
                    <td className="py-3.5 px-4 text-slate-400 font-sans text-[11px]">
                      <div>{p.local_body_name}</div>
                      <div className="text-[10px] text-slate-500 font-mono flex items-center gap-1 flex-wrap">
                        <span>Ward #{p.ward_number} {p.ward_name ? `(${p.ward_name})` : ''}</span>
                        {p.ward_code && (
                          <span className="px-1 py-0.2 rounded bg-indigo-950/70 text-indigo-400 border border-indigo-800/40 text-[9px]">
                            {p.ward_code}
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="py-3.5 px-4 font-mono text-[10px]">
                      {p.has_phone === false ? (
                        <div className="space-y-1">
                          <div className="flex items-center gap-1.5 text-cyan-300 font-sans font-medium text-[11px]">
                            <MapPin className="w-3.5 h-3.5 text-cyan-400 shrink-0" />
                            <span className="font-semibold text-white">Ward #{p.ward_number || '—'}</span>
                            <span className="text-slate-500">&bull;</span>
                            <span className="text-cyan-300 truncate max-w-[130px]" title={p.local_body_name}>{p.local_body_name || p.district_name}</span>
                          </div>
                          <div className="flex items-center gap-1.5 text-[10px] text-slate-400">
                            <span className="px-1.5 py-0.2 rounded bg-cyan-950 border border-cyan-800/60 text-cyan-300 font-mono text-[9px] font-semibold">
                              Admin Centroid
                            </span>
                            {p.latest_latitude && p.latest_longitude ? (
                              <span className="text-slate-300 font-mono">
                                {p.latest_latitude.toFixed(4)}, {p.latest_longitude.toFixed(4)}
                              </span>
                            ) : (
                              <span className="text-slate-500 italic">{p.district_name}</span>
                            )}
                          </div>
                        </div>
                      ) : p.latest_latitude && p.latest_longitude ? (
                        <div className="space-y-0.5">
                          <div className="text-emerald-400 flex items-center gap-1 font-mono">
                            <Navigation className="w-3 h-3 shrink-0" />
                            <span>{p.latest_latitude.toFixed(4)}, {p.latest_longitude.toFixed(4)}</span>
                          </div>
                          <span className="text-[9px] text-emerald-500/80 font-sans">Live GPS Telemetry</span>
                        </div>
                      ) : (
                        <span className="text-slate-600 italic">No GPS yet</span>
                      )}
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
                      <div className="inline-flex items-center gap-1.5">
                        <button
                          onClick={() => setSelectedPatient(p)}
                          className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-brand-400 border border-slate-700 transition-colors"
                          title="View Details"
                        >
                          <Eye className="w-3.5 h-3.5" />
                        </button>
                        <button
                          onClick={() => handleOpenEdit(p)}
                          className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-cyan-400 border border-slate-700 transition-colors"
                          title="Edit Patient"
                        >
                          <Edit2 className="w-3.5 h-3.5" />
                        </button>
                        {p.is_active && (
                          <button
                            onClick={() => {
                              setDeletingPatient(p);
                              setActionError(null);
                            }}
                            className="p-1.5 rounded-lg bg-slate-800 hover:bg-rose-950/40 text-rose-400 border border-slate-700 hover:border-rose-500/30 transition-colors"
                            title="Deactivate Patient & Account"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* ------------------------------------------------------------------ */}
      {/* 1. Add Patient & Individual Account Modal */}
      {/* ------------------------------------------------------------------ */}
      {showAddModal && (
        <div className="fixed inset-0 bg-slate-950/85 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="glass-panel max-w-xl w-full rounded-2xl p-6 space-y-5 border border-slate-700 max-h-[90vh] overflow-y-auto shadow-2xl">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2.5">
                <UserPlus className="w-5 h-5 text-brand-400" />
                <div>
                  <h3 className="text-base font-bold text-white">Register Patient & Account</h3>
                  <p className="text-[11px] text-slate-400">Creates patient record with linked individual login credentials</p>
                </div>
              </div>
              <button
                onClick={() => setShowAddModal(false)}
                className="p-1 rounded-lg text-slate-400 hover:text-white bg-slate-800"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {actionSuccess && (
              <div className="p-3 rounded-xl bg-emerald-500/15 border border-emerald-500/30 text-emerald-300 text-xs flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                <span>{actionSuccess}</span>
              </div>
            )}

            {actionError && (
              <div className="p-3 rounded-xl bg-rose-500/15 border border-rose-500/30 text-rose-300 text-xs flex items-center gap-2">
                <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
                <span>{actionError}</span>
              </div>
            )}

            <form onSubmit={handleCreatePatient} className="space-y-4 text-xs">
              {/* Account Credentials Section */}
              <div className="p-3.5 rounded-xl bg-brand-950/20 border border-brand-500/30 space-y-3">
                <span className="text-[11px] font-bold text-brand-400 uppercase tracking-wider flex items-center gap-1.5">
                  <KeyRound className="w-3.5 h-3.5" />
                  Individual Login Credentials
                </span>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div className="space-y-1">
                    <label className="text-slate-300 text-[11px] font-semibold flex items-center gap-1">
                      <Mail className="w-3 h-3 text-slate-400" />
                      Login Email *
                    </label>
                    <input
                      type="email"
                      required
                      placeholder="e.g. rahul@example.com"
                      value={formData.email}
                      onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                      className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-xl text-white font-mono"
                    />
                  </div>
                  <div className="space-y-1">
                    <label className="text-slate-300 text-[11px] font-semibold flex items-center gap-1">
                      <Lock className="w-3 h-3 text-slate-400" />
                      Initial Password *
                    </label>
                    <div className="relative">
                      <input
                        type={showInitialPassword ? 'text' : 'password'}
                        required
                        placeholder="Enter initial password"
                        value={formData.initial_password}
                        onChange={(e) => setFormData({ ...formData, initial_password: e.target.value })}
                        className="w-full px-3 py-2 pr-10 bg-slate-900 border border-slate-700 rounded-xl text-white font-mono"
                      />
                      <button
                        type="button"
                        id="toggle-initial-password-btn"
                        onClick={() => setShowInitialPassword(!showInitialPassword)}
                        aria-label={showInitialPassword ? 'Hide password' : 'Show password'}
                        title={showInitialPassword ? 'Hide password' : 'Show password'}
                        className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-200 transition-colors p-1 cursor-pointer focus:outline-none"
                      >
                        {showInitialPassword ? <EyeOff className="w-3.5 h-3.5 text-brand-400" /> : <Eye className="w-3.5 h-3.5" />}
                      </button>
                    </div>
                  </div>
                </div>
                <p className="text-[10px] text-slate-400">
                  Patient can log into the phone app using this Initial Password (via Email or Account ID). They will be prompted to reset it to a personal password upon first login.
                </p>
              </div>

              {/* Patient Demographics */}
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1">
                  <label className="text-slate-400 text-[11px] font-semibold">Account / Pseudo ID *</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. PAT-2026-001"
                    value={formData.pseudo_id}
                    onChange={(e) => setFormData({ ...formData, pseudo_id: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-900 border border-slate-800 rounded-xl text-white font-mono font-bold text-brand-300"
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-slate-400 text-[11px] font-semibold">Full Name *</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. Rahul Sharma"
                    value={formData.full_name}
                    onChange={(e) => setFormData({ ...formData, full_name: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-900 border border-slate-800 rounded-xl text-white"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-4 gap-3">
                <div className="space-y-1">
                  <label className="text-slate-400 text-[11px] font-semibold flex items-center gap-1">
                    <Calendar className="w-3 h-3 text-slate-400" />
                    Date of Birth
                  </label>
                  <input
                    type="date"
                    value={formData.date_of_birth}
                    onChange={(e) => handleDobChange(e.target.value)}
                    className="w-full px-3 py-2 bg-slate-900 border border-slate-800 rounded-xl text-white text-xs"
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-slate-400 text-[11px] font-semibold">Age *</label>
                  <input
                    type="number"
                    min="1"
                    max="120"
                    required
                    placeholder="e.g. 28"
                    value={formData.age}
                    onChange={(e) => setFormData({ ...formData, age: e.target.value === '' ? '' : Number(e.target.value) })}
                    className="w-full px-3 py-2 bg-slate-900 border border-slate-800 rounded-xl text-white font-mono"
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-slate-400 text-[11px] font-semibold">Gender *</label>
                  <select
                    required
                    value={formData.gender}
                    onChange={(e) => setFormData({ ...formData, gender: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-900 border border-slate-800 rounded-xl text-white"
                  >
                    <option value="">Select Gender</option>
                    <option value="FEMALE">Female</option>
                    <option value="MALE">Male</option>
                    <option value="OTHER">Other</option>
                  </select>
                </div>
                <div className="space-y-1">
                  <label className="text-slate-400 text-[11px] font-semibold flex items-center gap-1">
                    <Activity className="w-3 h-3 text-rose-400" />
                    Diagnosed Disease *
                  </label>
                  <select
                    required
                    value={formData.disease_id}
                    onChange={(e) => {
                      const d = diseases.find((item) => item.id === e.target.value);
                      setFormData({
                        ...formData,
                        disease_id: e.target.value,
                        disease_name: d ? d.name : '',
                      });
                    }}
                    className="w-full px-3 py-2 bg-slate-900 border border-slate-800 rounded-xl text-white text-xs"
                  >
                    <option value="">Select Disease...</option>
                    {diseases.map((d) => (
                      <option key={d.id} value={d.id}>
                        {d.name} ({d.code})
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              {/* Mobile Phone Availability & Officer GPS Tracking Controls */}
              <div className="p-3.5 rounded-xl bg-slate-900/60 border border-slate-800 space-y-3">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                  <div>
                    <label className="text-slate-300 text-[11px] font-semibold flex items-center gap-1.5">
                      <Phone className="w-3.5 h-3.5 text-brand-400" />
                      Does the patient have a mobile phone? *
                    </label>
                    <p className="text-[10px] text-slate-400">
                      Determines whether periodic GPS location telemetry is collected from this patient
                    </p>
                  </div>

                  <div className="flex items-center gap-2 shrink-0">
                    <button
                      type="button"
                      onClick={() => {
                        setFormData((prev) => ({ ...prev, has_phone: true }));
                        setPhoneError(null);
                      }}
                      className={`px-3.5 py-1.5 rounded-xl text-xs font-semibold flex items-center gap-1.5 border transition-all cursor-pointer ${
                        formData.has_phone
                          ? 'bg-brand-600 border-brand-500 text-white shadow-md'
                          : 'bg-slate-950 border-slate-800 text-slate-400 hover:text-white'
                      }`}
                    >
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      <span>Yes</span>
                    </button>
                    <button
                      type="button"
                      onClick={() => {
                        setFormData((prev) => ({ ...prev, has_phone: false, contact_number: '' }));
                        setPhoneError(null);
                      }}
                      className={`px-3.5 py-1.5 rounded-xl text-xs font-semibold flex items-center gap-1.5 border transition-all cursor-pointer ${
                        !formData.has_phone
                          ? 'bg-amber-600 border-amber-500 text-white shadow-md'
                          : 'bg-slate-950 border-slate-800 text-slate-400 hover:text-white'
                      }`}
                    >
                      <X className="w-3.5 h-3.5" />
                      <span>No</span>
                    </button>
                  </div>
                </div>

                {formData.has_phone ? (
                  <div className="space-y-3 pt-1 border-t border-slate-800/80">
                    <div className="space-y-1">
                      <div className="flex items-center justify-between">
                        <label className="text-slate-400 text-[11px] font-semibold">Contact Phone Number (10 Digits) *</label>
                        {formData.contact_number && (
                          <span className={`text-[10px] font-mono ${formData.contact_number.length === 10 ? 'text-emerald-400' : 'text-amber-400'}`}>
                            {formData.contact_number.length}/10 digits
                          </span>
                        )}
                      </div>
                      <input
                        type="tel"
                        required
                        inputMode="numeric"
                        maxLength={10}
                        placeholder="Enter exactly 10 numeric digits (e.g. 9847012345)"
                        value={formData.contact_number}
                        onChange={handlePhoneChange}
                        onBlur={handlePhoneBlur}
                        className={`w-full px-3 py-2 bg-slate-950 border rounded-xl text-white font-mono transition-colors ${
                          phoneError ? 'border-rose-500 focus:border-rose-500' : 'border-slate-800 focus:border-brand-500'
                        }`}
                      />
                      {phoneError && (
                        <p className="text-[10px] text-rose-400 flex items-center gap-1 mt-1 font-medium">
                          <AlertCircle className="w-3 h-3 shrink-0" />
                          <span>{phoneError}</span>
                        </p>
                      )}
                    </div>

                    {/* Officer-Configurable GPS Cadence & Active Tracking Days */}
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-1">
                      <div className="space-y-1">
                        <label className="text-slate-400 text-[11px] font-semibold flex items-center gap-1">
                          <Clock className="w-3.5 h-3.5 text-brand-400" />
                          <span>GPS Tracking Interval *</span>
                        </label>
                        <select
                          value={formData.tracking_interval_minutes}
                          onChange={(e) => setFormData({ ...formData, tracking_interval_minutes: Number(e.target.value) })}
                          className="w-full px-3 py-2 bg-slate-950 border border-slate-700 rounded-xl text-white text-xs font-mono"
                        >
                          <option value={1}>1 Minute (High Frequency)</option>
                          <option value={5}>5 Minutes (Intensive Surveillance)</option>
                          <option value={10}>10 Minutes (Standard Monitoring)</option>
                          <option value={15}>15 Minutes (Default Surveillance Protocol)</option>
                        </select>
                        <p className="text-[10px] text-slate-500">Configures periodic sampling cadence</p>
                      </div>

                      <div className="space-y-1">
                        <label className="text-slate-400 text-[11px] font-semibold flex items-center gap-1">
                          <Calendar className="w-3.5 h-3.5 text-brand-400" />
                          <span>Active Tracking Days *</span>
                        </label>
                        <div className="flex flex-wrap gap-1 pt-1">
                          {['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'].map((day) => {
                            const isChecked = formData.tracking_days.includes(day);
                            return (
                              <button
                                type="button"
                                key={day}
                                onClick={() => {
                                  const cur = formData.tracking_days;
                                  const next = isChecked ? cur.filter((d) => d !== day) : [...cur, day];
                                  setFormData({ ...formData, tracking_days: next });
                                }}
                                className={`px-2 py-1 rounded text-[10px] font-semibold border transition-all ${
                                  isChecked
                                    ? 'bg-brand-500/20 text-brand-300 border-brand-500/40'
                                    : 'bg-slate-950 text-slate-500 border-slate-800 hover:text-slate-300'
                                }`}
                              >
                                {day.slice(0, 3)}
                              </button>
                            );
                          })}
                        </div>
                        <p className="text-[10px] text-slate-500">Telemetry collected only on selected days</p>
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="p-2.5 rounded-lg bg-slate-950 border border-slate-800 text-[11px] text-amber-400 flex items-center gap-2">
                    <AlertTriangle className="w-3.5 h-3.5 shrink-0 text-amber-400" />
                    <span>No mobile phone. Patient will be represented by their official Kerala administrative centroid (STATIC_ADMIN_LOCATION) without fake GPS tracks.</span>
                  </div>
                )}

                {/* Surveillance / Monitoring Days Configuration */}
                <div className="pt-3 border-t border-slate-800/80 space-y-2">
                  <div className="flex items-center justify-between">
                    <label className="text-slate-300 text-[11px] font-semibold flex items-center gap-1.5">
                      <Clock className="w-3.5 h-3.5 text-cyan-400" />
                      <span>Monitoring Period (Days) *</span>
                    </label>
                    <span className="text-xs font-mono font-bold text-cyan-300 bg-cyan-950/80 px-2 py-0.5 rounded border border-cyan-800/60">
                      {formData.monitoring_days} Days Active Protocol
                    </span>
                  </div>
                  <div className="flex items-center gap-1.5 flex-wrap">
                    {[7, 14, 21, 28, 30].map((days) => (
                      <button
                        type="button"
                        key={days}
                        onClick={() => setFormData({ ...formData, monitoring_days: days })}
                        className={`px-2.5 py-1 rounded-lg text-[10px] font-semibold border transition-all cursor-pointer ${
                          formData.monitoring_days === days
                            ? 'bg-cyan-500/20 text-cyan-300 border-cyan-500/50 shadow-sm'
                            : 'bg-slate-950 text-slate-400 border-slate-800 hover:text-white'
                        }`}
                      >
                        {days} Days
                      </button>
                    ))}
                    <div className="flex items-center gap-1.5 ml-auto">
                      <span className="text-[10px] text-slate-400 font-sans">Custom:</span>
                      <input
                        type="number"
                        min={1}
                        max={180}
                        required
                        value={formData.monitoring_days}
                        onChange={(e) => setFormData({ ...formData, monitoring_days: Math.max(1, Number(e.target.value)) })}
                        className="w-16 px-2 py-1 bg-slate-950 border border-slate-700 rounded-lg text-white text-xs font-mono text-center focus:border-cyan-400 focus:outline-none"
                      />
                      <span className="text-[10px] text-slate-400">days</span>
                    </div>
                  </div>
                  <p className="text-[10px] text-slate-500">
                    Defines the assigned surveillance & quarantine observation period. This can be edited anytime later.
                  </p>
                </div>
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

              {/* Kerala Administrative Location Hierarchy */}
              <div className="p-3.5 rounded-xl bg-slate-900/60 border border-slate-800 space-y-3">
                <span className="text-[11px] font-bold text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
                  <MapPin className="w-3.5 h-3.5 text-brand-400" />
                  Kerala Administrative Hierarchy
                </span>

                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                  {/* District Dropdown (14 districts) */}
                  <div className="space-y-1">
                    <label className="text-slate-400 text-[11px] font-semibold">District (All 14) *</label>
                    <select
                      required
                      value={formData.district_id}
                      onChange={(e) => handleAddDistrictChange(e.target.value)}
                      className="w-full px-3 py-2 bg-slate-950 border border-slate-700 rounded-xl text-white text-xs"
                    >
                      <option value="">Select District</option>
                      {districts.map((d) => (
                        <option key={d.id} value={d.id}>
                          {d.name}
                        </option>
                      ))}
                    </select>
                  </div>

                  {/* Local Body Dropdown (Cascading) */}
                  <div className="space-y-1">
                    <label className="text-slate-400 text-[11px] font-semibold">Local Body *</label>
                    <select
                      required
                      disabled={!formData.district_id}
                      value={formData.local_body_id}
                      onChange={(e) => handleAddLocalBodyChange(e.target.value)}
                      className="w-full px-3 py-2 bg-slate-950 border border-slate-700 rounded-xl text-white text-xs disabled:opacity-50"
                    >
                      <option value="">
                        {!formData.district_id ? "Select District first" : "Select Local Body"}
                      </option>
                      {addLocalBodies.map((lb) => (
                        <option key={lb.id} value={lb.id}>
                          {lb.name} ({lb.body_type})
                        </option>
                      ))}
                    </select>
                  </div>

                  {/* Ward Dropdown (Cascading & Searchable) */}
                  <div className="space-y-1">
                    <label className="text-slate-400 text-[11px] font-semibold">Ward (Searchable) *</label>
                    <SearchableSelect
                      id="add-patient-ward-select"
                      value={formData.ward_id}
                      onChange={(val) => handleAddWardChange(val)}
                      options={addWards.map((w) => ({
                        value: w.id,
                        label: `Ward #${w.ward_number} - ${w.name}`,
                        code: w.ward_code,
                        number: w.ward_number,
                        sublabel: w.ward_code ? `Official Code: ${w.ward_code}` : undefined,
                      }))}
                      placeholder={
                        !formData.local_body_id
                          ? "Select Local Body first"
                          : "Search and select ward..."
                      }
                      disabled={!formData.local_body_id || addWards.length === 0}
                      disabledPlaceholder={!formData.local_body_id ? "Select Local Body first" : "No wards found"}
                      required
                    />
                  </div>
                </div>

                {!formData.has_phone && (
                  <div className="p-3.5 rounded-xl bg-cyan-950/40 border border-cyan-500/30 space-y-2 mt-2">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-semibold text-cyan-300 flex items-center gap-1.5">
                        <MapPin className="w-4 h-4 text-cyan-400" />
                        <span>Assigned Administrative Surveillance Location (No Phone)</span>
                      </span>
                      <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-cyan-500/20 text-cyan-300 border border-cyan-500/30 font-bold">
                        AUTO-MAPPED
                      </span>
                    </div>

                    <p className="text-[11px] text-slate-300">
                      Because this patient does not have a mobile phone, their spatial location in surveillance and heatmaps will be mapped according to their registered Kerala administrative hierarchy:
                    </p>

                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 text-xs">
                      <div className="p-2 rounded-lg bg-slate-900 border border-slate-800">
                        <span className="text-[10px] text-slate-400 uppercase font-mono block">1. District</span>
                        <span className="font-semibold text-white">{createSelectedDist?.name || 'Please select'}</span>
                      </div>
                      <div className="p-2 rounded-lg bg-slate-900 border border-slate-800">
                        <span className="text-[10px] text-slate-400 uppercase font-mono block">2. Panchayath / Local Body</span>
                        <span className="font-semibold text-cyan-300 truncate block">{createSelectedLb?.name || 'Please select'}</span>
                      </div>
                      <div className="p-2 rounded-lg bg-slate-900 border border-slate-800">
                        <span className="text-[10px] text-slate-400 uppercase font-mono block">3. Ward</span>
                        <span className="font-semibold text-emerald-400">
                          {createSelectedWard ? `Ward #${createSelectedWard.ward_number} (${createSelectedWard.name})` : 'Please select'}
                        </span>
                      </div>
                    </div>

                    {createAssignedCoords && (
                      <div className="p-2 rounded-lg bg-slate-950 border border-slate-800 flex items-center justify-between text-[11px] font-mono">
                        <span className="text-slate-400 font-sans">Centroid Coordinates:</span>
                        <span className="text-cyan-400 font-bold">
                          Lat {createAssignedCoords[0].toFixed(5)}, Lng {createAssignedCoords[1].toFixed(5)}
                        </span>
                        <span className="text-[10px] text-slate-500 font-sans font-medium">
                          ({createSelectedWard ? 'Ward Level Centroid' : createSelectedLb ? 'Panchayath Level Centroid' : 'District Centroid'})
                        </span>
                      </div>
                    )}
                  </div>
                )}
              </div>

              <div className="flex justify-end gap-3 pt-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={actionLoading}
                  className="px-5 py-2 rounded-xl bg-brand-600 hover:bg-brand-500 text-white text-xs font-semibold shadow-md disabled:opacity-50 flex items-center gap-2 cursor-pointer"
                >
                  {actionLoading && <RefreshCw className="w-3.5 h-3.5 animate-spin" />}
                  <span>Save Patient & Create Account</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ------------------------------------------------------------------ */}
      {/* 2. Edit Patient Modal */}
      {/* ------------------------------------------------------------------ */}
      {editingPatient && (
        <div className="fixed inset-0 bg-slate-950/85 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="glass-panel max-w-xl w-full rounded-2xl p-6 space-y-5 border border-slate-700 max-h-[90vh] overflow-y-auto shadow-2xl">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2.5">
                <Edit2 className="w-5 h-5 text-cyan-400" />
                <div>
                  <h3 className="text-base font-bold text-white">Edit Patient Record ({editingPatient.pseudo_id})</h3>
                  <p className="text-[11px] text-slate-400">Update demographic, administrative location, or account credentials</p>
                </div>
              </div>
              <button
                onClick={() => setEditingPatient(null)}
                className="p-1 rounded-lg text-slate-400 hover:text-white bg-slate-800"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {actionSuccess && (
              <div className="p-3 rounded-xl bg-emerald-500/15 border border-emerald-500/30 text-emerald-300 text-xs flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                <span>{actionSuccess}</span>
              </div>
            )}

            {actionError && (
              <div className="p-3 rounded-xl bg-rose-500/15 border border-rose-500/30 text-rose-300 text-xs flex items-center gap-2">
                <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
                <span>{actionError}</span>
              </div>
            )}

            <form onSubmit={handleUpdatePatient} className="space-y-4 text-xs">
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1">
                  <label className="text-slate-400 text-[11px] font-semibold">Full Name *</label>
                  <input
                    type="text"
                    required
                    value={editFormData.full_name}
                    onChange={(e) => setEditFormData({ ...editFormData, full_name: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-900 border border-slate-800 rounded-xl text-white"
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-slate-400 text-[11px] font-semibold flex items-center gap-1">
                    <Activity className="w-3 h-3 text-rose-400" />
                    Diagnosed Condition *
                  </label>
                  <select
                    value={editFormData.disease_id}
                    onChange={(e) => {
                      const d = diseases.find((item) => item.id === e.target.value);
                      setEditFormData({
                        ...editFormData,
                        disease_id: e.target.value,
                        disease_name: d ? d.name : '',
                      });
                    }}
                    className="w-full px-3 py-2 bg-slate-900 border border-slate-800 rounded-xl text-white text-xs"
                  >
                    <option value="">Select Condition...</option>
                    {diseases.map((d) => (
                      <option key={d.id} value={d.id}>
                        {d.name} ({d.code}) &bull; {d.contagion_type}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <div className="space-y-1">
                  <label className="text-slate-400 text-[11px] font-semibold flex items-center gap-1">
                    <Calendar className="w-3 h-3 text-slate-400" />
                    Date of Birth
                  </label>
                  <input
                    type="date"
                    value={editFormData.date_of_birth}
                    onChange={(e) => handleEditDobChange(e.target.value)}
                    className="w-full px-3 py-2 bg-slate-900 border border-slate-800 rounded-xl text-white text-xs"
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-slate-400 text-[11px] font-semibold">Age *</label>
                  <input
                    type="number"
                    min="1"
                    max="120"
                    required
                    value={editFormData.age}
                    onChange={(e) => setEditFormData({ ...editFormData, age: Number(e.target.value) })}
                    className="w-full px-3 py-2 bg-slate-900 border border-slate-800 rounded-xl text-white font-mono"
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-slate-400 text-[11px] font-semibold">Gender *</label>
                  <select
                    value={editFormData.gender}
                    onChange={(e) => setEditFormData({ ...editFormData, gender: e.target.value })}
                    className="w-full px-3 py-2 bg-slate-900 border border-slate-800 rounded-xl text-white"
                  >
                    <option value="FEMALE">Female</option>
                    <option value="MALE">Male</option>
                    <option value="OTHER">Other</option>
                  </select>
                </div>
              </div>

              {/* Mobile Phone Availability in Edit Modal */}
              <div className="p-3.5 rounded-xl bg-slate-900/60 border border-slate-800 space-y-3">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                  <div>
                    <label className="text-slate-300 text-[11px] font-semibold flex items-center gap-1.5">
                      <Phone className="w-3.5 h-3.5 text-brand-400" />
                      Does the patient have a mobile phone?
                    </label>
                    <p className="text-[10px] text-slate-400">
                      Toggle whether mobile GPS telemetry is active for this patient account
                    </p>
                  </div>

                  <div className="flex items-center gap-2 shrink-0">
                    <button
                      type="button"
                      onClick={() => {
                        setEditFormData((prev) => ({ ...prev, has_phone: true }));
                        setEditPhoneError(null);
                      }}
                      className={`px-3 py-1 rounded-xl text-xs font-semibold border transition-all cursor-pointer ${
                        editFormData.has_phone
                          ? 'bg-cyan-600 border-cyan-500 text-white shadow-md'
                          : 'bg-slate-950 border-slate-800 text-slate-400 hover:text-white'
                      }`}
                    >
                      <span>Yes</span>
                    </button>
                    <button
                      type="button"
                      onClick={() => {
                        setEditFormData((prev) => ({ ...prev, has_phone: false, contact_number: '' }));
                        setEditPhoneError(null);
                      }}
                      className={`px-3 py-1 rounded-xl text-xs font-semibold border transition-all cursor-pointer ${
                        !editFormData.has_phone
                          ? 'bg-amber-600 border-amber-500 text-white shadow-md'
                          : 'bg-slate-950 border-slate-800 text-slate-400 hover:text-white'
                      }`}
                    >
                      <span>No</span>
                    </button>
                  </div>
                </div>

                {editFormData.has_phone ? (
                  <div className="space-y-3 pt-1 border-t border-slate-800/80">
                    <div className="space-y-1">
                      <div className="flex items-center justify-between">
                        <label className="text-slate-400 text-[11px] font-semibold">Contact Phone (10 Digits) *</label>
                        {editFormData.contact_number && (
                          <span className={`text-[10px] font-mono ${editFormData.contact_number.length === 10 ? 'text-emerald-400' : 'text-amber-400'}`}>
                            {editFormData.contact_number.length}/10 digits
                          </span>
                        )}
                      </div>
                      <input
                        type="tel"
                        required
                        inputMode="numeric"
                        maxLength={10}
                        value={editFormData.contact_number}
                        onChange={handleEditPhoneChange}
                        className={`w-full px-3 py-2 bg-slate-950 border rounded-xl text-white font-mono ${
                          editPhoneError ? 'border-rose-500' : 'border-slate-800'
                        }`}
                      />
                      {editPhoneError && (
                        <p className="text-[10px] text-rose-400 flex items-center gap-1 mt-1 font-medium">
                          <AlertCircle className="w-3 h-3 shrink-0" />
                          <span>{editPhoneError}</span>
                        </p>
                      )}
                    </div>

                    {/* Officer-Configurable GPS Cadence & Active Tracking Days in Edit Modal */}
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-1">
                      <div className="space-y-1">
                        <label className="text-slate-400 text-[11px] font-semibold flex items-center gap-1">
                          <Clock className="w-3.5 h-3.5 text-brand-400" />
                          <span>GPS Tracking Interval</span>
                        </label>
                        <select
                          value={editFormData.tracking_interval_minutes}
                          onChange={(e) => setEditFormData({ ...editFormData, tracking_interval_minutes: Number(e.target.value) })}
                          className="w-full px-3 py-2 bg-slate-950 border border-slate-700 rounded-xl text-white text-xs font-mono"
                        >
                          <option value={1}>1 Minute (High Frequency)</option>
                          <option value={5}>5 Minutes (Intensive Surveillance)</option>
                          <option value={10}>10 Minutes (Standard Monitoring)</option>
                          <option value={15}>15 Minutes (Default Surveillance Protocol)</option>
                        </select>
                      </div>

                      <div className="space-y-1">
                        <label className="text-slate-400 text-[11px] font-semibold flex items-center gap-1">
                          <Calendar className="w-3.5 h-3.5 text-brand-400" />
                          <span>Active Tracking Days</span>
                        </label>
                        <div className="flex flex-wrap gap-1 pt-1">
                          {['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'].map((day) => {
                            const isChecked = editFormData.tracking_days.includes(day);
                            return (
                              <button
                                type="button"
                                key={day}
                                onClick={() => {
                                  const cur = editFormData.tracking_days;
                                  const next = isChecked ? cur.filter((d) => d !== day) : [...cur, day];
                                  setEditFormData({ ...editFormData, tracking_days: next });
                                }}
                                className={`px-2 py-1 rounded text-[10px] font-semibold border transition-all ${
                                  isChecked
                                    ? 'bg-cyan-500/20 text-cyan-300 border-cyan-500/40'
                                    : 'bg-slate-950 text-slate-500 border-slate-800 hover:text-slate-300'
                                }`}
                              >
                                {day.slice(0, 3)}
                              </button>
                            );
                          })}
                        </div>
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="p-2.5 rounded-lg bg-slate-950 border border-slate-800 text-[11px] text-amber-400 flex items-center gap-2">
                    <AlertTriangle className="w-3.5 h-3.5 shrink-0 text-amber-400" />
                    <span>No mobile phone. Patient represented by static administrative centroid (STATIC_ADMIN_LOCATION).</span>
                  </div>
                )}

                {/* Surveillance / Monitoring Days Configuration (Editable) */}
                <div className="pt-3 border-t border-slate-800/80 space-y-2">
                  <div className="flex items-center justify-between">
                    <label className="text-slate-300 text-[11px] font-semibold flex items-center gap-1.5">
                      <Clock className="w-3.5 h-3.5 text-cyan-400" />
                      <span>Monitoring Period (Days) *</span>
                    </label>
                    <span className="text-xs font-mono font-bold text-cyan-300 bg-cyan-950/80 px-2 py-0.5 rounded border border-cyan-800/60">
                      {editFormData.monitoring_days} Days Active Protocol
                    </span>
                  </div>
                  <div className="flex items-center gap-1.5 flex-wrap">
                    {[7, 14, 21, 28, 30].map((days) => (
                      <button
                        type="button"
                        key={days}
                        onClick={() => setEditFormData({ ...editFormData, monitoring_days: days })}
                        className={`px-2.5 py-1 rounded-lg text-[10px] font-semibold border transition-all cursor-pointer ${
                          editFormData.monitoring_days === days
                            ? 'bg-cyan-500/20 text-cyan-300 border-cyan-500/50 shadow-sm'
                            : 'bg-slate-950 text-slate-400 border-slate-800 hover:text-white'
                        }`}
                      >
                        {days} Days
                      </button>
                    ))}
                    <div className="flex items-center gap-1.5 ml-auto">
                      <span className="text-[10px] text-slate-400 font-sans">Custom:</span>
                      <input
                        type="number"
                        min={1}
                        max={180}
                        required
                        value={editFormData.monitoring_days}
                        onChange={(e) => setEditFormData({ ...editFormData, monitoring_days: Math.max(1, Number(e.target.value)) })}
                        className="w-16 px-2 py-1 bg-slate-950 border border-slate-700 rounded-lg text-white text-xs font-mono text-center focus:border-cyan-400 focus:outline-none"
                      />
                      <span className="text-[10px] text-slate-400">days</span>
                    </div>
                  </div>
                  <p className="text-[10px] text-slate-500">
                    Edit the assigned quarantine/surveillance monitoring window for this patient.
                  </p>
                </div>
              </div>

              <div className="space-y-1">
                <label className="text-slate-400 text-[11px] font-semibold">Residential Address *</label>
                <input
                  type="text"
                  required
                  value={editFormData.address}
                  onChange={(e) => setEditFormData({ ...editFormData, address: e.target.value })}
                  className="w-full px-3 py-2 bg-slate-900 border border-slate-800 rounded-xl text-white"
                />
              </div>

              {/* Account Credentials Update */}
              <div className="p-3.5 rounded-xl bg-slate-900/60 border border-slate-800 space-y-3">
                <span className="text-[11px] font-bold text-cyan-400 uppercase tracking-wider flex items-center gap-1.5">
                  <KeyRound className="w-3.5 h-3.5" />
                  Linked Login Account
                </span>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div className="space-y-1">
                    <label className="text-slate-400 text-[11px] font-semibold">Account Email</label>
                    <input
                      type="email"
                      value={editFormData.email}
                      onChange={(e) => setEditFormData({ ...editFormData, email: e.target.value })}
                      className="w-full px-3 py-2 bg-slate-950 border border-slate-700 rounded-xl text-white font-mono"
                    />
                  </div>
                  <div className="space-y-1">
                    <label className="text-slate-400 text-[11px] font-semibold">New Password (leave blank to keep)</label>
                    <div className="relative">
                      <input
                        type={showEditPassword ? 'text' : 'password'}
                        placeholder="••••••••••••"
                        value={editFormData.password}
                        onChange={(e) => setEditFormData({ ...editFormData, password: e.target.value })}
                        className="w-full px-3 py-2 pr-10 bg-slate-950 border border-slate-700 rounded-xl text-white font-mono"
                      />
                      <button
                        type="button"
                        id="toggle-edit-password-btn"
                        onClick={() => setShowEditPassword(!showEditPassword)}
                        aria-label={showEditPassword ? 'Hide password' : 'Show password'}
                        title={showEditPassword ? 'Hide password' : 'Show password'}
                        className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-200 transition-colors p-1 cursor-pointer focus:outline-none"
                      >
                        {showEditPassword ? <EyeOff className="w-3.5 h-3.5 text-brand-400" /> : <Eye className="w-3.5 h-3.5" />}
                      </button>
                    </div>
                  </div>
                </div>
              </div>

              {/* Cascading Administrative Location Hierarchy */}
              <div className="p-3.5 rounded-xl bg-slate-900/60 border border-slate-800 space-y-3">
                <span className="text-[11px] font-bold text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
                  <MapPin className="w-3.5 h-3.5 text-brand-400" />
                  Kerala Administrative Hierarchy
                </span>

                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                  {/* District Dropdown */}
                  <div className="space-y-1">
                    <label className="text-slate-400 text-[11px] font-semibold">District (All 14) *</label>
                    <select
                      value={editFormData.district_id}
                      onChange={(e) => handleEditDistrictChange(e.target.value)}
                      className="w-full px-3 py-2 bg-slate-950 border border-slate-700 rounded-xl text-white text-xs"
                    >
                      {districts.map((d) => (
                        <option key={d.id} value={d.id}>
                          {d.name}
                        </option>
                      ))}
                    </select>
                  </div>

                  {/* Local Body Dropdown */}
                  <div className="space-y-1">
                    <label className="text-slate-400 text-[11px] font-semibold">Local Body *</label>
                    <select
                      value={editFormData.local_body_id}
                      onChange={(e) => handleEditLocalBodyChange(e.target.value)}
                      className="w-full px-3 py-2 bg-slate-950 border border-slate-700 rounded-xl text-white text-xs"
                    >
                      {editLocalBodies.map((lb) => (
                        <option key={lb.id} value={lb.id}>
                          {lb.name} ({lb.body_type})
                        </option>
                      ))}
                    </select>
                  </div>

                  {/* Ward Dropdown (Cascading & Searchable) */}
                  <div className="space-y-1">
                    <label className="text-slate-400 text-[11px] font-semibold">Ward (Searchable) *</label>
                    <SearchableSelect
                      id="edit-patient-ward-select"
                      value={editFormData.ward_id}
                      onChange={(val) => handleEditWardChange(val)}
                      options={editWards.map((w) => ({
                        value: w.id,
                        label: `Ward #${w.ward_number} - ${w.name}`,
                        code: w.ward_code,
                        number: w.ward_number,
                        sublabel: w.ward_code ? `Official Code: ${w.ward_code}` : undefined,
                      }))}
                      placeholder="Search ward name, code (e.g. THUMPOLY)..."
                      disabled={!editFormData.local_body_id || editWards.length === 0}
                      disabledPlaceholder={!editFormData.local_body_id ? "Select Local Body first" : "No wards found"}
                      required
                    />
                  </div>
                </div>

                {!editFormData.has_phone && (
                  <div className="p-3.5 rounded-xl bg-cyan-950/40 border border-cyan-500/30 space-y-2 mt-2">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-semibold text-cyan-300 flex items-center gap-1.5">
                        <MapPin className="w-4 h-4 text-cyan-400" />
                        <span>Assigned Administrative Surveillance Location (No Phone)</span>
                      </span>
                      <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-cyan-500/20 text-cyan-300 border border-cyan-500/30 font-bold">
                        AUTO-MAPPED
                      </span>
                    </div>

                    <p className="text-[11px] text-slate-300">
                      Because this patient does not have a mobile phone, their spatial location in surveillance and heatmaps will be mapped according to their registered Kerala administrative hierarchy:
                    </p>

                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 text-xs">
                      <div className="p-2 rounded-lg bg-slate-900 border border-slate-800">
                        <span className="text-[10px] text-slate-400 uppercase font-mono block">1. District</span>
                        <span className="font-semibold text-white">{editSelectedDist?.name || 'Please select'}</span>
                      </div>
                      <div className="p-2 rounded-lg bg-slate-900 border border-slate-800">
                        <span className="text-[10px] text-slate-400 uppercase font-mono block">2. Panchayath / Local Body</span>
                        <span className="font-semibold text-cyan-300 truncate block">{editSelectedLb?.name || 'Please select'}</span>
                      </div>
                      <div className="p-2 rounded-lg bg-slate-900 border border-slate-800">
                        <span className="text-[10px] text-slate-400 uppercase font-mono block">3. Ward</span>
                        <span className="font-semibold text-emerald-400">
                          {editSelectedWard ? `Ward #${editSelectedWard.ward_number} (${editSelectedWard.name})` : 'Please select'}
                        </span>
                      </div>
                    </div>

                    {editAssignedCoords && (
                      <div className="p-2 rounded-lg bg-slate-950 border border-slate-800 flex items-center justify-between text-[11px] font-mono">
                        <span className="text-slate-400 font-sans">Centroid Coordinates:</span>
                        <span className="text-cyan-400 font-bold">
                          Lat {editAssignedCoords[0].toFixed(5)}, Lng {editAssignedCoords[1].toFixed(5)}
                        </span>
                        <span className="text-[10px] text-slate-500 font-sans font-medium">
                          ({editSelectedWard ? 'Ward Level Centroid' : editSelectedLb ? 'Panchayath Level Centroid' : 'District Centroid'})
                        </span>
                      </div>
                    )}
                  </div>
                )}
              </div>

              {/* Status toggle */}
              <div className="space-y-1 pt-1">
                <label className="text-slate-400 text-[11px] font-semibold">Surveillance & Account Status</label>
                <div className="flex items-center gap-4 pt-1">
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="radio"
                      checked={editFormData.is_active}
                      onChange={() => setEditFormData({ ...editFormData, is_active: true })}
                    />
                    <span className="text-emerald-400 font-semibold">Active Surveillance</span>
                  </label>
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="radio"
                      checked={!editFormData.is_active}
                      onChange={() => setEditFormData({ ...editFormData, is_active: false })}
                    />
                    <span className="text-slate-400 font-semibold">Inactive / Deactivated</span>
                  </label>
                </div>
              </div>

              <div className="flex justify-end gap-3 pt-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setEditingPatient(null)}
                  className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={actionLoading}
                  className="px-5 py-2 rounded-xl bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-semibold shadow-md disabled:opacity-50 flex items-center gap-2 cursor-pointer"
                >
                  {actionLoading && <RefreshCw className="w-3.5 h-3.5 animate-spin" />}
                  <span>Save Changes</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ------------------------------------------------------------------ */}
      {/* 3. Delete / Deactivation Confirmation Dialog */}
      {/* ------------------------------------------------------------------ */}
      {deletingPatient && (
        <div className="fixed inset-0 bg-slate-950/85 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="glass-panel max-w-md w-full rounded-2xl p-6 space-y-4 border border-rose-500/30 shadow-2xl">
            <div className="w-12 h-12 rounded-2xl bg-rose-500/15 border border-rose-500/30 flex items-center justify-center text-rose-400 mx-auto">
              <AlertTriangle className="w-6 h-6" />
            </div>

            <div className="text-center space-y-2">
              <h3 className="text-base font-bold text-white">
                Deactivate Patient Record & Account?
              </h3>
              <p className="text-xs text-slate-300 font-mono">
                {deletingPatient.pseudo_id} &bull; {deletingPatient.full_name}
              </p>
              <p className="text-xs text-slate-400 leading-relaxed pt-1">
                Deactivating disables login access and revokes active quarantine monitoring while preserving all historical telemetry logs for audit.
              </p>
            </div>

            {actionError && (
              <div className="p-3 rounded-xl bg-rose-500/15 border border-rose-500/30 text-rose-300 text-xs flex items-center gap-2">
                <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
                <span>{actionError}</span>
              </div>
            )}

            <div className="flex justify-center gap-3 pt-2">
              <button
                type="button"
                onClick={() => setDeletingPatient(null)}
                disabled={actionLoading}
                className="px-4 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold cursor-pointer"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleConfirmDelete}
                disabled={actionLoading}
                className="px-5 py-2.5 rounded-xl bg-rose-600 hover:bg-rose-500 text-white text-xs font-semibold shadow-lg shadow-rose-600/20 flex items-center gap-2 cursor-pointer"
              >
                {actionLoading && <RefreshCw className="w-3.5 h-3.5 animate-spin" />}
                <span>Confirm Deactivation</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ------------------------------------------------------------------ */}
      {/* 4. Patient Detail Modal (Clear Administrative Location vs GPS Telemetry) */}
      {/* ------------------------------------------------------------------ */}
      {selectedPatient && (
        <div className="fixed inset-0 bg-slate-950/85 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="glass-panel max-w-xl w-full rounded-2xl p-6 space-y-5 border border-slate-700 shadow-2xl max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div>
                <span className="text-[10px] font-mono uppercase text-slate-500">Individual Patient Record</span>
                <h3 className="text-lg font-bold text-white">{selectedPatient.pseudo_id}</h3>
              </div>
              <button
                onClick={() => setSelectedPatient(null)}
                className="p-1 rounded-lg text-slate-400 hover:text-white bg-slate-800"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-4 text-xs">
              {/* Header card */}
              <div className="p-3.5 rounded-xl bg-slate-900/60 border border-slate-800 flex items-center justify-between">
                <div>
                  <span className="text-slate-500 block text-[10px] uppercase font-mono">Full Name</span>
                  <span className="font-semibold text-white text-sm">{selectedPatient.full_name}</span>
                  <span className="text-slate-400 block text-[11px] font-sans mt-0.5">{selectedPatient.age} Yrs &bull; {selectedPatient.gender}</span>
                </div>
                <span className={`px-2.5 py-1 rounded text-[10px] font-bold ${
                  selectedPatient.is_active ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30' : 'bg-slate-800 text-slate-400'
                }`}>
                  {selectedPatient.is_active ? 'ACTIVE SURVEILLANCE' : 'INACTIVE'}
                </span>
              </div>

              {/* Disease Condition & Phone Status */}
              <div className="grid grid-cols-2 gap-3">
                <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800 space-y-1">
                  <span className="text-slate-500 block text-[10px] uppercase font-mono flex items-center gap-1">
                    <Activity className="w-3 h-3 text-rose-400" />
                    Diagnosed Condition
                  </span>
                  <span className="font-semibold text-rose-300 text-xs block">
                    {selectedPatient.disease_name || 'Under Surveillance Evaluation'}
                  </span>
                </div>
                <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800 space-y-1">
                  <span className="text-slate-500 block text-[10px] uppercase font-mono flex items-center gap-1">
                    <Phone className="w-3 h-3 text-brand-400" />
                    Mobile Phone Status
                  </span>
                  <span className="font-semibold text-white text-xs block">
                    {selectedPatient.has_phone === false || !selectedPatient.contact_number ? (
                      <span className="text-amber-400 font-sans">No Mobile Phone (GPS Inactive)</span>
                    ) : (
                      <span className="font-mono text-emerald-400">{selectedPatient.contact_number}</span>
                    )}
                  </span>
                </div>
                <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800 space-y-1 col-span-2">
                  <span className="text-slate-500 block text-[10px] uppercase font-mono flex items-center gap-1">
                    <Clock className="w-3 h-3 text-cyan-400" />
                    Assigned Surveillance Monitoring Period
                  </span>
                  <span className="font-semibold text-cyan-300 text-xs block font-mono flex items-center gap-2">
                    <span>{selectedPatient.monitoring_days || 14} Days Protocol</span>
                    <span className="text-slate-500">&bull;</span>
                    <span className="text-slate-400 font-sans text-[11px]">Active: {selectedPatient.tracking_days || 'All Days'}</span>
                  </span>
                </div>
              </div>

              {/* Linked Account Details */}
              <div className="p-3.5 rounded-xl bg-brand-950/20 border border-brand-500/30 space-y-2">
                <span className="text-brand-400 block text-[10px] uppercase font-mono font-bold flex items-center gap-1.5">
                  <KeyRound className="w-3.5 h-3.5" />
                  Individual Account Credentials
                </span>
                <div className="grid grid-cols-2 gap-3 pt-1">
                  <div>
                    <span className="text-slate-500 block text-[10px]">Account ID (Pseudo ID)</span>
                    <span className="font-mono font-bold text-white text-xs">{selectedPatient.pseudo_id}</span>
                  </div>
                  <div>
                    <span className="text-slate-500 block text-[10px]">Login Email</span>
                    <span className="font-mono text-white text-xs truncate block">{selectedPatient.account_email || 'Linked User Account'}</span>
                  </div>
                </div>
              </div>

              {/* Administrative Location Hierarchy */}
              <div className="p-3.5 rounded-xl bg-slate-900/60 border border-slate-800 space-y-2">
                <span className="text-slate-400 block text-[10px] uppercase font-mono font-bold flex items-center gap-1.5">
                  <MapPin className="w-3.5 h-3.5 text-brand-400" />
                  Administrative Location (Kerala)
                </span>
                <div className="grid grid-cols-3 gap-2 pt-1 font-mono text-[11px]">
                  <div className="p-2 rounded-lg bg-slate-950 border border-slate-800">
                    <span className="text-slate-500 block text-[9px] uppercase">District</span>
                    <span className="text-white font-semibold">{selectedPatient.district_name}</span>
                  </div>
                  <div className="p-2 rounded-lg bg-slate-950 border border-slate-800">
                    <span className="text-slate-500 block text-[9px] uppercase">Local Body</span>
                    <span className="text-white font-semibold truncate block">{selectedPatient.local_body_name}</span>
                  </div>
                  <div className="p-2 rounded-lg bg-slate-950 border border-slate-800">
                    <span className="text-slate-500 block text-[9px] uppercase">Ward</span>
                    <span className="text-white font-semibold block truncate">
                      #{selectedPatient.ward_number} {selectedPatient.ward_name ? `(${selectedPatient.ward_name})` : ''}
                    </span>
                    {selectedPatient.ward_code && (
                      <span className="text-[10px] text-indigo-400 font-mono block mt-0.5">
                        Code: {selectedPatient.ward_code}
                      </span>
                    )}
                  </div>
                </div>
                <div className="text-[11px] text-slate-300 pt-1">
                  <span className="text-slate-500 font-mono">Address: </span>
                  {selectedPatient.address}
                </div>
              </div>

              {/* Surveillance Location & GPS Cadence Section */}
              {selectedPatient.has_phone !== false ? (
                <div className="p-3.5 rounded-xl bg-slate-900/60 border border-slate-800 space-y-2">
                  <span className="text-slate-400 block text-[10px] uppercase font-mono font-bold flex items-center gap-1.5">
                    <Clock className="w-3.5 h-3.5 text-cyan-400" />
                    Surveillance GPS Sampling Interval (Officer Configurable)
                  </span>
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pt-1">
                    <div className="flex items-center gap-2">
                      <label className="text-[11px] text-slate-400">Cadence:</label>
                      <select
                        value={samplingInterval}
                        onChange={(e) => setSamplingInterval(Number(e.target.value))}
                        className="px-3 py-1.5 bg-slate-950 border border-slate-700 rounded-xl text-white text-xs font-mono"
                      >
                        <option value={1}>1 Minute (High Precision Testing)</option>
                        <option value={5}>5 Minutes</option>
                        <option value={10}>10 Minutes</option>
                        <option value={15}>15 Minutes (Default Standard)</option>
                        <option value={30}>30 Minutes</option>
                        <option value={60}>60 Minutes (Hourly Cadence)</option>
                      </select>
                    </div>
                    <span className="text-[11px] text-cyan-400 font-mono font-semibold">
                      ~{samplingInterval} min telemetry interval
                    </span>
                  </div>
                  <p className="text-[10px] text-slate-500">
                    Configures how frequently the mobile client captures and logs GPS observations during authorized monitoring sessions.
                  </p>
                </div>
              ) : null}

              {/* Spatial Location Telemetry Display (GPS vs No-Phone Administrative Location) */}
              <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-slate-300 text-xs uppercase font-mono font-bold flex items-center gap-1.5">
                    {selectedPatient.has_phone === false ? (
                      <>
                        <MapPin className="w-4 h-4 text-cyan-400" />
                        <span>Administrative Location (Ward / Panchayath / District)</span>
                      </>
                    ) : (
                      <>
                        <Navigation className="w-4 h-4 text-emerald-400" />
                        <span>Real-time GPS Telemetry (Latest Observation)</span>
                      </>
                    )}
                  </span>
                  {selectedPatient.has_phone === false ? (
                    <span className="text-[10px] px-2 py-0.5 rounded-full bg-cyan-500/15 border border-cyan-500/30 text-cyan-300 font-mono font-semibold">
                      NO PHONE &bull; STATIC ADMIN LOCATION
                    </span>
                  ) : (
                    <span className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-500/15 border border-emerald-500/30 text-emerald-400 font-mono font-semibold">
                      GPS ACTIVE
                    </span>
                  )}
                </div>

                {selectedPatient.has_phone === false ? (
                  <div className="space-y-3">
                    <div className="p-3 rounded-xl bg-cyan-950/30 border border-cyan-500/30 space-y-2">
                      <div className="flex items-start gap-2.5">
                        <Info className="w-4 h-4 shrink-0 text-cyan-400 mt-0.5" />
                        <div className="text-xs text-slate-300 leading-relaxed">
                          Patient is registered <strong className="text-white">without a mobile phone</strong>. Spatial location is fixed to their official administrative centroid based on their registered <strong className="text-cyan-300">District, Panchayath (Local Body), and Ward</strong>:
                        </div>
                      </div>

                      <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 pt-2 border-t border-cyan-500/20 text-xs">
                        <div className="bg-slate-950/80 p-2.5 rounded-lg border border-slate-800">
                          <span className="text-[10px] text-slate-400 uppercase font-mono block">1. District</span>
                          <span className="font-bold text-white text-xs">{selectedPatient.district_name || '—'}</span>
                        </div>
                        <div className="bg-slate-950/80 p-2.5 rounded-lg border border-slate-800">
                          <span className="text-[10px] text-slate-400 uppercase font-mono block">2. Panchayath / Local Body</span>
                          <span className="font-bold text-cyan-300 text-xs truncate block" title={selectedPatient.local_body_name}>
                            {selectedPatient.local_body_name || '—'}
                          </span>
                        </div>
                        <div className="bg-slate-950/80 p-2.5 rounded-lg border border-slate-800">
                          <span className="text-[10px] text-slate-400 uppercase font-mono block">3. Ward</span>
                          <span className="font-bold text-emerald-400 text-xs">
                            Ward #{selectedPatient.ward_number} {selectedPatient.ward_name ? `(${selectedPatient.ward_name})` : ''}
                          </span>
                        </div>
                      </div>
                    </div>

                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 font-mono text-[11px]">
                      <div className="p-2 rounded-lg bg-slate-950 border border-slate-800">
                        <span className="text-slate-500 block text-[9px] uppercase">Centroid Latitude</span>
                        <span className="text-cyan-400 font-semibold">{selectedPatient.latest_latitude ? selectedPatient.latest_latitude.toFixed(6) : '—'}</span>
                      </div>
                      <div className="p-2 rounded-lg bg-slate-950 border border-slate-800">
                        <span className="text-slate-500 block text-[9px] uppercase">Centroid Longitude</span>
                        <span className="text-cyan-400 font-semibold">{selectedPatient.latest_longitude ? selectedPatient.latest_longitude.toFixed(6) : '—'}</span>
                      </div>
                      <div className="p-2 rounded-lg bg-slate-950 border border-slate-800">
                        <span className="text-slate-500 block text-[9px] uppercase">Resolution Level</span>
                        <span className="text-white font-semibold">
                          {selectedPatient.ward_id ? 'Ward Centroid' : selectedPatient.local_body_id ? 'Panchayath Centroid' : 'District Centroid'}
                        </span>
                      </div>
                      <div className="p-2 rounded-lg bg-slate-950 border border-slate-800">
                        <span className="text-slate-500 block text-[9px] uppercase">Source</span>
                        <span className="text-cyan-400 font-semibold">{selectedPatient.latest_source || 'STATIC_ADMIN_LOCATION'}</span>
                      </div>
                    </div>
                  </div>
                ) : selectedPatient.latest_latitude && selectedPatient.latest_longitude ? (
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-1 font-mono text-[11px]">
                    <div className="p-2 rounded-lg bg-slate-950 border border-slate-800">
                      <span className="text-slate-500 block text-[9px] uppercase">Latitude</span>
                      <span className="text-emerald-400 font-semibold">{selectedPatient.latest_latitude.toFixed(6)}</span>
                    </div>
                    <div className="p-2 rounded-lg bg-slate-950 border border-slate-800">
                      <span className="text-slate-500 block text-[9px] uppercase">Longitude</span>
                      <span className="text-emerald-400 font-semibold">{selectedPatient.latest_longitude.toFixed(6)}</span>
                    </div>
                    <div className="p-2 rounded-lg bg-slate-950 border border-slate-800">
                      <span className="text-slate-500 block text-[9px] uppercase">Accuracy</span>
                      <span className="text-white font-semibold">±{selectedPatient.latest_accuracy || 5}m</span>
                    </div>
                    <div className="p-2 rounded-lg bg-slate-950 border border-slate-800">
                      <span className="text-slate-500 block text-[9px] uppercase">Source</span>
                      <span className="text-cyan-400 font-semibold">{selectedPatient.latest_source || 'PATIENT_GPS'}</span>
                    </div>
                  </div>
                ) : (
                  <div className="p-3 rounded-lg bg-slate-950 border border-slate-800/80 text-slate-500 italic text-[11px]">
                    No GPS telemetry observations recorded yet for this patient account. Monitoring session pending.
                  </div>
                )}
              </div>
            </div>

            <div className="flex justify-between items-center pt-2 border-t border-slate-800">
              <button
                onClick={() => {
                  const p = selectedPatient;
                  setSelectedPatient(null);
                  handleOpenEdit(p);
                }}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-cyan-400 text-xs font-semibold border border-slate-700 cursor-pointer"
              >
                <Edit2 className="w-3.5 h-3.5" />
                <span>Edit Record</span>
              </button>

              <button
                onClick={() => setSelectedPatient(null)}
                className="px-4 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold cursor-pointer"
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
