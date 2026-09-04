import React from 'react';
import { 
  DistrictGIS, 
  LocalBodyGIS, 
  WardGIS, 
  DiseaseItem 
} from '../../types';
import { Filter, RotateCcw, MapPin, ChevronRight, Calendar, Activity } from 'lucide-react';

interface GISFilterBarProps {
  diseases: DiseaseItem[];
  districts: DistrictGIS[];
  localBodies: LocalBodyGIS[];
  wards: WardGIS[];
  
  selectedDistrict: string;
  selectedLocalBody: string;
  selectedWard: string;
  selectedDisease: string;
  selectedStatus: string;
  startDate: string;
  endDate: string;

  onChangeDistrict: (val: string) => void;
  onChangeLocalBody: (val: string) => void;
  onChangeWard: (val: string) => void;
  onChangeDisease: (val: string) => void;
  onChangeStatus: (val: string) => void;
  onChangeStartDate: (val: string) => void;
  onChangeEndDate: (val: string) => void;
  onResetFilters: () => void;
}

export const GISFilterBar: React.FC<GISFilterBarProps> = ({
  diseases,
  districts,
  localBodies,
  wards,
  selectedDistrict,
  selectedLocalBody,
  selectedWard,
  selectedDisease,
  selectedStatus,
  startDate,
  endDate,
  onChangeDistrict,
  onChangeLocalBody,
  onChangeWard,
  onChangeDisease,
  onChangeStatus,
  onChangeStartDate,
  onChangeEndDate,
  onResetFilters,
}) => {
  const currentDistrictObj = districts.find(d => d.id === selectedDistrict);
  const currentLocalBodyObj = localBodies.find(lb => lb.id === selectedLocalBody);
  const currentWardObj = wards.find(w => w.id === selectedWard);

  return (
    <div className="glass-panel rounded-xl p-4 md:p-5 space-y-4">
      {/* Top Header & Breadcrumb Hierarchy Navigation Indicator */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-800 pb-3">
        <div className="flex items-center gap-2">
          <div className="p-1.5 rounded-lg bg-brand-500/15 text-brand-400">
            <Filter className="w-4 h-4" />
          </div>
          <div>
            <h2 className="font-heading font-semibold text-sm text-slate-200">
              Hierarchical Geographic & Outbreak Filters
            </h2>
            <div className="flex items-center gap-1.5 text-[11px] text-slate-400 mt-0.5">
              <span className="text-cyan-400 font-medium">Kerala</span>
              <ChevronRight className="w-3 h-3 text-slate-600" />
              <span className={currentDistrictObj ? 'text-cyan-300 font-medium' : 'text-slate-500'}>
                {currentDistrictObj ? currentDistrictObj.name : 'All Districts'}
              </span>
              <ChevronRight className="w-3 h-3 text-slate-600" />
              <span className={currentLocalBodyObj ? 'text-emerald-300 font-medium' : 'text-slate-500'}>
                {currentLocalBodyObj ? currentLocalBodyObj.name : 'All Local Bodies'}
              </span>
              <ChevronRight className="w-3 h-3 text-slate-600" />
              <span className={currentWardObj ? 'text-purple-300 font-medium' : 'text-slate-500'}>
                {currentWardObj ? `Ward #${currentWardObj.ward_number}` : 'All Wards'}
              </span>
            </div>
          </div>
        </div>

        <button
          onClick={onResetFilters}
          className="self-start sm:self-auto flex items-center gap-1.5 text-xs text-slate-400 hover:text-white bg-slate-800/80 hover:bg-slate-700 px-3 py-1.5 rounded-lg border border-slate-700 transition-colors"
        >
          <RotateCcw className="w-3 h-3 text-brand-400" />
          <span>Reset Hierarchy</span>
        </button>
      </div>

      {/* Cascading Filter Controls Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
        {/* 1. District Cascading Selector */}
        <div className="space-y-1">
          <label className="text-[11px] font-semibold text-cyan-400 flex items-center gap-1">
            <MapPin className="w-3 h-3" />
            <span>District</span>
          </label>
          <select
            value={selectedDistrict}
            onChange={(e) => onChangeDistrict(e.target.value)}
            className="w-full bg-slate-950 border border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500 transition-colors"
          >
            <option value="">[All Districts ▼]</option>
            {districts.map((dist) => (
              <option key={dist.id} value={dist.id}>
                {dist.name} ({dist.code})
              </option>
            ))}
          </select>
        </div>

        {/* 2. Local Body Cascading Selector (Filtered by selected District) */}
        <div className="space-y-1">
          <label className="text-[11px] font-semibold text-emerald-400 flex items-center gap-1">
            <MapPin className="w-3 h-3" />
            <span>Local Body</span>
          </label>
          <select
            value={selectedLocalBody}
            onChange={(e) => onChangeLocalBody(e.target.value)}
            disabled={!selectedDistrict && localBodies.length === 0}
            className={`w-full bg-slate-950 border rounded-lg px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 transition-colors ${
              !selectedDistrict ? 'border-slate-800 text-slate-500' : 'border-slate-700'
            }`}
          >
            <option value="">
              {!selectedDistrict ? '[Select District first]' : '[All Local Bodies ▼]'}
            </option>
            {localBodies.map((lb) => (
              <option key={lb.id} value={lb.id}>
                {lb.name} ({lb.body_type})
              </option>
            ))}
          </select>
        </div>

        {/* 3. Ward Cascading Selector (Filtered by selected Local Body) */}
        <div className="space-y-1">
          <label className="text-[11px] font-semibold text-purple-400 flex items-center gap-1">
            <MapPin className="w-3 h-3" />
            <span>Ward</span>
          </label>
          <select
            value={selectedWard}
            onChange={(e) => onChangeWard(e.target.value)}
            disabled={!selectedLocalBody && wards.length === 0}
            className={`w-full bg-slate-950 border rounded-lg px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-purple-500 focus:ring-1 focus:ring-purple-500 transition-colors ${
              !selectedLocalBody ? 'border-slate-800 text-slate-500' : 'border-slate-700'
            }`}
          >
            <option value="">
              {!selectedLocalBody ? '[Select Local Body first]' : '[All Wards ▼]'}
            </option>
            {wards.map((w) => (
              <option key={w.id} value={w.id}>
                Ward #{w.ward_number}: {w.name}
              </option>
            ))}
          </select>
        </div>

        {/* 4. Disease Catalog Filter */}
        <div className="space-y-1">
          <label className="text-[11px] font-semibold text-slate-300 flex items-center gap-1">
            <Activity className="w-3 h-3 text-rose-400" />
            <span>Disease</span>
          </label>
          <select
            value={selectedDisease}
            onChange={(e) => onChangeDisease(e.target.value)}
            className="w-full bg-slate-950 border border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-brand-500 focus:ring-1 focus:ring-brand-500"
          >
            <option value="">[All Diseases ▼]</option>
            {diseases.map((d) => (
              <option key={d.id} value={d.id}>
                {d.name} ({d.code})
              </option>
            ))}
          </select>
        </div>

        {/* 5. Date Range - Start Date */}
        <div className="space-y-1">
          <label className="text-[11px] font-semibold text-slate-300 flex items-center gap-1">
            <Calendar className="w-3 h-3 text-brand-400" />
            <span>Start Date</span>
          </label>
          <input
            type="date"
            value={startDate}
            onChange={(e) => onChangeStartDate(e.target.value)}
            className="w-full bg-slate-950 border border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-brand-500 focus:ring-1 focus:ring-brand-500"
          />
        </div>

        {/* 6. Date Range - End Date / Status */}
        <div className="space-y-1">
          <label className="text-[11px] font-semibold text-slate-300 flex items-center gap-1">
            <Calendar className="w-3 h-3 text-brand-400" />
            <span>End Date</span>
          </label>
          <input
            type="date"
            value={endDate}
            onChange={(e) => onChangeEndDate(e.target.value)}
            className="w-full bg-slate-950 border border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-brand-500 focus:ring-1 focus:ring-brand-500"
          />
        </div>
      </div>
    </div>
  );
};
