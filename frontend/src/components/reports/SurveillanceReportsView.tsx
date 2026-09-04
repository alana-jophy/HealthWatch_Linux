import React, { useState, useEffect } from 'react';
import {
  FileText,
  Download,
  Filter,
  RefreshCw,
  Table as TableIcon,
  Shield,
  Info,
  Calendar,
  Layers,
  FileSpreadsheet,
  CheckCircle2,
  AlertTriangle,
  Building,
  MapPin,
  Flame,
  Route,
  Radio,
  Clock
} from 'lucide-react';

import {
  ReportType,
  ReportFormat,
  ReportPreviewResponse,
  ReportFilterParams,
  DistrictGIS,
  LocalBodyGIS,
  WardGIS,
  DiseaseItem,
} from '../../types';
import {
  fetchReportPreview,
  downloadReportFile,
  fetchDistricts,
  fetchLocalBodies,
  fetchWards,
  fetchDiseases,
} from '../../services/api';

interface ReportTypeOption {
  id: ReportType;
  label: string;
  description: string;
  icon: React.ElementType;
  badge: string;
}

const REPORT_TYPES: ReportTypeOption[] = [
  {
    id: 'comprehensive',
    label: 'Comprehensive Dossier',
    description: 'Consolidated statewide summary across all epidemiological surveillance domains',
    icon: Layers,
    badge: 'Master',
  },
  {
    id: 'disease_statistics',
    label: 'Disease Statistics',
    description: 'Pathogen catalog case counts, contagion classifications, and mortality rates',
    icon: FileText,
    badge: 'Catalog',
  },
  {
    id: 'district_cases',
    label: 'District-wise Cases',
    description: 'Caseload proportions, active surveillance counts across Kerala administrative districts',
    icon: MapPin,
    badge: 'Tier 1',
  },
  {
    id: 'local_body_cases',
    label: 'Local-Body Cases',
    description: 'Municipal corporations and municipalities epidemiological incident breakdown',
    icon: Building,
    badge: 'Tier 2',
  },
  {
    id: 'ward_cases',
    label: 'Ward-wise Cases',
    description: 'Micro-surveillance ward caseloads and outbreak concentration tier assignments',
    icon: TableIcon,
    badge: 'Micro',
  },
  {
    id: 'date_range_cases',
    label: 'Date-Range Cases',
    description: 'Anonymized case incident line listing with diagnosis timestamps and severity levels',
    icon: Calendar,
    badge: 'Line List',
  },
  {
    id: 'hotspot_summary',
    label: 'Hotspot Summary',
    description: 'High-risk clusters, active infection zones, and dominant pathogen tracking',
    icon: Flame,
    badge: 'Risk Tiers',
  },
  {
    id: 'potential_exposures',
    label: 'Potential Exposures',
    description: 'Spatial-temporal intersections between discrete observations (non-causal)',
    icon: Route,
    badge: 'Overlap',
  },
  {
    id: 'monitoring_summary',
    label: 'Monitoring Summary',
    description: 'Authorized quarantine monitoring telemetry sessions with ~15-min intervals',
    icon: Radio,
    badge: 'Telemetry',
  },
];

export const SurveillanceReportsView: React.FC = () => {
  const [selectedType, setSelectedType] = useState<ReportType>('comprehensive');
  const [preview, setPreview] = useState<ReportPreviewResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isExporting, setIsExporting] = useState<ReportFormat | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Cascading Filter Hierarchy Options
  const [diseases, setDiseases] = useState<DiseaseItem[]>([]);
  const [districts, setDistricts] = useState<DistrictGIS[]>([]);
  const [localBodies, setLocalBodies] = useState<LocalBodyGIS[]>([]);
  const [wards, setWards] = useState<WardGIS[]>([]);

  // Filter Values
  const [selectedDisease, setSelectedDisease] = useState<string>('');
  const [selectedDistrict, setSelectedDistrict] = useState<string>('');
  const [selectedLocalBody, setSelectedLocalBody] = useState<string>('');
  const [selectedWard, setSelectedWard] = useState<string>('');
  const [startDate, setStartDate] = useState<string>('');
  const [endDate, setEndDate] = useState<string>('');
  const [caseStatus, setCaseStatus] = useState<string>('ALL');

  // Load Geographic Catalogs
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

  // Cascade Local Bodies
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

  // Cascade Wards
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

  // Fetch Report Preview
  const loadPreview = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const filters: ReportFilterParams = {
        report_type: selectedType,
        disease_id: selectedDisease || undefined,
        district_id: selectedDistrict || undefined,
        local_body_id: selectedLocalBody || undefined,
        ward_id: selectedWard || undefined,
        start_date: startDate || undefined,
        end_date: endDate || undefined,
        case_status: caseStatus !== 'ALL' ? caseStatus : undefined,
      };
      const res = await fetchReportPreview(filters);
      setPreview(res);
    } catch (err: any) {
      console.error('Error fetching report preview:', err);
      setError(err?.response?.data?.detail || 'Failed to load report preview.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadPreview();
  }, [selectedType, selectedDisease, selectedDistrict, selectedLocalBody, selectedWard, startDate, endDate, caseStatus]);

  // Direct File Export (Browser Download)
  const handleExport = async (format: ReportFormat) => {
    setIsExporting(format);
    try {
      const filters: ReportFilterParams = {
        report_type: selectedType,
        format,
        disease_id: selectedDisease || undefined,
        district_id: selectedDistrict || undefined,
        local_body_id: selectedLocalBody || undefined,
        ward_id: selectedWard || undefined,
        start_date: startDate || undefined,
        end_date: endDate || undefined,
        case_status: caseStatus !== 'ALL' ? caseStatus : undefined,
      };

      const { blob, filename } = await downloadReportFile(filters);

      // Trigger standard browser download
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch (err: any) {
      console.error(`Export failed for format ${format}:`, err);
      setError(`Failed to export ${format.toUpperCase()} report.`);
    } finally {
      setIsExporting(null);
    }
  };

  const handleResetFilters = () => {
    setSelectedDisease('');
    setSelectedDistrict('');
    setSelectedLocalBody('');
    setSelectedWard('');
    setStartDate('');
    setEndDate('');
    setCaseStatus('ALL');
  };

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="glass-panel rounded-2xl p-6 relative overflow-hidden border border-slate-800">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <span className="px-2.5 py-0.5 rounded-full bg-brand-500/10 border border-brand-500/30 text-[11px] font-semibold text-brand-400 uppercase tracking-wider">
                Step 18: Official Reporting
              </span>
              <span className="text-xs text-slate-500 font-mono">PDF &bull; CSV &bull; JSON</span>
            </div>
            <h1 className="text-2xl font-heading font-extrabold text-white tracking-tight">
              Surveillance Reports & Epidemiological Export Engine
            </h1>
            <p className="text-xs text-slate-400 max-w-2xl leading-relaxed">
              Compile, preview, and generate official surveillance digests for public health authorities.
              Full support for disease statistics, jurisdictional aggregates, date-range line listings, outbreak hotspots, and telemetry audits.
            </p>
          </div>

          <div className="flex items-center gap-2 self-start md:self-auto shrink-0">
            {/* Download PDF Button */}
            <button
              onClick={() => handleExport('pdf')}
              disabled={isExporting !== null}
              className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-rose-600 hover:bg-rose-500 text-white text-xs font-semibold shadow-lg shadow-rose-950/40 transition-all disabled:opacity-50"
            >
              <Download className={`w-3.5 h-3.5 ${isExporting === 'pdf' ? 'animate-bounce' : ''}`} />
              <span>{isExporting === 'pdf' ? 'Compiling PDF...' : 'Download PDF Report'}</span>
            </button>

            {/* Download CSV Button */}
            <button
              onClick={() => handleExport('csv')}
              disabled={isExporting !== null}
              className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold shadow-lg shadow-emerald-950/40 transition-all disabled:opacity-50"
            >
              <FileSpreadsheet className={`w-3.5 h-3.5 ${isExporting === 'csv' ? 'animate-bounce' : ''}`} />
              <span>{isExporting === 'csv' ? 'Streaming CSV...' : 'Download CSV Export'}</span>
            </button>
          </div>
        </div>

        {/* Privacy & Ethical Notice */}
        <div className="mt-4 pt-3 border-t border-slate-800/80 flex items-start gap-2.5 text-slate-400 text-xs">
          <Shield className="w-4 h-4 text-brand-400 shrink-0 mt-0.5" />
          <p className="leading-normal">
            <span className="font-semibold text-slate-300">Privacy Safeguards & Anonymization:</span>{' '}
            Reports strictly protect patient confidentiality. Records use anonymized synthetic IDs (<code>pseudo_id</code>)
            and omit private phone numbers, street addresses, or raw private telemetry. Potential exposures are non-causal overlaps.
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
      {/* 1. REPORT TYPE SELECTOR (9 MODULE OPTIONS) */}
      {/* ========================================================= */}
      <div className="glass-panel rounded-2xl p-5 border border-slate-800 space-y-3">
        <div className="flex items-center justify-between pb-2 border-b border-slate-800/80">
          <div className="flex items-center gap-2">
            <Layers className="w-4 h-4 text-brand-400" />
            <h2 className="text-sm font-heading font-bold text-white uppercase tracking-wider">
              Select Surveillance Report Module
            </h2>
          </div>
          <span className="text-xs text-slate-500 font-mono">8 Core Modules + Master Dossier</span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-2.5">
          {REPORT_TYPES.map((opt) => {
            const Icon = opt.icon;
            const isSelected = selectedType === opt.id;
            return (
              <button
                key={opt.id}
                onClick={() => setSelectedType(opt.id)}
                className={`p-3 rounded-xl border text-left transition-all flex flex-col justify-between ${
                  isSelected
                    ? 'bg-brand-500/10 border-brand-500/40 shadow-sm'
                    : 'bg-slate-950/60 border-slate-800 hover:border-slate-700 hover:bg-slate-900/40'
                }`}
              >
                <div className="flex items-center justify-between w-full mb-2">
                  <div
                    className={`p-1.5 rounded-lg ${
                      isSelected ? 'bg-brand-500/20 text-brand-400' : 'bg-slate-800 text-slate-400'
                    }`}
                  >
                    <Icon className="w-4 h-4" />
                  </div>
                  <span
                    className={`text-[9px] font-bold px-1.5 py-0.5 rounded uppercase tracking-wider ${
                      isSelected
                        ? 'bg-brand-500/30 text-brand-300'
                        : 'bg-slate-800/80 text-slate-500'
                    }`}
                  >
                    {opt.badge}
                  </span>
                </div>
                <div>
                  <h3
                    className={`text-xs font-bold ${
                      isSelected ? 'text-white' : 'text-slate-200'
                    }`}
                  >
                    {opt.label}
                  </h3>
                  <p className="text-[10px] text-slate-500 line-clamp-2 mt-0.5 leading-snug">
                    {opt.description}
                  </p>
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {/* ========================================================= */}
      {/* 2. CASCADING FILTER TOOLBAR */}
      {/* ========================================================= */}
      <div className="glass-panel rounded-2xl p-5 border border-slate-800 space-y-4">
        <div className="flex items-center justify-between pb-3 border-b border-slate-800/80">
          <div className="flex items-center gap-2">
            <Filter className="w-4 h-4 text-brand-400" />
            <h2 className="text-sm font-heading font-bold text-white uppercase tracking-wider">
              Filter Parameters & Jurisdictional Scope
            </h2>
          </div>
          {(selectedDisease || selectedDistrict || selectedLocalBody || selectedWard || startDate || endDate || caseStatus !== 'ALL') && (
            <button
              onClick={handleResetFilters}
              className="text-xs font-semibold text-brand-400 hover:text-brand-300 underline underline-offset-4"
            >
              Reset Filters
            </button>
          )}
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
          {/* Disease */}
          <div>
            <label className="block text-[11px] font-semibold text-slate-400 mb-1">Disease</label>
            <select
              value={selectedDisease}
              onChange={(e) => setSelectedDisease(e.target.value)}
              className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-brand-500"
            >
              <option value="">All Pathogens (Statewide)</option>
              {diseases.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.name} ({d.code})
                </option>
              ))}
            </select>
          </div>

          {/* District */}
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

          {/* Local Body */}
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

          {/* Ward */}
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

          {/* Case Status */}
          <div>
            <label className="block text-[11px] font-semibold text-slate-400 mb-1">Case Status</label>
            <select
              value={caseStatus}
              onChange={(e) => setCaseStatus(e.target.value)}
              className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-brand-500"
            >
              <option value="ALL">All Statuses</option>
              <option value="CONFIRMED">Confirmed</option>
              <option value="SUSPECTED">Suspected</option>
              <option value="RECOVERED">Recovered</option>
              <option value="DECEASED">Deceased</option>
            </select>
          </div>

          {/* Date Window */}
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
      {/* 3. REPORT LIVE DATA PREVIEW TABLE */}
      {/* ========================================================= */}
      <div className="glass-panel rounded-2xl p-6 border border-slate-800 space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-3 border-b border-slate-800/80 gap-3">
          <div>
            <div className="flex items-center gap-2">
              <TableIcon className="w-5 h-5 text-brand-400" />
              <h3 className="text-base font-heading font-bold text-white">
                {preview?.title || 'Report Preview'}
              </h3>
            </div>
            <p className="text-xs text-slate-400 mt-0.5">
              Active Records: <strong className="text-white font-mono">{preview?.total_records ?? 0}</strong> compiled
              {preview?.generated_at && ` • Compiled at ${new Date(preview.generated_at).toLocaleTimeString()}`}
            </p>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={loadPreview}
              disabled={isLoading}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold transition-colors"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin text-brand-400' : ''}`} />
              <span>Refresh Table</span>
            </button>
          </div>
        </div>

        {/* Tabular Output */}
        <div className="overflow-x-auto rounded-xl border border-slate-800 bg-slate-950/80 max-h-[480px]">
          <table className="w-full text-left text-xs border-collapse">
            <thead className="bg-slate-900/90 text-slate-300 sticky top-0 z-10 border-b border-slate-800">
              <tr>
                {preview?.columns?.map((col, idx) => (
                  <th
                    key={`th-${idx}`}
                    className="py-3 px-4 font-semibold uppercase text-[10px] tracking-wider text-slate-400"
                  >
                    {col}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-mono text-[11px] text-slate-300">
              {isLoading ? (
                <tr>
                  <td colSpan={preview?.columns?.length || 6} className="py-12 text-center text-slate-500">
                    <RefreshCw className="w-5 h-5 animate-spin mx-auto mb-2 text-brand-400" />
                    <span>Compiling epidemiological records...</span>
                  </td>
                </tr>
              ) : !preview?.rows?.length ? (
                <tr>
                  <td colSpan={preview?.columns?.length || 6} className="py-12 text-center text-slate-500">
                    No records found matching active filter parameters.
                  </td>
                </tr>
              ) : (
                preview.rows.map((row, rowIdx) => (
                  <tr key={`row-${rowIdx}`} className="hover:bg-slate-900/40 transition-colors">
                    {preview.columns.map((col, colIdx) => (
                      <td key={`cell-${rowIdx}-${colIdx}`} className="py-2.5 px-4">
                        {String(row[col] ?? '')}
                      </td>
                    ))}
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
