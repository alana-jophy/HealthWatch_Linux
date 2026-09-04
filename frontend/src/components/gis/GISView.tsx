import React, { useState, useEffect } from 'react';
import { 
  fetchDistricts, 
  fetchLocalBodies, 
  fetchWards, 
  fetchDiseases, 
  fetchGISCases 
} from '../../services/api';
import { 
  DistrictGIS, 
  LocalBodyGIS, 
  WardGIS, 
  DiseaseItem, 
  DiseaseGISCase 
} from '../../types';
import { GISFilterBar } from './GISFilterBar';
import { SurveillanceMap } from './SurveillanceMap';
import { 
  MapPin, 
  Activity, 
  RefreshCw,
  Layers,
  Database,
  Calendar,
  AlertTriangle,
  FileSpreadsheet,
  Flame
} from 'lucide-react';
import { DiseaseHotspotHeatmap } from './DiseaseHotspotHeatmap';

export const GISView: React.FC = () => {
  const [diseases, setDiseases] = useState<DiseaseItem[]>([]);
  const [districts, setDistricts] = useState<DistrictGIS[]>([]);
  const [localBodies, setLocalBodies] = useState<LocalBodyGIS[]>([]);
  const [wards, setWards] = useState<WardGIS[]>([]);
  const [cases, setCases] = useState<DiseaseGISCase[]>([]);
  const [gisMode, setGisMode] = useState<'hierarchy' | 'heatmap'>('hierarchy');

  // Hierarchical Filter States
  const [selectedDistrict, setSelectedDistrict] = useState<string>('');
  const [selectedLocalBody, setSelectedLocalBody] = useState<string>('');
  const [selectedWard, setSelectedWard] = useState<string>('');
  const [selectedDisease, setSelectedDisease] = useState<string>('');
  const [selectedStatus, setSelectedStatus] = useState<string>('');
  const [startDate, setStartDate] = useState<string>('');
  const [endDate, setEndDate] = useState<string>('');

  // Map Coordinates & Zoom Navigation State
  // Default Kerala State Center: Lat 8.5241, Lng 76.9366 (Zoom: 9)
  const [centerCoordinates, setCenterCoordinates] = useState<[number, number]>([8.5241, 76.9366]);
  const [zoomLevel, setZoomLevel] = useState<number>(9);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  // 1. Initial Load: Districts & Disease Catalog
  useEffect(() => {
    const initGIS = async () => {
      setIsLoading(true);
      try {
        const [dists, dis] = await Promise.all([
          fetchDistricts(),
          fetchDiseases(),
        ]);
        setDistricts(dists);
        setDiseases(dis);
      } catch (err) {
        console.error('Failed to load initial GIS data:', err);
      } finally {
        setIsLoading(false);
      }
    };
    initGIS();
  }, []);

  // 2. Cascading District Change Handler: Loads Local Bodies and resets child selections
  const handleDistrictChange = async (districtId: string) => {
    setSelectedDistrict(districtId);
    setSelectedLocalBody('');
    setSelectedWard('');
    setWards([]);

    if (districtId) {
      try {
        const lbs = await fetchLocalBodies(districtId);
        setLocalBodies(lbs);

        const matchedDist = districts.find(d => d.id === districtId);
        if (matchedDist && matchedDist.center_latitude && matchedDist.center_longitude) {
          setCenterCoordinates([matchedDist.center_latitude, matchedDist.center_longitude]);
          setZoomLevel(11);
        }
      } catch (err) {
        console.error('Error fetching local bodies for district:', err);
      }
    } else {
      setLocalBodies([]);
      setCenterCoordinates([8.5241, 76.9366]);
      setZoomLevel(9);
    }
  };

  // 3. Cascading Local Body Change Handler: Loads Wards and resets child ward selection
  const handleLocalBodyChange = async (localBodyId: string) => {
    setSelectedLocalBody(localBodyId);
    setSelectedWard('');

    if (localBodyId) {
      try {
        const wds = await fetchWards(localBodyId);
        setWards(wds);

        const matchedLb = localBodies.find(lb => lb.id === localBodyId);
        if (matchedLb && matchedLb.center_latitude && matchedLb.center_longitude) {
          setCenterCoordinates([matchedLb.center_latitude, matchedLb.center_longitude]);
          setZoomLevel(13);
        }
      } catch (err) {
        console.error('Error fetching wards for local body:', err);
      }
    } else {
      setWards([]);
      if (selectedDistrict) {
        const matchedDist = districts.find(d => d.id === selectedDistrict);
        if (matchedDist && matchedDist.center_latitude && matchedDist.center_longitude) {
          setCenterCoordinates([matchedDist.center_latitude, matchedDist.center_longitude]);
          setZoomLevel(11);
        }
      }
    }
  };

  // 4. Ward Selection Handler: Zooms directly into Ward
  const handleWardChange = (wardId: string) => {
    setSelectedWard(wardId);

    if (wardId) {
      const matchedWard = wards.find(w => w.id === wardId);
      if (matchedWard && matchedWard.center_latitude && matchedWard.center_longitude) {
        setCenterCoordinates([matchedWard.center_latitude, matchedWard.center_longitude]);
        setZoomLevel(15);
      }
    } else if (selectedLocalBody) {
      const matchedLb = localBodies.find(lb => lb.id === selectedLocalBody);
      if (matchedLb && matchedLb.center_latitude && matchedLb.center_longitude) {
        setCenterCoordinates([matchedLb.center_latitude, matchedLb.center_longitude]);
        setZoomLevel(13);
      }
    }
  };

  // 5. Fetch Filtered GIS Cases dynamically from backend
  const loadCases = async () => {
    try {
      const caseResults = await fetchGISCases({
        district_id: selectedDistrict || undefined,
        local_body_id: selectedLocalBody || undefined,
        ward_id: selectedWard || undefined,
        disease_id: selectedDisease || undefined,
        case_status: selectedStatus || undefined,
        start_date: startDate || undefined,
        end_date: endDate || undefined,
      });
      setCases(caseResults);
    } catch (err) {
      console.error('Error fetching GIS cases:', err);
    }
  };

  useEffect(() => {
    loadCases();
  }, [selectedDistrict, selectedLocalBody, selectedWard, selectedDisease, selectedStatus, startDate, endDate]);

  // 6. Reset all hierarchical filters
  const handleResetFilters = () => {
    setSelectedDistrict('');
    setSelectedLocalBody('');
    setSelectedWard('');
    setSelectedDisease('');
    setSelectedStatus('');
    setStartDate('');
    setEndDate('');
    setLocalBodies([]);
    setWards([]);
    setCenterCoordinates([8.5241, 76.9366]);
    setZoomLevel(9);
  };

  const activeDistrictName = districts.find(d => d.id === selectedDistrict)?.name;
  const activeLocalBodyName = localBodies.find(lb => lb.id === selectedLocalBody)?.name;
  const activeWardName = wards.find(w => w.id === selectedWard)?.name;

  return (
    <div className="space-y-6">
      {/* Title & Hierarchy Breadcrumb Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 glass-panel rounded-2xl p-5 md:p-6">
        <div>
          <div className="flex items-center gap-2 text-xs font-semibold text-brand-400 mb-1">
            <MapPin className="w-3.5 h-3.5" />
            <span>State of Kerala Spatial Surveillance</span>
          </div>
          <h1 className="font-heading text-xl md:text-2xl font-bold text-white tracking-tight">
            District &rarr; Local Body &rarr; Ward Navigation Map
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Hierarchical geographic drilldown with PostGIS spatial telemetry and auto-zooming layer management.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <div className="flex bg-slate-950 p-1 rounded-xl border border-slate-800">
            <button
              onClick={() => setGisMode('hierarchy')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                gisMode === 'hierarchy'
                  ? 'bg-brand-600 text-white shadow-sm'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <Layers className="w-3.5 h-3.5" />
              <span>Hierarchical Markers</span>
            </button>
            <button
              onClick={() => setGisMode('heatmap')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                gisMode === 'heatmap'
                  ? 'bg-rose-600 text-white shadow-sm'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <Flame className="w-3.5 h-3.5 text-amber-300" />
              <span>Disease Hotspot Heatmap</span>
            </button>
          </div>

          {gisMode === 'hierarchy' && (
            <button
              onClick={loadCases}
              className="flex items-center gap-2 px-3 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-xs font-medium text-slate-200 border border-slate-700 transition-colors shadow-sm"
            >
              <RefreshCw className="w-3.5 h-3.5 text-brand-400" />
              <span>Refresh</span>
            </button>
          )}
        </div>
      </div>

      {gisMode === 'heatmap' ? (
        <DiseaseHotspotHeatmap />
      ) : (
        <>

      {/* Cascading Filter Bar */}
      <GISFilterBar
        diseases={diseases}
        districts={districts}
        localBodies={localBodies}
        wards={wards}
        selectedDistrict={selectedDistrict}
        selectedLocalBody={selectedLocalBody}
        selectedWard={selectedWard}
        selectedDisease={selectedDisease}
        selectedStatus={selectedStatus}
        startDate={startDate}
        endDate={endDate}
        onChangeDistrict={handleDistrictChange}
        onChangeLocalBody={handleLocalBodyChange}
        onChangeWard={handleWardChange}
        onChangeDisease={setSelectedDisease}
        onChangeStatus={setSelectedStatus}
        onChangeStartDate={setStartDate}
        onChangeEndDate={setEndDate}
        onResetFilters={handleResetFilters}
      />

      {/* Reusable Leaflet GIS Map with dynamic Auto-Zoom */}
      <SurveillanceMap
        districts={districts}
        localBodies={localBodies}
        wards={wards}
        cases={cases}
        centerCoordinates={centerCoordinates}
        zoomLevel={zoomLevel}
      />

      {/* Dynamic Geographic Scope & KPIs */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="glass-panel p-4 rounded-xl flex items-center justify-between">
          <div>
            <div className="text-xs text-slate-400">Current Scope</div>
            <div className="font-heading text-sm font-bold text-cyan-400 mt-1 truncate max-w-[170px]">
              {activeWardName ? `Ward: ${activeWardName}` : activeLocalBodyName ? `${activeLocalBodyName}` : activeDistrictName ? `${activeDistrictName} Dist.` : 'Kerala State'}
            </div>
          </div>
          <div className="p-2.5 rounded-lg bg-cyan-500/15 text-cyan-400 border border-cyan-500/20">
            <MapPin className="w-5 h-5" />
          </div>
        </div>

        <div className="glass-panel p-4 rounded-xl flex items-center justify-between">
          <div>
            <div className="text-xs text-slate-400">Cases in Scope</div>
            <div className="font-heading text-xl font-bold text-white mt-1">{cases.length}</div>
          </div>
          <div className="p-2.5 rounded-lg bg-rose-500/15 text-rose-400 border border-rose-500/20">
            <Activity className="w-5 h-5" />
          </div>
        </div>

        <div className="glass-panel p-4 rounded-xl flex items-center justify-between">
          <div>
            <div className="text-xs text-slate-400">Active Wards</div>
            <div className="font-heading text-xl font-bold text-purple-400 mt-1">{wards.length || 'All'}</div>
          </div>
          <div className="p-2.5 rounded-lg bg-purple-500/15 text-purple-400 border border-purple-500/20">
            <Layers className="w-5 h-5" />
          </div>
        </div>

        <div className="glass-panel p-4 rounded-xl flex items-center justify-between">
          <div>
            <div className="text-xs text-slate-400">Spatial Telemetry</div>
            <div className="font-heading text-sm font-bold text-emerald-400 mt-1">PostGIS SRID:4326</div>
          </div>
          <div className="p-2.5 rounded-lg bg-emerald-500/15 text-emerald-400 border border-emerald-500/20">
            <Database className="w-5 h-5" />
          </div>
        </div>
      </div>
        </>
      )}
    </div>
  );
};
