import React, { useState, useEffect } from 'react';
import {
  Users,
  Activity,
  CheckCircle2,
  HelpCircle,
  HeartHandshake,
  Radio,
  Route,
  Filter,
  RefreshCw,
  MapPin,
  Building,
  Info,
  TrendingUp,
  BarChart3,
  PieChart as PieChartIcon
} from 'lucide-react';
import { MapContainer, TileLayer, CircleMarker, Popup, Tooltip as LeafletTooltip, useMap } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Cell,
} from 'recharts';

import {
  SurveillanceDashboardResponse,
  SurveillanceFilterParams,
  DistrictGIS,
  LocalBodyGIS,
  WardGIS,
  DiseaseItem,
} from '../../types';
import {
  fetchSurveillanceDashboard,
  fetchDistricts,
  fetchLocalBodies,
  fetchWards,
  fetchDiseases,
} from '../../services/api';

type MapMode = 'cases' | 'districts';

// Helper controller to reposition the map when switching modes
const MapViewController: React.FC<{ mode: MapMode }> = ({ mode }) => {
  const map = useMap();
  useEffect(() => {
    if (mode === 'districts') {
      map.flyTo([10.35, 76.3], 7.5, { animate: true, duration: 0.7 });
    }
  }, [mode, map]);
  return null;
};

export const PublicHealthSurveillanceDashboard: React.FC = () => {
  // Main Surveillance State
  const [data, setData] = useState<SurveillanceDashboardResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Cascading Filter Hierarchy Options
  const [diseases, setDiseases] = useState<DiseaseItem[]>([]);
  const [districts, setDistricts] = useState<DistrictGIS[]>([]);
  const [localBodies, setLocalBodies] = useState<LocalBodyGIS[]>([]);
  const [wards, setWards] = useState<WardGIS[]>([]);

  // Filter Selection State
  const [selectedDisease, setSelectedDisease] = useState<string>('');
  const [selectedDistrict, setSelectedDistrict] = useState<string>('');
  const [selectedLocalBody, setSelectedLocalBody] = useState<string>('');
  const [selectedWard, setSelectedWard] = useState<string>('');
  const [startDate, setStartDate] = useState<string>('');
  const [endDate, setEndDate] = useState<string>('');
  const [caseStatus, setCaseStatus] = useState<string>('ALL');

  // Map Visualization Mode
  const [mapMode, setMapMode] = useState<MapMode>('cases');

  // Load Geographic Catalog & Diseases on mount
  useEffect(() => {
    const loadCatalogs = async () => {
      try {
        const [distList, disList] = await Promise.all([
          fetchDistricts(),
          fetchDiseases(),
        ]);
        setDistricts(distList);
        setDiseases(disList);
      } catch (err) {
        console.error('Failed to load geographic/disease catalogs:', err);
      }
    };
    loadCatalogs();
  }, []);

  // Cascade Local Bodies when District changes
  useEffect(() => {
    if (selectedDistrict) {
      fetchLocalBodies(selectedDistrict)
        .then(setLocalBodies)
        .catch(() => setLocalBodies([]));
    } else {
      setLocalBodies([]);
    }
    setSelectedLocalBody('');
    setSelectedWard('');
  }, [selectedDistrict]);

  // Cascade Wards when Local Body changes
  useEffect(() => {
    if (selectedLocalBody) {
      fetchWards(selectedLocalBody)
        .then(setWards)
        .catch(() => setWards([]));
    } else {
      setWards([]);
    }
    setSelectedWard('');
  }, [selectedLocalBody]);

  // Primary Data Fetcher
  const loadDashboard = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const filters: SurveillanceFilterParams = {
        disease_id: selectedDisease || undefined,
        district_id: selectedDistrict || undefined,
        local_body_id: selectedLocalBody || undefined,
        ward_id: selectedWard || undefined,
        start_date: startDate || undefined,
        end_date: endDate || undefined,
        case_status: caseStatus !== 'ALL' ? caseStatus : undefined,
      };
      const response = await fetchSurveillanceDashboard(filters);
      setData(response);
    } catch (err: any) {
      console.error('Error fetching surveillance dashboard:', err);
      setError(err?.response?.data?.detail || 'Failed to load surveillance dashboard statistics.');
    } finally {
      setIsLoading(false);
    }
  };

  // Re-fetch whenever filters change
  useEffect(() => {
    loadDashboard();
  }, [selectedDisease, selectedDistrict, selectedLocalBody, selectedWard, startDate, endDate, caseStatus]);

  // Reset Filters
  const handleResetFilters = () => {
    setSelectedDisease('');
    setSelectedDistrict('');
    setSelectedLocalBody('');
    setSelectedWard('');
    setStartDate('');
    setEndDate('');
    setCaseStatus('ALL');
  };

  // Status Badge Helper
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'CONFIRMED':
        return '#ef4444'; // Red
      case 'SUSPECTED':
        return '#f59e0b'; // Amber
      case 'RECOVERED':
        return '#10b981'; // Emerald
      case 'DECEASED':
        return '#a855f7'; // Purple
      default:
        return '#64748b'; // Slate
    }
  };

  // Predefined disease colors for chart
  const DISEASE_COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ec4899', '#8b5cf6', '#06b6d4'];
  const DISTRICT_COLORS = ['#6366f1', '#14b8a6', '#f97316', '#a855f7', '#0ea5e9'];

  const kpi = data?.kpi_summary;

  return (
    <div className="space-y-6">
      {/* Header Banner & Decision Support Notice */}
      <div className="glass-panel rounded-2xl p-6 relative overflow-hidden border border-slate-800">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <span className="px-2.5 py-0.5 rounded-full bg-brand-500/10 border border-brand-500/30 text-[11px] font-semibold text-brand-400 uppercase tracking-wider">
                Step 17: Central Surveillance
              </span>
              <span className="text-xs text-slate-500 font-mono">Real-Time Aggregation</span>
            </div>
            <h1 className="text-2xl font-heading font-extrabold text-white tracking-tight">
              Public Health Surveillance Dashboard
            </h1>
            <p className="text-xs text-slate-400 max-w-2xl leading-relaxed">
              Real-time high-level disease incidence tracking, spatial epidemiology, 15-minute telemetry monitoring,
              and PostGIS potential spatial-temporal exposure intersections across Kerala health jurisdictions.
            </p>
          </div>

          <div className="flex items-center gap-3 self-start md:self-auto shrink-0">
            <button
              onClick={loadDashboard}
              disabled={isLoading}
              className="flex items-center gap-2 px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 text-xs font-semibold transition-all shadow-sm"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin text-brand-400' : ''}`} />
              <span>Refresh Metrics</span>
            </button>
          </div>
        </div>

        {/* Ethical Decision Support Banner */}
        <div className="mt-4 pt-3 border-t border-slate-800/80 flex items-start gap-2.5 text-slate-400 text-xs">
          <Info className="w-4 h-4 text-brand-400 shrink-0 mt-0.5" />
          <p className="leading-normal">
            <span className="font-semibold text-slate-300">Epidemiological Decision Support:</span>{' '}
            All metrics, case densities, and exposure counts are derived dynamically from authorized health records and
            consented telemetry. Exposure events denote potential spatial-temporal overlap and do not assert clinical transmission.
          </p>
        </div>
      </div>

      {error && (
        <div className="p-4 bg-rose-500/10 border border-rose-500/30 text-rose-400 text-xs rounded-xl flex items-center gap-2">
          <Info className="w-4 h-4 text-rose-400 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* ========================================================= */}
      {/* 1. FILTER CONTROLS BAR */}
      {/* ========================================================= */}
      <div className="glass-panel rounded-2xl p-5 border border-slate-800 space-y-4">
        <div className="flex items-center justify-between pb-3 border-b border-slate-800/80">
          <div className="flex items-center gap-2">
            <Filter className="w-4 h-4 text-brand-400" />
            <h2 className="text-sm font-heading font-bold text-white uppercase tracking-wider">
              Surveillance Scope & Dynamic Filters
            </h2>
          </div>
          {(selectedDisease || selectedDistrict || selectedLocalBody || selectedWard || startDate || endDate || caseStatus !== 'ALL') && (
            <button
              onClick={handleResetFilters}
              className="text-xs font-semibold text-brand-400 hover:text-brand-300 underline underline-offset-4"
            >
              Reset All Filters
            </button>
          )}
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
          {/* Disease Filter */}
          <div>
            <label className="block text-[11px] font-semibold text-slate-400 mb-1">Disease</label>
            <select
              value={selectedDisease}
              onChange={(e) => setSelectedDisease(e.target.value)}
              className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-brand-500"
            >
              <option value="">All Diseases (Statewide)</option>
              {diseases.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.name} ({d.code})
                </option>
              ))}
            </select>
          </div>

          {/* District Filter */}
          <div>
            <label className="block text-[11px] font-semibold text-slate-400 mb-1">District</label>
            <select
              value={selectedDistrict}
              onChange={(e) => setSelectedDistrict(e.target.value)}
              className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-brand-500"
            >
              <option value="">All Districts</option>
              {districts.map((dist) => (
                <option key={dist.id} value={dist.id}>
                  {dist.name}
                </option>
              ))}
            </select>
          </div>

          {/* Local Body Filter */}
          <div>
            <label className="block text-[11px] font-semibold text-slate-400 mb-1">Local Body</label>
            <select
              value={selectedLocalBody}
              onChange={(e) => setSelectedLocalBody(e.target.value)}
              disabled={!selectedDistrict}
              className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-brand-500 disabled:opacity-50"
            >
              <option value="">All Local Bodies</option>
              {localBodies.map((lb) => (
                <option key={lb.id} value={lb.id}>
                  {lb.name} ({lb.body_type})
                </option>
              ))}
            </select>
          </div>

          {/* Ward Filter */}
          <div>
            <label className="block text-[11px] font-semibold text-slate-400 mb-1">Ward</label>
            <select
              value={selectedWard}
              onChange={(e) => setSelectedWard(e.target.value)}
              disabled={!selectedLocalBody}
              className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-brand-500 disabled:opacity-50"
            >
              <option value="">All Wards</option>
              {wards.map((w) => (
                <option key={w.id} value={w.id}>
                  Ward {w.ward_number} - {w.name}
                </option>
              ))}
            </select>
          </div>

          {/* Case Status Filter */}
          <div>
            <label className="block text-[11px] font-semibold text-slate-400 mb-1">Case Status</label>
            <select
              value={caseStatus}
              onChange={(e) => setCaseStatus(e.target.value)}
              className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-brand-500"
            >
              <option value="ALL">All Statuses</option>
              <option value="CONFIRMED">Confirmed Only</option>
              <option value="SUSPECTED">Suspected Only</option>
              <option value="RECOVERED">Recovered Only</option>
              <option value="DECEASED">Deceased Only</option>
            </select>
          </div>

          {/* Date Range Start/End Filter */}
          <div>
            <label className="block text-[11px] font-semibold text-slate-400 mb-1">Diagnosis Date</label>
            <div className="flex items-center gap-1.5">
              <input
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                placeholder="From"
                className="w-1/2 bg-slate-950 border border-slate-800 rounded-lg px-2 py-1.5 text-[11px] text-slate-200 focus:outline-none focus:border-brand-500"
              />
              <span className="text-slate-500 text-xs">→</span>
              <input
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                placeholder="To"
                className="w-1/2 bg-slate-950 border border-slate-800 rounded-lg px-2 py-1.5 text-[11px] text-slate-200 focus:outline-none focus:border-brand-500"
              />
            </div>
          </div>
        </div>
      </div>

      {/* ========================================================= */}
      {/* 2. KPI CARDS (7 Required KPI Metrics) */}
      {/* ========================================================= */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-7 gap-3">
        {/* KPI 1: Total Patients */}
        <div className="glass-panel rounded-xl p-4 border border-slate-800/90 relative overflow-hidden flex flex-col justify-between">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-[11px] font-semibold uppercase tracking-wider">Total Patients</span>
            <div className="p-1.5 rounded-lg bg-blue-500/10 text-blue-400">
              <Users className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3">
            <span className="text-2xl font-extrabold text-white font-mono">
              {isLoading ? '...' : kpi?.total_patients ?? 0}
            </span>
            <span className="block text-[10px] text-slate-500 mt-0.5">Registered Health Registry</span>
          </div>
        </div>

        {/* KPI 2: Active Cases */}
        <div className="glass-panel rounded-xl p-4 border border-amber-500/20 bg-amber-500/5 relative overflow-hidden flex flex-col justify-between">
          <div className="flex items-center justify-between text-amber-400">
            <span className="text-[11px] font-semibold uppercase tracking-wider">Active Cases</span>
            <div className="p-1.5 rounded-lg bg-amber-500/10 text-amber-400">
              <Activity className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3">
            <span className="text-2xl font-extrabold text-amber-400 font-mono">
              {isLoading ? '...' : kpi?.active_cases ?? 0}
            </span>
            <span className="block text-[10px] text-amber-400/70 mt-0.5">Confirmed + Suspected</span>
          </div>
        </div>

        {/* KPI 3: Confirmed Cases */}
        <div className="glass-panel rounded-xl p-4 border border-rose-500/20 bg-rose-500/5 relative overflow-hidden flex flex-col justify-between">
          <div className="flex items-center justify-between text-rose-400">
            <span className="text-[11px] font-semibold uppercase tracking-wider">Confirmed</span>
            <div className="p-1.5 rounded-lg bg-rose-500/10 text-rose-400">
              <CheckCircle2 className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3">
            <span className="text-2xl font-extrabold text-rose-400 font-mono">
              {isLoading ? '...' : kpi?.confirmed_cases ?? 0}
            </span>
            <span className="block text-[10px] text-rose-400/70 mt-0.5">Lab/Clinical Confirmed</span>
          </div>
        </div>

        {/* KPI 4: Suspected Cases */}
        <div className="glass-panel rounded-xl p-4 border border-slate-800/90 relative overflow-hidden flex flex-col justify-between">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-[11px] font-semibold uppercase tracking-wider">Suspected</span>
            <div className="p-1.5 rounded-lg bg-yellow-500/10 text-yellow-400">
              <HelpCircle className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3">
            <span className="text-2xl font-extrabold text-yellow-400 font-mono">
              {isLoading ? '...' : kpi?.suspected_cases ?? 0}
            </span>
            <span className="block text-[10px] text-slate-500 mt-0.5">Under Field Investigation</span>
          </div>
        </div>

        {/* KPI 5: Recovered Cases */}
        <div className="glass-panel rounded-xl p-4 border border-emerald-500/20 bg-emerald-500/5 relative overflow-hidden flex flex-col justify-between">
          <div className="flex items-center justify-between text-emerald-400">
            <span className="text-[11px] font-semibold uppercase tracking-wider">Recovered</span>
            <div className="p-1.5 rounded-lg bg-emerald-500/10 text-emerald-400">
              <HeartHandshake className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3">
            <span className="text-2xl font-extrabold text-emerald-400 font-mono">
              {isLoading ? '...' : kpi?.recovered_cases ?? 0}
            </span>
            <span className="block text-[10px] text-emerald-400/70 mt-0.5">Full Clinical Recovery</span>
          </div>
        </div>

        {/* KPI 6: Active Monitoring Sessions */}
        <div className="glass-panel rounded-xl p-4 border border-purple-500/20 bg-purple-500/5 relative overflow-hidden flex flex-col justify-between">
          <div className="flex items-center justify-between text-purple-400">
            <span className="text-[11px] font-semibold uppercase tracking-wider">Monitoring</span>
            <div className="p-1.5 rounded-lg bg-purple-500/10 text-purple-400">
              <Radio className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3">
            <span className="text-2xl font-extrabold text-purple-400 font-mono">
              {isLoading ? '...' : kpi?.active_monitoring_sessions ?? 0}
            </span>
            <span className="block text-[10px] text-purple-400/70 mt-0.5">~15-Min Telemetry Active</span>
          </div>
        </div>

        {/* KPI 7: Potential Exposure Events */}
        <div className="glass-panel rounded-xl p-4 border border-orange-500/20 bg-orange-500/5 relative overflow-hidden flex flex-col justify-between col-span-2 sm:col-span-1">
          <div className="flex items-center justify-between text-orange-400">
            <span className="text-[11px] font-semibold uppercase tracking-wider">Potential Exposure</span>
            <div className="p-1.5 rounded-lg bg-orange-500/10 text-orange-400">
              <Route className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3">
            <span className="text-2xl font-extrabold text-orange-400 font-mono">
              {isLoading ? '...' : kpi?.potential_exposure_events ?? 0}
            </span>
            <span className="block text-[10px] text-orange-400/70 mt-0.5">Spatial-Temporal Overlaps</span>
          </div>
        </div>
      </div>

      {/* ========================================================= */}
      {/* 3. CHARTS ROW 1: CASES OVER TIME (RECHARTS) */}
      {/* ========================================================= */}
      <div className="glass-panel rounded-2xl p-6 border border-slate-800">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 mb-4 border-b border-slate-800/80 gap-2">
          <div>
            <div className="flex items-center gap-2">
              <TrendingUp className="w-4 h-4 text-brand-400" />
              <h3 className="text-base font-heading font-bold text-white">
                Epidemic Trajectory: Cases Over Time
              </h3>
            </div>
            <p className="text-xs text-slate-400 mt-0.5">
              Daily incidence trend classified by confirmed, suspected, and recovered clinical statuses.
            </p>
          </div>
          <div className="flex items-center gap-4 text-xs font-mono text-slate-400">
            <div className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-rose-500"></span>
              <span>Confirmed</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-amber-500"></span>
              <span>Suspected</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-500"></span>
              <span>Recovered</span>
            </div>
          </div>
        </div>

        <div className="h-72 w-full">
          {isLoading ? (
            <div className="h-full flex items-center justify-center text-slate-500 text-xs">
              <RefreshCw className="w-5 h-5 animate-spin mr-2" /> Loading incidence time-series...
            </div>
          ) : !data?.charts?.cases_over_time?.length ? (
            <div className="h-full flex items-center justify-center text-slate-500 text-xs">
              No incidence observations match selected filter bounds.
            </div>
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart
                data={data.charts.cases_over_time}
                margin={{ top: 10, right: 20, left: -10, bottom: 0 }}
              >
                <defs>
                  <linearGradient id="colorConfirmed" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#ef4444" stopOpacity={0.4} />
                    <stop offset="95%" stopColor="#ef4444" stopOpacity={0.0} />
                  </linearGradient>
                  <linearGradient id="colorSuspected" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#f59e0b" stopOpacity={0.4} />
                    <stop offset="95%" stopColor="#f59e0b" stopOpacity={0.0} />
                  </linearGradient>
                  <linearGradient id="colorRecovered" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#10b981" stopOpacity={0.4} />
                    <stop offset="95%" stopColor="#10b981" stopOpacity={0.0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="date" stroke="#64748b" tick={{ fill: '#94a3b8', fontSize: 11 }} />
                <YAxis stroke="#64748b" tick={{ fill: '#94a3b8', fontSize: 11 }} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#0f172a',
                    borderColor: '#334155',
                    borderRadius: '0.75rem',
                    color: '#f8fafc',
                    fontSize: '12px',
                  }}
                />
                <Area
                  type="monotone"
                  dataKey="confirmed"
                  stroke="#ef4444"
                  strokeWidth={2}
                  fillOpacity={1}
                  fill="url(#colorConfirmed)"
                  name="Confirmed"
                />
                <Area
                  type="monotone"
                  dataKey="suspected"
                  stroke="#f59e0b"
                  strokeWidth={2}
                  fillOpacity={1}
                  fill="url(#colorSuspected)"
                  name="Suspected"
                />
                <Area
                  type="monotone"
                  dataKey="recovered"
                  stroke="#10b981"
                  strokeWidth={2}
                  fillOpacity={1}
                  fill="url(#colorRecovered)"
                  name="Recovered"
                />
              </AreaChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>

      {/* ========================================================= */}
      {/* 4. CHARTS ROW 2: CATEGORICAL BREAKDOWNS (RECHARTS) */}
      {/* ========================================================= */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Chart 2: Cases by Disease */}
        <div className="glass-panel rounded-2xl p-6 border border-slate-800">
          <div className="flex items-center justify-between pb-3 mb-4 border-b border-slate-800/80">
            <div className="flex items-center gap-2">
              <PieChartIcon className="w-4 h-4 text-emerald-400" />
              <h3 className="text-sm font-heading font-bold text-white">
                Cases by Disease Strain
              </h3>
            </div>
            <span className="text-xs text-slate-500 font-mono">Catalog Distribution</span>
          </div>

          <div className="h-64 w-full">
            {isLoading ? (
              <div className="h-full flex items-center justify-center text-slate-500 text-xs">
                Loading disease distribution...
              </div>
            ) : !data?.charts?.cases_by_disease?.length ? (
              <div className="h-full flex items-center justify-center text-slate-500 text-xs">
                No disease records found.
              </div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  data={data.charts.cases_by_disease}
                  layout="vertical"
                  margin={{ top: 5, right: 30, left: 40, bottom: 5 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                  <XAxis type="number" stroke="#64748b" tick={{ fill: '#94a3b8', fontSize: 11 }} />
                  <YAxis
                    dataKey="disease_code"
                    type="category"
                    stroke="#64748b"
                    tick={{ fill: '#94a3b8', fontSize: 11 }}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#0f172a',
                      borderColor: '#334155',
                      borderRadius: '0.75rem',
                      color: '#f8fafc',
                      fontSize: '12px',
                    }}
                    formatter={(val: any, _: any, item: any) => [
                      `${val} cases (${item.payload.percentage}%) - ${item.payload.disease_name}`,
                      'Incidence',
                    ]}
                  />
                  <Bar dataKey="count" radius={[0, 4, 4, 0]}>
                    {data.charts.cases_by_disease.map((_, index) => (
                      <Cell
                        key={`cell-disease-${index}`}
                        fill={DISEASE_COLORS[index % DISEASE_COLORS.length]}
                      />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>

        {/* Chart 3: Cases by District */}
        <div className="glass-panel rounded-2xl p-6 border border-slate-800">
          <div className="flex items-center justify-between pb-3 mb-4 border-b border-slate-800/80">
            <div className="flex items-center gap-2">
              <MapPin className="w-4 h-4 text-cyan-400" />
              <h3 className="text-sm font-heading font-bold text-white">
                Cases by Administrative District
              </h3>
            </div>
            <span className="text-xs text-slate-500 font-mono">Geographic Hierarchy</span>
          </div>

          <div className="h-64 w-full">
            {isLoading ? (
              <div className="h-full flex items-center justify-center text-slate-500 text-xs">
                Loading district distribution...
              </div>
            ) : !data?.charts?.cases_by_district?.length ? (
              <div className="h-full flex items-center justify-center text-slate-500 text-xs">
                No district records found.
              </div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  data={data.charts.cases_by_district}
                  margin={{ top: 5, right: 20, left: -10, bottom: 5 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                  <XAxis
                    dataKey="district_name"
                    stroke="#64748b"
                    tick={{ fill: '#94a3b8', fontSize: 11 }}
                  />
                  <YAxis stroke="#64748b" tick={{ fill: '#94a3b8', fontSize: 11 }} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#0f172a',
                      borderColor: '#334155',
                      borderRadius: '0.75rem',
                      color: '#f8fafc',
                      fontSize: '12px',
                    }}
                    formatter={(val: any, _: any, item: any) => [
                      `${val} cases (${item.payload.percentage}%)`,
                      'Cases',
                    ]}
                  />
                  <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                    {data.charts.cases_by_district.map((_, index) => (
                      <Cell
                        key={`cell-district-${index}`}
                        fill={DISTRICT_COLORS[index % DISTRICT_COLORS.length]}
                      />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>
      </div>

      {/* ========================================================= */}
      {/* 5. CHARTS ROW 3: LOCAL BODY & WARD (RECHARTS) */}
      {/* ========================================================= */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Chart 4: Cases by Local Body */}
        <div className="glass-panel rounded-2xl p-6 border border-slate-800">
          <div className="flex items-center justify-between pb-3 mb-4 border-b border-slate-800/80">
            <div className="flex items-center gap-2">
              <Building className="w-4 h-4 text-purple-400" />
              <h3 className="text-sm font-heading font-bold text-white">
                Cases by Local Body (Corporations / Municipalities)
              </h3>
            </div>
            <span className="text-xs text-slate-500 font-mono">Tier 2 Local Governance</span>
          </div>

          <div className="h-64 w-full">
            {isLoading ? (
              <div className="h-full flex items-center justify-center text-slate-500 text-xs">
                Loading local body distribution...
              </div>
            ) : !data?.charts?.cases_by_local_body?.length ? (
              <div className="h-full flex items-center justify-center text-slate-500 text-xs">
                No local body data matching active filters.
              </div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  data={data.charts.cases_by_local_body}
                  margin={{ top: 5, right: 20, left: -10, bottom: 25 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                  <XAxis
                    dataKey="local_body_name"
                    stroke="#64748b"
                    angle={-20}
                    textAnchor="end"
                    interval={0}
                    tick={{ fill: '#94a3b8', fontSize: 10 }}
                  />
                  <YAxis stroke="#64748b" tick={{ fill: '#94a3b8', fontSize: 11 }} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#0f172a',
                      borderColor: '#334155',
                      borderRadius: '0.75rem',
                      color: '#f8fafc',
                      fontSize: '12px',
                    }}
                    formatter={(val: any, _: any, item: any) => [
                      `${val} cases (${item.payload.percentage}%) - ${item.payload.district_name}`,
                      'Cases',
                    ]}
                  />
                  <Bar dataKey="count" fill="#8b5cf6" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>

        {/* Chart 5: Cases by Ward */}
        <div className="glass-panel rounded-2xl p-6 border border-slate-800">
          <div className="flex items-center justify-between pb-3 mb-4 border-b border-slate-800/80">
            <div className="flex items-center gap-2">
              <BarChart3 className="w-4 h-4 text-amber-400" />
              <h3 className="text-sm font-heading font-bold text-white">
                Cases by Ward (Top Epidemiological Units)
              </h3>
            </div>
            <span className="text-xs text-slate-500 font-mono">Micro-Level Surveillance</span>
          </div>

          <div className="h-64 w-full">
            {isLoading ? (
              <div className="h-full flex items-center justify-center text-slate-500 text-xs">
                Loading ward distribution...
              </div>
            ) : !data?.charts?.cases_by_ward?.length ? (
              <div className="h-full flex items-center justify-center text-slate-500 text-xs">
                No ward data matching active filters.
              </div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  data={data.charts.cases_by_ward.slice(0, 8)}
                  margin={{ top: 5, right: 20, left: -10, bottom: 25 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                  <XAxis
                    dataKey="ward_name"
                    stroke="#64748b"
                    angle={-20}
                    textAnchor="end"
                    interval={0}
                    tick={{ fill: '#94a3b8', fontSize: 10 }}
                  />
                  <YAxis stroke="#64748b" tick={{ fill: '#94a3b8', fontSize: 11 }} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#0f172a',
                      borderColor: '#334155',
                      borderRadius: '0.75rem',
                      color: '#f8fafc',
                      fontSize: '12px',
                    }}
                    formatter={(val: any, _: any, item: any) => [
                      `${val} cases (${item.payload.percentage}%) - ${item.payload.local_body_name}`,
                      'Cases',
                    ]}
                  />
                  <Bar dataKey="count" fill="#f59e0b" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>
      </div>

      {/* ========================================================= */}
      {/* 6. INTEGRATED SURVEILLANCE MAP (CASE MAP / HEATMAP / DISTRICT) */}
      {/* ========================================================= */}
      <div className="glass-panel rounded-2xl p-6 border border-slate-800 space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-3 border-b border-slate-800/80 gap-3">
          <div>
            <div className="flex items-center gap-2">
              <MapPin className="w-5 h-5 text-brand-400" />
              <h3 className="text-base font-heading font-bold text-white">
                Spatial Surveillance & District Distribution
              </h3>
            </div>
            <p className="text-xs text-slate-400 mt-0.5">
              Dual-mode spatial telemetry: Disease case markers and district-level epidemiological distribution.
            </p>
          </div>

          {/* Map Layer Mode Switcher */}
          <div className="flex items-center bg-slate-950 p-1 rounded-xl border border-slate-800 self-start sm:self-auto">
            <button
              onClick={() => setMapMode('cases')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors ${
                mapMode === 'cases'
                  ? 'bg-brand-600 text-white shadow-sm'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <MapPin className="w-3.5 h-3.5" />
              <span>Disease Case Map</span>
            </button>

            <button
              onClick={() => setMapMode('districts')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors ${
                mapMode === 'districts'
                  ? 'bg-brand-600 text-white shadow-sm'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <Building className="w-3.5 h-3.5" />
              <span>District Visualization</span>
            </button>
          </div>
        </div>

        {/* Map Container */}
        <div className="relative h-96 w-full rounded-xl overflow-hidden border border-slate-800 bg-slate-950">
          <MapContainer
            center={[10.35, 76.3]}
            zoom={7.5}
            style={{ height: '100%', width: '100%' }}
            className="z-0"
          >
            <MapViewController mode={mapMode} />

            <TileLayer
              className="map-tiles-dark"
              attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            />

            {/* Mode 1: Discrete Disease Case Markers */}
            {mapMode === 'cases' &&
              data?.map_data?.disease_cases?.map((c) => (
                <CircleMarker
                  key={`case-marker-${c.id}`}
                  center={[c.latitude, c.longitude]}
                  radius={7}
                  pathOptions={{
                    fillColor: getStatusColor(c.case_status),
                    fillOpacity: 0.85,
                    color: '#ffffff',
                    weight: 1.5,
                  }}
                >
                  <Popup className="custom-leaflet-popup">
                    <div className="p-1 space-y-1 text-slate-900 text-xs">
                      <div className="font-bold border-b pb-1 text-slate-800">
                        {c.disease_name}
                      </div>
                      <div className="text-[11px]">
                        <strong>Status:</strong>{' '}
                        <span
                          style={{ color: getStatusColor(c.case_status) }}
                          className="font-semibold"
                        >
                          {c.case_status}
                        </span>
                      </div>
                      <div className="text-[11px]">
                        <strong>Location:</strong> {c.ward_name}, {c.district_name}
                      </div>
                      <div className="text-[11px]">
                        <strong>Diagnosed:</strong> {c.diagnosis_date}
                      </div>
                      <div className="text-[10px] text-slate-500 font-mono">
                        Patient ID: {c.patient_pseudo_id}
                      </div>
                    </div>
                  </Popup>
                </CircleMarker>
              ))}

            {/* Mode 2: District Aggregation Visualization with Clear Labels */}
            {mapMode === 'districts' &&
              data?.map_data?.districts?.map((d) => {
                const hasCases = d.case_count > 0;
                return (
                  <CircleMarker
                    key={`district-marker-${d.id}`}
                    center={[d.latitude, d.longitude]}
                    radius={hasCases ? Math.max(14, Math.min(30, 14 + d.case_count * 3)) : 8}
                    pathOptions={{
                      fillColor: hasCases ? '#f43f5e' : '#6366f1',
                      fillOpacity: hasCases ? 0.9 : 0.45,
                      color: hasCases ? '#ffffff' : '#a5b4fc',
                      weight: hasCases ? 2.5 : 1.5,
                    }}
                  >
                    <LeafletTooltip
                      permanent
                      direction="top"
                      offset={[0, hasCases ? -12 : -8]}
                      className="district-label-tooltip"
                    >
                      <div
                        className={`flex items-center gap-1.5 px-2.5 py-0.5 rounded-md border shadow-lg backdrop-blur-md pointer-events-none whitespace-nowrap transition-all ${
                          hasCases
                            ? 'bg-slate-950/95 border-rose-500/80 text-white shadow-rose-950/60 ring-1 ring-rose-500/40'
                            : 'bg-slate-950/90 border-slate-700/80 text-slate-200'
                        }`}
                      >
                        <span className="font-semibold text-xs tracking-wide">{d.name}</span>
                        <span
                          className={`px-1.5 py-0.2 rounded text-[10px] font-bold ${
                            hasCases
                              ? 'bg-rose-500 text-white shadow-sm'
                              : 'bg-slate-800 text-slate-400'
                          }`}
                        >
                          {d.case_count}
                        </span>
                      </div>
                    </LeafletTooltip>

                    <Popup className="custom-leaflet-popup">
                      <div className="p-1 space-y-1.5 text-slate-900 text-xs min-w-[170px]">
                        <div className="font-bold border-b pb-1 text-slate-900 text-sm flex items-center justify-between">
                          <span>{d.name} District</span>
                          <span
                            className={`text-[10px] px-1.5 py-0.2 rounded font-bold ${
                              hasCases
                                ? 'bg-rose-100 text-rose-700'
                                : 'bg-emerald-100 text-emerald-700'
                            }`}
                          >
                            {hasCases ? 'Active Outbreak' : 'Zero Cases'}
                          </span>
                        </div>
                        <div className="text-[11px] flex justify-between">
                          <strong className="text-slate-700">Total Cases:</strong>
                          <span className="font-bold text-slate-900">{d.case_count}</span>
                        </div>
                        <div className="text-[11px] flex justify-between">
                          <strong className="text-slate-700">Active Under Surveillance:</strong>
                          <span className="font-bold text-rose-600">{d.active_count}</span>
                        </div>
                        <div className="text-[10px] text-slate-500 pt-1 border-t flex justify-between">
                          <span>Coordinates:</span>
                          <span>
                            {d.latitude.toFixed(3)}° N, {d.longitude.toFixed(3)}° E
                          </span>
                        </div>
                      </div>
                    </Popup>
                  </CircleMarker>
                );
              })}
          </MapContainer>

          {/* Map Legend Overlay */}
          <div className="absolute bottom-3 right-3 z-[400] bg-slate-950/90 border border-slate-800/90 p-3 rounded-xl backdrop-blur text-xs space-y-2 shadow-xl">
            <span className="block font-semibold text-slate-300 text-[11px] uppercase tracking-wider">
              {mapMode === 'cases' ? 'Case Status' : 'District Surveillance'}
            </span>

            {mapMode === 'cases' && (
              <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-[11px]">
                <div className="flex items-center gap-1.5">
                  <span className="w-2.5 h-2.5 rounded-full bg-rose-500"></span>
                  <span className="text-slate-300">Confirmed</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="w-2.5 h-2.5 rounded-full bg-amber-500"></span>
                  <span className="text-slate-300">Suspected</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="w-2.5 h-2.5 rounded-full bg-emerald-500"></span>
                  <span className="text-slate-300">Recovered</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="w-2.5 h-2.5 rounded-full bg-purple-500"></span>
                  <span className="text-slate-300">Deceased</span>
                </div>
              </div>
            )}

            {mapMode === 'districts' && (
              <div className="space-y-1.5 text-[11px]">
                <div className="flex items-center gap-2">
                  <span className="w-3 h-3 rounded-full bg-rose-500 border border-white"></span>
                  <span className="text-slate-200 font-medium">Active Caseload (≥ 1)</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="w-2.5 h-2.5 rounded-full bg-indigo-500/50 border border-indigo-300"></span>
                  <span className="text-slate-400">Zero Reported Cases (0)</span>
                </div>
                <p className="text-[10px] text-slate-500 pt-1 border-t border-slate-800">
                  All 14 Kerala districts labelled with total confirmed caseload.
                </p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
