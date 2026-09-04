import React, { useEffect } from 'react';
import { 
  MapContainer, 
  TileLayer, 
  GeoJSON, 
  Marker, 
  Popup, 
  LayersControl, 
  LayerGroup,
  useMap 
} from 'react-leaflet';
import L from 'leaflet';
import { 
  DistrictGIS, 
  LocalBodyGIS, 
  WardGIS, 
  DiseaseGISCase 
} from '../../types';
import { ShieldAlert, Activity, Calendar, MapPin, Layers, Info } from 'lucide-react';

// Fix Leaflet default marker icon path issue in Vite
import markerIcon2x from 'leaflet/dist/images/marker-icon-2x.png';
import markerIcon from 'leaflet/dist/images/marker-icon.png';
import markerShadow from 'leaflet/dist/images/marker-shadow.png';

delete (L.Icon.Default.prototype as any)._getIconUrl;
L.Icon.Default.mergeOptions({
  iconUrl: markerIcon,
  iconRetinaUrl: markerIcon2x,
  shadowUrl: markerShadow,
});

// Custom SVG Pin Generator by Severity / Status
const createCustomMarkerIcon = (status: string, severity: string) => {
  let color = '#3b82f6'; // blue default
  let pulse = false;

  if (status === 'CONFIRMED') {
    if (severity === 'CRITICAL' || severity === 'SEVERE') {
      color = '#ef4444'; // Red
      pulse = true;
    } else {
      color = '#f59e0b'; // Amber
    }
  } else if (status === 'SUSPECTED') {
    color = '#eab308'; // Yellow
  } else if (status === 'RECOVERED') {
    color = '#10b981'; // Green
  } else if (status === 'DECEASED') {
    color = '#64748b'; // Slate
  }

  const svgHtml = `
    <div style="position: relative; width: 32px; height: 32px; display: flex; align-items: center; justify-content: center;">
      ${pulse ? `<div style="position: absolute; width: 28px; height: 28px; border-radius: 50%; background: ${color}; opacity: 0.4; animation: ping 1.5s cubic-bezier(0, 0, 0.2, 1) infinite;"></div>` : ''}
      <div style="position: relative; width: 24px; height: 24px; border-radius: 50%; background: ${color}; border: 2.5px solid #ffffff; box-shadow: 0 4px 10px rgba(0,0,0,0.5); display: flex; align-items: center; justify-content: center;">
        <div style="width: 7px; height: 7px; border-radius: 50%; background: #ffffff;"></div>
      </div>
    </div>
  `;

  return L.divIcon({
    html: svgHtml,
    className: 'custom-leaflet-marker',
    iconSize: [32, 32],
    iconAnchor: [16, 16],
    popupAnchor: [0, -16],
  });
};

// Component to dynamically re-center map when center coordinates change
const MapController: React.FC<{ center: [number, number]; zoom: number }> = ({ center, zoom }) => {
  const map = useMap();
  useEffect(() => {
    map.flyTo(center, zoom, { duration: 1.2 });
  }, [center, zoom, map]);
  return null;
};

interface SurveillanceMapProps {
  districts: DistrictGIS[];
  localBodies: LocalBodyGIS[];
  wards: WardGIS[];
  cases: DiseaseGISCase[];
  centerCoordinates: [number, number];
  zoomLevel: number;
}

export const SurveillanceMap: React.FC<SurveillanceMapProps> = ({
  districts,
  localBodies,
  wards,
  cases,
  centerCoordinates,
  zoomLevel,
}) => {
  return (
    <div className="w-full h-[580px] rounded-xl overflow-hidden border border-slate-800 shadow-2xl relative">
      <MapContainer
        center={centerCoordinates}
        zoom={zoomLevel}
        scrollWheelZoom={true}
        className="w-full h-full bg-slate-950"
      >
        <MapController center={centerCoordinates} zoom={zoomLevel} />

        <LayersControl position="topright">
          {/* Base Map Layers */}
          <LayersControl.BaseLayer checked name="CartoDB Dark Matter">
            <TileLayer
              attribution='&copy; <a href="https://carto.com/">CARTO</a>'
              url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
              maxZoom={19}
            />
          </LayersControl.BaseLayer>

          <LayersControl.BaseLayer name="OpenStreetMap Standard">
            <TileLayer
              attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              maxZoom={19}
            />
          </LayersControl.BaseLayer>

          {/* Overlay Layer 1: District Boundaries */}
          <LayersControl.Overlay checked name="District Boundaries (Kerala)">
            <LayerGroup>
              {districts.map((d) => (
                d.geojson ? (
                  <GeoJSON
                    key={`dist-${d.id}`}
                    data={d.geojson}
                    style={{
                      color: '#06b6d4',
                      weight: 2,
                      opacity: 0.8,
                      fillColor: '#0891b2',
                      fillOpacity: 0.08,
                      dashArray: '4, 4',
                    }}
                  >
                    <Popup>
                      <div className="text-slate-900 font-sans text-xs">
                        <div className="font-bold text-sm text-cyan-800">{d.name} District</div>
                        <div>State: {d.state}</div>
                        <div>Code: {d.code}</div>
                        <div className="text-[10px] text-slate-500 mt-1 font-mono">Source: {d.source}</div>
                      </div>
                    </Popup>
                  </GeoJSON>
                ) : null
              ))}
            </LayerGroup>
          </LayersControl.Overlay>

          {/* Overlay Layer 2: Local Body Boundaries */}
          <LayersControl.Overlay checked name="Local Bodies (Corporation/Panchayat)">
            <LayerGroup>
              {localBodies.map((lb) => (
                lb.geojson ? (
                  <GeoJSON
                    key={`lb-${lb.id}`}
                    data={lb.geojson}
                    style={{
                      color: '#10b981',
                      weight: 1.5,
                      opacity: 0.7,
                      fillColor: '#059669',
                      fillOpacity: 0.12,
                    }}
                  >
                    <Popup>
                      <div className="text-slate-900 font-sans text-xs">
                        <div className="font-bold text-sm text-emerald-800">{lb.name}</div>
                        <div>Type: {lb.body_type}</div>
                        <div className="text-[10px] text-slate-500 mt-1 font-mono">Source: {lb.source}</div>
                      </div>
                    </Popup>
                  </GeoJSON>
                ) : null
              ))}
            </LayerGroup>
          </LayersControl.Overlay>

          {/* Overlay Layer 3: Ward Boundaries */}
          <LayersControl.Overlay checked name="Ward Boundaries">
            <LayerGroup>
              {wards.map((w) => (
                w.geojson ? (
                  <GeoJSON
                    key={`ward-${w.id}`}
                    data={w.geojson}
                    style={{
                      color: '#8b5cf6',
                      weight: 1,
                      opacity: 0.6,
                      fillColor: '#7c3aed',
                      fillOpacity: 0.15,
                    }}
                  >
                    <Popup>
                      <div className="text-slate-900 font-sans text-xs">
                        <div className="font-bold text-sm text-purple-800">Ward #{w.ward_number}: {w.name}</div>
                        <div className="text-[10px] text-slate-500 mt-1 font-mono">Source: {w.source}</div>
                      </div>
                    </Popup>
                  </GeoJSON>
                ) : null
              ))}
            </LayerGroup>
          </LayersControl.Overlay>

          {/* Overlay Layer 4: Disease Case Locations */}
          <LayersControl.Overlay checked name="Disease Case Incidents">
            <LayerGroup>
              {cases.map((c) => (
                <Marker
                  key={`case-${c.case_id}`}
                  position={[c.latitude, c.longitude]}
                  icon={createCustomMarkerIcon(c.case_status, c.severity)}
                >
                  <Popup>
                    <div className="p-1 max-w-xs font-sans text-slate-900 space-y-2">
                      <div className="flex items-center justify-between border-b pb-1.5 gap-2">
                        <div className="font-bold text-sm text-slate-900 flex items-center gap-1">
                          <Activity className="w-4 h-4 text-rose-600" />
                          <span>{c.disease_name}</span>
                        </div>
                        <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded uppercase ${
                          c.case_status === 'CONFIRMED' ? 'bg-red-100 text-red-800' : 'bg-amber-100 text-amber-800'
                        }`}>
                          {c.case_status}
                        </span>
                      </div>

                      <div className="grid grid-cols-2 gap-x-2 gap-y-1 text-xs text-slate-700">
                        <div>
                          <span className="text-slate-500 font-medium">Pseudo ID:</span>
                          <div className="font-mono font-semibold">{c.patient_pseudo_id}</div>
                        </div>
                        <div>
                          <span className="text-slate-500 font-medium">Severity:</span>
                          <div className="font-semibold text-rose-700">{c.severity}</div>
                        </div>
                        <div>
                          <span className="text-slate-500 font-medium">Classification:</span>
                          <div>{c.contagion_type}</div>
                        </div>
                        <div>
                          <span className="text-slate-500 font-medium">Diagnosis:</span>
                          <div>{c.diagnosis_date}</div>
                        </div>
                      </div>

                      <div className="bg-slate-100 p-1.5 rounded text-[11px] text-slate-700 flex items-center gap-1.5">
                        <MapPin className="w-3.5 h-3.5 text-cyan-600 shrink-0" />
                        <span className="truncate">
                          {c.district_name ? `${c.district_name}` : ''} {c.ward_number ? `(Ward ${c.ward_number})` : ''}
                        </span>
                      </div>

                      <div className="flex items-center justify-between text-[10px] text-slate-500 pt-1 border-t">
                        <span>Coordinates: {c.latitude.toFixed(4)}°, {c.longitude.toFixed(4)}°</span>
                        <span className="font-mono text-cyan-700 font-bold">[{c.source}]</span>
                      </div>
                    </div>
                  </Popup>
                </Marker>
              ))}
            </LayerGroup>
          </LayersControl.Overlay>
        </LayersControl>
      </MapContainer>

      {/* Floating Spatial Hierarchy & Status Overlay */}
      <div className="absolute bottom-4 left-4 z-[1000] bg-slate-900/90 backdrop-blur-md px-3.5 py-2 rounded-xl border border-slate-800 text-xs text-slate-300 shadow-xl flex items-center gap-3">
        <div className="flex items-center gap-1.5 text-cyan-400 font-semibold">
          <MapPin className="w-3.5 h-3.5" />
          <span>Hierarchy: Kerala &rarr; District &rarr; Local Body &rarr; Ward</span>
        </div>
        <span className="text-slate-600">|</span>
        <span className="font-mono text-[11px] text-slate-400">Cases Displayed: <strong className="text-white">{cases.length}</strong></span>
        <span className="text-slate-600">|</span>
        <span className="text-[10px] bg-brand-500/20 text-brand-400 px-2 py-0.5 rounded border border-brand-500/30">EPSG:4326</span>
      </div>
    </div>
  );
};
