import React, { useState, useEffect } from 'react';
import {
  MapContainer,
  TileLayer,
  CircleMarker,
  Popup,
  useMap,
} from 'react-leaflet';
import {
  fetchDistricts,
  fetchLocalBodies,
  fetchWards,
  fetchDiseases,
  fetchDiseaseHeatmaps,
} from '../../services/api';
import {
  DistrictGIS,
  LocalBodyGIS,
  WardGIS,
  DiseaseItem,
  DiseaseHeatmapResponse,
  HotspotAreaItem,
} from '../../types';
import { HeatmapLayer } from './HeatmapLayer';
import {
  Flame,
  ShieldCheck,
  MapPin,
  Filter,
  Calendar,
  Layers,
  RefreshCw,
  Activity,
  AlertTriangle,
  Info,
  Sliders,
  CheckCircle2,
  TrendingUp,
} from 'lucide-react';

// Re-centering helper for Leaflet Map
const MapFlyTo: React.FC<{ center: [number, number]; zoom: number }> = ({ center, zoom }) => {
  const map = useMap();
  useEffect(() => {
    map.flyTo(center, zoom, { duration: 1.2 });
  }, [center, zoom, map]);
  return null;
};

export const DiseaseHotspotHeatmap: React.FC = () => {
  // State for Catalog / Geographic Hierarchy
  const [diseases, setDiseases] = useState<DiseaseItem[]>([]);
  const [districts, setDistricts] = useState<DistrictGIS[]>([]);
  const [localBodies, setLocalBodies] = useState<LocalBodyGIS[]>([]);
  const [wards, setWards] = useState<WardGIS[]>([]);

  // Filter States
  const [selectedDisease, setSelectedDisease] = useState<string>('');
  const [selectedDistrict, setSelectedDistrict] = useState<string>('');
  const [selectedLocalBody, setSelectedLocalBody] = useState<string>('');
  const [selectedWard, setSelectedWard] = useState<string>('');
  const [selectedStatus, setSelectedStatus] = useState<string>('');
  const [startDate, setStartDate] = useState<string>('');
  const [endDate, setEndDate] = useState<string>('');

  // Heatmap Customization Controls
  const [heatRadius, setHeatRadius] = useState<number>(30);
  const [heatBlur, setHeatBlur] = useState<number>(20);
  const [showHotspotRings, setShowHotspotRings] = useState<boolean>(true);

  // Map Navigation State (Default to Kerala state center)
  const [mapCenter, setMapCenter] = useState<[number, number]>([8.5241, 76.9366]);
  const [mapZoom, setMapZoom] = useState<number>(9);

  // Heatmap Data & Loading State
  const [heatmapData, setHeatmapData] = useState<DiseaseHeatmapResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [selectedHotspot, setSelectedHotspot] = useState<HotspotAreaItem | null>(null);

  // 1. Initial Load: Catalogs
  useEffect(() => {
    const initCatalogs = async () => {
      try {
        const [dists, dis] = await Promise.all([
          fetchDistricts(),
          fetchDiseases(),
        ]);
        setDistricts(dists);
        setDiseases(dis);
      } catch (err) {
        console.error('Failed to load districts/diseases catalog:', err);
      }
    };
    initCatalogs();
  }, []);

  // 2. Fetch Heatmap Data when Filters Change
  const loadHeatmapData = async () => {
    setIsLoading(true);
    try {
      const data = await fetchDiseaseHeatmaps({
        disease_id: selectedDisease || undefined,
        district_id: selectedDistrict || undefined,
        local_body_id: selectedLocalBody || undefined,
        ward_id: selectedWard || undefined,
        case_status: selectedStatus || undefined,
        start_date: startDate || undefined,
        end_date: endDate || undefined,
      });
      setHeatmapData(data);
    } catch (err) {
      console.error('Failed to query disease heatmap telemetry:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadHeatmapData();
  }, [
    selectedDisease,
    selectedDistrict,
    selectedLocalBody,
    selectedWard,
    selectedStatus,
    startDate,
    endDate,
  ]);

  // 3. District Cascading Change
  const handleDistrictChange = async (districtId: string) => {
    setSelectedDistrict(districtId);
    setSelectedLocalBody('');
    setSelectedWard('');
    setWards([]);

    if (districtId) {
      try {
        const lbs = await fetchLocalBodies(districtId);
        setLocalBodies(lbs);
        const dist = districts.find(d => d.id === districtId);
        if (dist && dist.center_latitude && dist.center_longitude) {
          setMapCenter([dist.center_latitude, dist.center_longitude]);
          setMapZoom(11);
        }
      } catch (err) {
        console.error('Error loading local bodies for district:', err);
      }
    } else {
      setLocalBodies([]);
      setMapCenter([8.5241, 76.9366]);
      setMapZoom(9);
    }
  };

  // 4. Local Body Cascading Change
  const handleLocalBodyChange = async (localBodyId: string) => {
    setSelectedLocalBody(localBodyId);
    setSelectedWard('');

    if (localBodyId) {
      try {
        const wds = await fetchWards(localBodyId);
        setWards(wds);
        const lb = localBodies.find(l => l.id === localBodyId);
        if (lb && lb.center_latitude && lb.center_longitude) {
          setMapCenter([lb.center_latitude, lb.center_longitude]);
          setMapZoom(13);
        }
      } catch (err) {
        console.error('Error loading wards for local body:', err);
      }
    } else {
      setWards([]);
      if (selectedDistrict) {
        const dist = districts.find(d => d.id === selectedDistrict);
        if (dist && dist.center_latitude && dist.center_longitude) {
          setMapCenter([dist.center_latitude, dist.center_longitude]);
          setMapZoom(11);
        }
      }
    }
  };

  // 5. Ward Change
  const handleWardChange = (wardId: string) => {
    setSelectedWard(wardId);
    if (wardId) {
      const w = wards.find(item => item.id === wardId);
      if (w && w.center_latitude && w.center_longitude) {
        setMapCenter([w.center_latitude, w.center_longitude]);
        setMapZoom(15);
      }
    }
  };

  // 6. Reset Filters
  const handleResetFilters = () => {
    setSelectedDisease('');
    setSelectedDistrict('');
    setSelectedLocalBody('');
    setSelectedWard('');
    setSelectedStatus('');
    setStartDate('');
    setEndDate('');
    setLocalBodies([]);
    setWards([]);
    setSelectedHotspot(null);
    setMapCenter([8.5241, 76.9366]);
    setMapZoom(9);
  };

  // 7. Focus on a Hotspot Area from Dashboard
  const handleFocusHotspot = (hotspot: HotspotAreaItem) => {
    setSelectedHotspot(hotspot);
    setMapCenter([hotspot.latitude, hotspot.longitude]);
    setMapZoom(14);
  };

  const activeDistrictName = districts.find(d => d.id === selectedDistrict)?.name;

  return (
    <div className="space-y-6">
      {/* 1. Header Banner & Synthetic Demo Badge */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 glass-panel rounded-2xl p-6 relative overflow-hidden">
        <div className="space-y-1 z-10 max-w-2xl">
          <div className="flex items-center gap-2 text-xs font-semibold text-rose-400">
            <Flame className="w-4 h-4 animate-pulse text-rose-500" />
            <span>Disease Surveillance & Outbreak Density Analysis</span>
          </div>
          <h1 className="font-heading text-xl md:text-2xl font-bold text-white tracking-tight">
            Disease Hotspot Heatmap Dashboard
          </h1>
          <p className="text-xs text-slate-400">
            Continuous density surface mapping population-level disease incidents across Kerala administrative wards with differential privacy aggregation.
          </p>
        </div>

        {/* Demo Identification & Privacy Badges */}
        <div className="flex flex-col sm:flex-row items-start sm:items-center gap-2 z-10">
          <div className="px-3 py-1.5 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-400 text-xs font-semibold flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-amber-500 animate-ping"></span>
            <span>DEMO / SYNTHETIC DATA</span>
          </div>
          <div className="px-3 py-1.5 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs font-medium flex items-center gap-1.5">
            <ShieldCheck className="w-3.5 h-3.5" />
            <span>Privacy Preserved (Ward Centroid)</span>
          </div>
        </div>
      </div>

      {/* 2. Surveillance Dashboard Key Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Total Cases */}
        <div className="glass-panel rounded-xl p-4 border border-slate-800">
          <div className="flex items-center justify-between text-slate-400 text-xs mb-1">
            <span>Total Cases Statewide</span>
            <Activity className="w-4 h-4 text-brand-400" />
          </div>
          <div className="text-2xl font-bold font-heading text-white">
            {heatmapData?.total_cases_statewide ?? '...'}
          </div>
          <div className="text-[11px] text-slate-500 mt-1 flex items-center gap-1">
            <span className="text-brand-400 font-medium">All Kerala</span>
            <span>surveillance incidents</span>
          </div>
        </div>

        {/* Cases in Selected Area */}
        <div className="glass-panel rounded-xl p-4 border border-slate-800">
          <div className="flex items-center justify-between text-slate-400 text-xs mb-1">
            <span>Cases in Selected Area</span>
            <MapPin className="w-4 h-4 text-amber-400" />
          </div>
          <div className="text-2xl font-bold font-heading text-amber-300">
            {heatmapData?.cases_in_selected_area ?? '...'}
          </div>
          <div className="text-[11px] text-slate-500 mt-1 truncate">
            {activeDistrictName ? `In ${activeDistrictName}` : 'Statewide filter active'}
          </div>
        </div>

        {/* Hotspot Areas Identified */}
        <div className="glass-panel rounded-xl p-4 border border-slate-800">
          <div className="flex items-center justify-between text-slate-400 text-xs mb-1">
            <span>Hotspot Areas</span>
            <Flame className="w-4 h-4 text-rose-400" />
          </div>
          <div className="text-2xl font-bold font-heading text-rose-400 flex items-center gap-2">
            <span>{heatmapData?.concentration_summary?.hotspot ?? 0}</span>
            <span className="text-xs font-normal text-rose-500/80 px-2 py-0.5 rounded bg-rose-500/10 border border-rose-500/20">
              Critical
            </span>
          </div>
          <div className="text-[11px] text-slate-500 mt-1">
            {`${heatmapData?.concentration_summary?.high ?? 0} High, ${heatmapData?.concentration_summary?.moderate ?? 0} Mod zones`}
          </div>
        </div>

        {/* Clinical Case Breakdown */}
        <div className="glass-panel rounded-xl p-4 border border-slate-800">
          <div className="flex items-center justify-between text-slate-400 text-xs mb-1">
            <span>Active vs Recovered</span>
            <TrendingUp className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-2xl font-bold font-heading text-emerald-300">
            {heatmapData?.status_distribution?.confirmed ?? 0}
            <span className="text-xs font-normal text-slate-400 ml-1.5">Confirmed</span>
          </div>
          <div className="text-[11px] text-slate-500 mt-1">
            {`${heatmapData?.status_distribution?.suspected ?? 0} Suspected · ${heatmapData?.status_distribution?.recovered ?? 0} Recovered`}
          </div>
        </div>
      </div>

      {/* 3. Comprehensive Cascading Filter Bar */}
      <div className="glass-panel rounded-2xl p-5 border border-slate-800 space-y-4">
        <div className="flex items-center justify-between border-b border-slate-800/80 pb-3">
          <div className="flex items-center gap-2 text-xs font-semibold text-slate-300">
            <Filter className="w-4 h-4 text-brand-400" />
            <span>Surveillance Filters (Updates Heatmap in Real-Time)</span>
          </div>

          <button
            onClick={handleResetFilters}
            className="flex items-center gap-1.5 text-xs text-slate-400 hover:text-white px-2.5 py-1 rounded-lg hover:bg-slate-800 transition-colors"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>Reset Filters</span>
          </button>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
          {/* Disease Filter */}
          <div>
            <label className="block text-[11px] font-medium text-slate-400 mb-1">Disease</label>
            <select
              value={selectedDisease}
              onChange={(e) => setSelectedDisease(e.target.value)}
              className="w-full bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-brand-500"
            >
              <option value="">All Diseases</option>
              {diseases.map(d => (
                <option key={d.id} value={d.id}>{d.name} ({d.code})</option>
              ))}
            </select>
          </div>

          {/* District Filter */}
          <div>
            <label className="block text-[11px] font-medium text-slate-400 mb-1">District</label>
            <select
              value={selectedDistrict}
              onChange={(e) => handleDistrictChange(e.target.value)}
              className="w-full bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-brand-500"
            >
              <option value="">All Kerala Districts</option>
              {districts.map(d => (
                <option key={d.id} value={d.id}>{d.name}</option>
              ))}
            </select>
          </div>

          {/* Local Body Filter */}
          <div>
            <label className="block text-[11px] font-medium text-slate-400 mb-1">Local Body</label>
            <select
              value={selectedLocalBody}
              onChange={(e) => handleLocalBodyChange(e.target.value)}
              disabled={!selectedDistrict}
              className="w-full bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-brand-500 disabled:opacity-50"
            >
              <option value="">All Local Bodies</option>
              {localBodies.map(lb => (
                <option key={lb.id} value={lb.id}>{lb.name}</option>
              ))}
            </select>
          </div>

          {/* Ward Filter */}
          <div>
            <label className="block text-[11px] font-medium text-slate-400 mb-1">Ward</label>
            <select
              value={selectedWard}
              onChange={(e) => handleWardChange(e.target.value)}
              disabled={!selectedLocalBody}
              className="w-full bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-brand-500 disabled:opacity-50"
            >
              <option value="">All Wards</option>
              {wards.map(w => (
                <option key={w.id} value={w.id}>Ward {w.ward_number}: {w.name}</option>
              ))}
            </select>
          </div>

          {/* Case Status Filter */}
          <div>
            <label className="block text-[11px] font-medium text-slate-400 mb-1">Case Status</label>
            <select
              value={selectedStatus}
              onChange={(e) => setSelectedStatus(e.target.value)}
              className="w-full bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-brand-500"
            >
              <option value="">All Statuses</option>
              <option value="SUSPECTED">SUSPECTED</option>
              <option value="CONFIRMED">CONFIRMED</option>
              <option value="RECOVERED">RECOVERED</option>
              <option value="DECEASED">DECEASED</option>
            </select>
          </div>

          {/* Date Range Start */}
          <div>
            <label className="block text-[11px] font-medium text-slate-400 mb-1 flex items-center gap-1">
              <Calendar className="w-3 h-3 text-slate-500" />
              <span>Diagnosed On/After</span>
            </label>
            <input
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              className="w-full bg-slate-900 border border-slate-700 rounded-lg px-2.5 py-1 text-xs text-slate-200 focus:outline-none focus:border-brand-500"
            />
          </div>
        </div>

        {/* Heatmap Visual Tuning Controls */}
        <div className="flex flex-wrap items-center justify-between gap-4 pt-3 border-t border-slate-800/80 text-xs text-slate-400">
          <div className="flex items-center gap-6">
            <div className="flex items-center gap-2">
              <Sliders className="w-3.5 h-3.5 text-brand-400" />
              <span>Heat Radius:</span>
              <input
                type="range"
                min="15"
                max="50"
                value={heatRadius}
                onChange={(e) => setHeatRadius(Number(e.target.value))}
                className="w-24 accent-brand-500 h-1 bg-slate-800 rounded-lg cursor-pointer"
              />
              <span className="text-slate-300 font-mono">{heatRadius}px</span>
            </div>

            <div className="flex items-center gap-2">
              <span>Blur:</span>
              <input
                type="range"
                min="10"
                max="35"
                value={heatBlur}
                onChange={(e) => setHeatBlur(Number(e.target.value))}
                className="w-24 accent-brand-500 h-1 bg-slate-800 rounded-lg cursor-pointer"
              />
              <span className="text-slate-300 font-mono">{heatBlur}px</span>
            </div>
          </div>

          <label className="flex items-center gap-2 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={showHotspotRings}
              onChange={(e) => setShowHotspotRings(e.target.checked)}
              className="rounded bg-slate-900 border-slate-700 text-brand-500 focus:ring-0"
            />
            <span>Highlight Hotspot Cluster Centroids</span>
          </label>
        </div>
      </div>

      {/* 4. Interactive Map & Concentration Legend */}
      <div className="space-y-3">
        <div className="w-full h-[580px] rounded-2xl overflow-hidden border border-slate-800 shadow-2xl relative">
          <MapContainer
            center={mapCenter}
            zoom={mapZoom}
            className="w-full h-full"
            scrollWheelZoom={true}
          >
            <TileLayer
              className="map-tiles-dark"
              attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              maxZoom={19}
            />

            <MapFlyTo center={mapCenter} zoom={mapZoom} />

            {/* Leaflet Canvas Heat Layer */}
            {heatmapData && heatmapData.density_points.length > 0 && (
              <HeatmapLayer
                points={heatmapData.density_points as [number, number, number][]}
                radius={heatRadius}
                blur={heatBlur}
                maxZoom={18}
                minOpacity={0.35}
              />
            )}

            {/* Hotspot Indicators & Centroids */}
            {showHotspotRings && heatmapData?.hotspot_areas?.map((area) => {
              const isHotspot = area.risk_tier === 'HOTSPOT';
              const isHigh = area.risk_tier === 'HIGH';
              const isMod = area.risk_tier === 'MODERATE';
              const ringColor = isHotspot ? '#ef4444' : isHigh ? '#f97316' : isMod ? '#eab308' : '#3b82f6';
              const radius = isHotspot ? 24 : isHigh ? 18 : isMod ? 14 : 10;

              return (
                <CircleMarker
                  key={area.area_id}
                  center={[area.latitude, area.longitude]}
                  radius={radius}
                  pathOptions={{
                    color: ringColor,
                    fillColor: ringColor,
                    fillOpacity: isHotspot ? 0.35 : 0.25,
                    weight: isHotspot ? 2.5 : 1.5,
                  }}
                >
                  <Popup className="custom-leaflet-popup">
                    <div className="p-2 space-y-2 text-slate-800 max-w-xs">
                      <div className="flex items-center justify-between gap-2 border-b pb-1">
                        <span className="font-bold text-sm text-slate-900">{area.area_name}</span>
                        <span
                          className={`text-[10px] font-bold px-2 py-0.5 rounded ${
                            isHotspot ? 'bg-red-100 text-red-700' : isHigh ? 'bg-orange-100 text-orange-700' : 'bg-yellow-100 text-yellow-700'
                          }`}
                        >
                          {area.risk_tier}
                        </span>
                      </div>
                      <div className="text-xs space-y-1 text-slate-600">
                        <div><strong>District:</strong> {area.district_name}</div>
                        {area.local_body_name && <div><strong>Local Body:</strong> {area.local_body_name}</div>}
                        <div><strong>Total Cases:</strong> <span className="font-semibold text-slate-900">{area.total_cases}</span></div>
                        <div><strong>Confirmed:</strong> {area.confirmed_cases} | <strong>Suspected:</strong> {area.suspected_cases}</div>
                        <div><strong>Dominant Disease:</strong> {area.dominant_disease}</div>
                      </div>
                      <div className="text-[10px] text-slate-400 italic pt-1 border-t">
                        Aggregated ward centroid location
                      </div>
                    </div>
                  </Popup>
                </CircleMarker>
              );
            })}
          </MapContainer>

          {/* Privacy & Concentration Legend Overlay */}
          <div className="absolute bottom-4 left-4 z-[1000] bg-slate-950/90 backdrop-blur-md p-3.5 rounded-xl border border-slate-800 shadow-xl max-w-xs text-xs">
            <div className="font-semibold text-white mb-2 flex items-center gap-1.5">
              <Layers className="w-3.5 h-3.5 text-brand-400" />
              <span>Disease Density Scale</span>
            </div>

            <div className="space-y-1.5">
              <div className="flex items-center gap-2">
                <span className="w-3 h-3 rounded-full bg-blue-500"></span>
                <span className="text-slate-300">Low concentration</span>
                <span className="text-[10px] text-slate-500 ml-auto">&lt; 3 cases</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="w-3 h-3 rounded-full bg-amber-400"></span>
                <span className="text-slate-300">Moderate concentration</span>
                <span className="text-[10px] text-slate-500 ml-auto">3–4 cases</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="w-3 h-3 rounded-full bg-orange-500"></span>
                <span className="text-slate-300">High concentration</span>
                <span className="text-[10px] text-slate-500 ml-auto">5–9 cases</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="w-3 h-3 rounded-full bg-rose-600 animate-pulse"></span>
                <span className="text-rose-400 font-semibold">Hotspot area</span>
                <span className="text-[10px] text-rose-500 font-bold ml-auto">&ge; 10 cases</span>
              </div>
            </div>

            <div className="mt-2.5 pt-2 border-t border-slate-800/80 text-[10px] text-slate-400 flex items-start gap-1">
              <Info className="w-3 h-3 text-slate-400 shrink-0 mt-0.5" />
              <span>Patient addresses protected; aggregated by ward centroids.</span>
            </div>
          </div>
        </div>
      </div>

      {/* 5. Dashboard Panels: Hotspot Areas List & Disease Distribution */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Hotspot Areas Focus List (2 Cols) */}
        <div className="lg:col-span-2 glass-panel rounded-2xl p-6 space-y-4">
          <div className="flex items-center justify-between border-b border-slate-800/80 pb-3">
            <div>
              <h2 className="font-heading text-base font-bold text-white flex items-center gap-2">
                <Flame className="w-4 h-4 text-rose-500" />
                <span>Identified Hotspots & High Concentration Areas</span>
              </h2>
              <p className="text-xs text-slate-400 mt-0.5">
                Wards categorized by epidemiological risk tier based on case concentration.
              </p>
            </div>
            <span className="text-xs text-slate-400">
              {heatmapData?.hotspot_areas?.length ?? 0} Clusters Identified
            </span>
          </div>

          <div className="space-y-2.5 max-h-[360px] overflow-y-auto pr-1">
            {!heatmapData?.hotspot_areas || heatmapData.hotspot_areas.length === 0 ? (
              <div className="text-center py-8 text-xs text-slate-500">
                No disease clusters match the selected filter parameters.
              </div>
            ) : (
              heatmapData.hotspot_areas.map((area) => {
                const isHotspot = area.risk_tier === 'HOTSPOT';
                const isHigh = area.risk_tier === 'HIGH';
                const isMod = area.risk_tier === 'MODERATE';

                return (
                  <div
                    key={area.area_id}
                    onClick={() => handleFocusHotspot(area)}
                    className={`p-3.5 rounded-xl border transition-all cursor-pointer flex items-center justify-between gap-4 ${
                      isHotspot
                        ? 'bg-rose-500/5 border-rose-500/30 hover:border-rose-500/60'
                        : isHigh
                        ? 'bg-orange-500/5 border-orange-500/30 hover:border-orange-500/60'
                        : isMod
                        ? 'bg-yellow-500/5 border-yellow-500/20 hover:border-yellow-500/40'
                        : 'bg-slate-900/50 border-slate-800 hover:border-slate-700'
                    }`}
                  >
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <span className="font-semibold text-sm text-white">{area.area_name}</span>
                        <span
                          className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                            isHotspot
                              ? 'bg-rose-500/20 text-rose-300 border border-rose-500/30'
                              : isHigh
                              ? 'bg-orange-500/20 text-orange-300 border border-orange-500/30'
                              : isMod
                              ? 'bg-yellow-500/20 text-yellow-300 border border-yellow-500/30'
                              : 'bg-blue-500/20 text-blue-300 border border-blue-500/30'
                          }`}
                        >
                          {area.risk_tier}
                        </span>
                      </div>
                      <div className="text-xs text-slate-400">
                        {area.district_name} {area.local_body_name ? `· ${area.local_body_name}` : ''}
                      </div>
                    </div>

                    <div className="text-right shrink-0">
                      <div className="text-base font-bold font-heading text-white">
                        {area.total_cases} <span className="text-xs font-normal text-slate-400">cases</span>
                      </div>
                      <div className="text-[11px] text-brand-400 hover:underline">
                        Focus on Map &rarr;
                      </div>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* Disease Distribution Panel (1 Col) */}
        <div className="glass-panel rounded-2xl p-6 space-y-4">
          <div className="border-b border-slate-800/80 pb-3">
            <h2 className="font-heading text-base font-bold text-white flex items-center gap-2">
              <TrendingUp className="w-4 h-4 text-brand-400" />
              <span>Disease Distribution</span>
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Proportion of cases across diagnosed pathologies.
            </p>
          </div>

          <div className="space-y-4">
            {heatmapData?.disease_distribution?.map((d) => (
              <div key={d.disease_id} className="space-y-1.5">
                <div className="flex items-center justify-between text-xs">
                  <span className="text-slate-200 font-medium">{d.disease_name}</span>
                  <span className="text-slate-400 font-mono">
                    {d.case_count} cases ({d.percentage}%)
                  </span>
                </div>
                <div className="w-full bg-slate-800/80 rounded-full h-2 overflow-hidden">
                  <div
                    className={`h-full rounded-full ${
                      d.disease_code.includes('DENGUE')
                        ? 'bg-rose-500'
                        : d.disease_code.includes('COVID')
                        ? 'bg-amber-500'
                        : 'bg-brand-500'
                    }`}
                    style={{ width: `${Math.min(d.percentage, 100)}%` }}
                  />
                </div>
              </div>
            ))}

            {/* Privacy Compliance Footer */}
            <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800 text-[11px] text-slate-400 space-y-1 mt-4">
              <div className="font-semibold text-slate-300 flex items-center gap-1.5">
                <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
                <span>Ethical Surveillance Policy</span>
              </div>
              <p>
                Heatmap density surfaces are generated with differential privacy smoothing. No exact patient home coordinates are published.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
