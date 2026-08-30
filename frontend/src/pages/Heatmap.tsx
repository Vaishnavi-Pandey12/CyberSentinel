import React, { useState } from 'react';
import L from 'leaflet';
import { MapContainer, TileLayer, Rectangle, Popup, Marker, CircleMarker, useMap } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import { useNavigate } from 'react-router-dom';

// --- Types mapping to our Python FastAPI response ---
interface BoundingBox {
  north: number;
  south: number;
  east: number;
  west: number;
}

interface InterdictionZone {
  zone_id: string;
  priority_weight?: number;
  center: { lat: number; lng: number };
  bounding_box: BoundingBox;
  target_nodes: string[];
}

interface GraphNode {
  id: string;
  type: string;
  riskScore: number;
  metadata?: {
    label?: string;
    lat?: number;
    lng?: number;
    name?: string;
    evidence_chain?: string[];
    location_id?: string;
    [key: string]: any;
  };
}

// Custom Leaflet Icons for GIS map nodes
const createCustomPin = (color: string, label: string) => {
  return L.divIcon({
    className: '',
    html: `
      <div style="
        display: flex;
        align-items: center;
        gap: 6px;
        background: #0F1210;
        border: 1px solid ${color};
        padding: 4px 8px;
        border-radius: 6px;
        box-shadow: 0 0 12px ${color}66;
        color: #FFFFFF;
        font-family: monospace;
        font-size: 10px;
        font-weight: bold;
        white-space: nowrap;
      ">
        <span style="
          width: 8px;
          height: 8px;
          border-radius: 50%;
          background: ${color};
          box-shadow: 0 0 8px ${color};
        "></span>
        ${label}
      </div>
    `,
    iconSize: [120, 30],
    iconAnchor: [60, 15],
    popupAnchor: [0, -15],
  });
};

// Map helper to smoothly pan/zoom when new zones are detected across Pan-India
const MapUpdater = ({ zones, nodes }: { zones: InterdictionZone[]; nodes: GraphNode[] }) => {
  const map = useMap();
  React.useEffect(() => {
    const points: [number, number][] = [];
    
    // Collect zone centers
    zones.forEach((zone) => {
      if (zone.center?.lat && zone.center?.lng) {
        points.push([zone.center.lat, zone.center.lng]);
      }
    });

    // Collect node coordinates
    nodes.forEach((node) => {
      if (node.metadata?.lat && node.metadata?.lng) {
        points.push([node.metadata.lat, node.metadata.lng]);
      }
    });

    if (points.length > 0) {
      const bounds = L.latLngBounds(points);
      map.flyToBounds(bounds, { padding: [60, 60], maxZoom: 12, duration: 1.5 });
    }
  }, [zones, nodes, map]);
  return null;
};

export function Heatmap() {
  const navigate = useNavigate();
  const [zones, setZones] = useState<InterdictionZone[]>([]);
  const [graphNodes, setGraphNodes] = useState<GraphNode[]>([]);
  const [isPredicting, setIsPredicting] = useState<boolean>(false);
  const [dispatchStatus, setDispatchStatus] = useState<string | null>(null);

  // Hit the FastAPI Intelligence Engine
  const runPrediction = async () => {
    setIsPredicting(true);
    setDispatchStatus(null);
    try {
      const endpoints = [
        'http://localhost:8001/api/engine/run-intelligence',
        'http://localhost:8000/api/engine/run-intelligence',
        '/api/engine/run-intelligence'
      ];
      
      let res: Response | null = null;
      for (const url of endpoints) {
        try {
          const r = await fetch(url, { method: 'POST' });
          if (r.ok) {
            res = r;
            break;
          }
        } catch {
          // try next
        }
      }

      if (res && res.ok) {
        const data = await res.json();
        setZones(data.interdiction_zones || []);
        if (data.graph && Array.isArray(data.graph.nodes)) {
          setGraphNodes(data.graph.nodes);
        }
      }
    } catch (error) {
      console.error("Failed to run prediction pipeline:", error);
    } finally {
      setIsPredicting(false);
    }
  };

  // Mock "Last-Mile" Dispatch Action
  const dispatchPatrol = (zoneId: string) => {
    setDispatchStatus(`TRANSMITTING SECURE COORDINATES FOR ${zoneId}...`);
    setTimeout(() => {
      setDispatchStatus(`SUCCESS: Coordinates pushed to nearest patrol unit for ${zoneId}. ETA: 4 mins.`);
      setTimeout(() => setDispatchStatus(null), 4000);
    }, 1500);
  };

  // Helper to resolve node coordinates (database metadata or synthetic Pan-India defaults)
  const getNodeCoordinates = (node: GraphNode): [number, number] | null => {
    if (node.metadata?.lat && node.metadata?.lng) {
      return [Number(node.metadata.lat), Number(node.metadata.lng)];
    }
    // Pan-India synthetic location maps for demo visualization
    const locMap: Record<string, [number, number]> = {
      'n_atm_104': [16.5062, 80.6480],
      'n_atm_221': [16.5044, 80.6558],
      'ATM_BENZ_1': [16.4971, 80.6516],
      'ATM_BENZ_2': [16.4975, 80.6650],
      'ATM_PATAMATA_1': [16.5020, 80.6580],
      'ATM_MG_ROAD_1': [16.5060, 80.6490],
      'n_mule_1': [17.4435, 78.3772], // Hyderabad
      'n_mule_2': [19.0650, 72.8653], // Mumbai
      'M883': [12.9279, 77.6271],     // Bengaluru
      'n_victim_1': [28.6304, 77.2177] // New Delhi
    };
    return locMap[node.id] || null;
  };

  return (
    <div className="relative w-full h-screen bg-[#0F1210] font-sans overflow-hidden text-gray-200">
      
      {/* 1. Tactical Action Overlay & Dashboard Shortcut */}
      <div className="absolute top-6 left-1/2 -translate-x-1/2 z-[1000] w-11/12 max-w-5xl bg-[#0F1210]/90 backdrop-blur-xl border border-[#48D878]/30 rounded-lg p-4 flex justify-between items-center shadow-[0_0_25px_rgba(72,216,120,0.15)]">
        <div className="flex gap-4 items-center">
          <div className="flex flex-col">
            <span className="text-[9px] uppercase tracking-widest text-gray-400">Coverage Scope</span>
            <span className="text-sm font-semibold text-white">Pan-India Monitored Network</span>
          </div>
          <div className="w-px h-8 bg-white/10 mx-1" />
          <div className="flex flex-col">
            <span className="text-[9px] uppercase tracking-widest text-gray-400">Active Nodes</span>
            <span className="text-sm font-semibold text-emerald-400">{graphNodes.length || '6 Live'} Nodes</span>
          </div>
          <div className="w-px h-8 bg-white/10 mx-1" />
          <div className="flex flex-col">
            <span className="text-[9px] uppercase tracking-widest text-gray-400">Threat Hotspots</span>
            <span className="text-sm font-semibold text-red-400">{zones.length} Critical Zones</span>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate('/graph')}
            className="px-5 py-2.5 bg-blue-500/15 hover:bg-blue-500/25 text-blue-400 font-mono text-xs font-bold rounded-md border border-blue-500/60 shadow-[0_0_20px_rgba(59,130,246,0.25)] transition-all uppercase tracking-widest cursor-pointer"
          >
            GRAPH WORKSPACE
          </button>
          <button 
            onClick={runPrediction}
            disabled={isPredicting}
            className="px-6 py-2.5 bg-[#48D878]/15 hover:bg-[#48D878]/25 text-[#48D878] font-mono text-xs font-bold rounded-md border border-[#48D878]/60 shadow-[0_0_20px_rgba(72,216,120,0.25)] transition-all disabled:opacity-50 tracking-widest uppercase flex items-center gap-2 cursor-pointer"
          >
            {isPredicting ? (
              <>
                <div className="w-3.5 h-3.5 border-2 border-[#48D878]/30 border-t-[#48D878] rounded-full animate-spin" />
                <span className="font-mono text-xs font-bold tracking-widest">RUNNING ML PIPELINE...</span>
              </>
            ) : (
              <span className="font-mono text-xs font-bold tracking-widest">RUN LIVE ML PREDICTION</span>
            )}
          </button>
        </div>
      </div>

      {/* 2. GIS Map Canvas */}
      <MapContainer 
        center={[22.5937, 78.9629]} // Center of India (Madhya Pradesh)
        zoom={5}                    // Subcontinent scale view
        className="w-full h-full z-0"
        zoomControl={false}
      >
        <TileLayer
          url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
          attribution='&copy; Esri &mdash; Source: Esri, Maxar, Earthstar Geographics, and the GIS User Community'
        />
        
        <MapUpdater zones={zones} nodes={graphNodes} />

        {/* 3. Render DBSCAN Bounding Boxes */}
        {zones.map((zone) => {
          const bounds: [number, number][] = [
            [zone.bounding_box.south, zone.bounding_box.west],
            [zone.bounding_box.north, zone.bounding_box.east]
          ];

          return (
            <Rectangle 
              key={zone.zone_id} 
              bounds={bounds}
              pathOptions={{ 
                color: '#ef4444', 
                fillColor: '#ef4444', 
                fillOpacity: 0.25, 
                weight: 2, 
                dashArray: '5 5' 
              }}
            >
              <Popup className="tactical-popup">
                <div className="bg-[#0F1210] p-3 -m-3 text-gray-200 min-w-[240px] rounded border border-red-500/40">
                  <div className="flex justify-between items-center mb-1">
                    <span className="text-[10px] font-bold text-red-500 tracking-widest uppercase">
                      {zone.zone_id}
                    </span>
                    {zone.priority_weight && (
                      <span className="text-[9px] px-1.5 py-0.5 bg-red-500/20 text-red-400 font-mono rounded">
                        Priority Weight: {zone.priority_weight}
                      </span>
                    )}
                  </div>
                  <div className="text-xs text-gray-400 mb-3 border-b border-white/10 pb-2">
                    Corroborated Target ATMs: {zone.target_nodes.length}
                  </div>
                  <button 
                    onClick={() => dispatchPatrol(zone.zone_id)}
                    className="w-full py-2 bg-blue-500/10 hover:bg-blue-500/20 text-blue-400 font-bold text-[10px] uppercase tracking-widest rounded border border-blue-500/40 transition-colors cursor-pointer"
                  >
                    Push to Patrol Unit
                  </button>
                </div>
              </Popup>
            </Rectangle>
          );
        })}

        {/* 4. Render Active Graph Nodes / Markers on the GIS Map */}
        {graphNodes.map((node) => {
          const coords = getNodeCoordinates(node);
          if (!coords) return null;

          const nType = String(node.type || '').toUpperCase();
          const riskScore = Number(node.riskScore || 0);
          
          let color = '#48D878'; // Green for low risk
          if (nType === 'VICTIM' || riskScore >= 80) color = '#ef4444'; // Red
          else if (nType === 'MULE' || riskScore >= 50) color = '#f97316'; // Orange

          const pinLabel = `${nType}: ${node.id} (${riskScore.toFixed(1)})`;
          const customIcon = createCustomPin(color, pinLabel);

          return (
            <React.Fragment key={`node-map-${node.id}`}>
              {/* Outer pulsing ring for high risk nodes */}
              {riskScore >= 80 && (
                <CircleMarker
                  center={coords}
                  radius={18}
                  pathOptions={{
                    color: color,
                    fillColor: color,
                    fillOpacity: 0.15,
                    weight: 1,
                    dashArray: '3 3'
                  }}
                />
              )}

              {/* Pin Marker */}
              <Marker position={coords} icon={customIcon}>
                <Popup className="tactical-popup">
                  <div className="bg-[#0F1210] p-3 -m-3 text-gray-200 min-w-[220px] rounded border border-emerald-500/40">
                    <div className="flex justify-between items-center mb-1">
                      <span className="text-[10px] font-bold tracking-widest uppercase text-emerald-400">
                        {nType} NODE
                      </span>
                      <span className="text-[10px] font-bold font-mono px-1.5 py-0.5 rounded bg-white/10 text-white">
                        {riskScore.toFixed(1)}/100
                      </span>
                    </div>
                    <div className="text-xs font-semibold text-white mb-1">
                      {node.metadata?.label || node.metadata?.name || node.id}
                    </div>
                    {node.metadata?.evidence_chain && node.metadata.evidence_chain.length > 0 && (
                      <div className="text-[9px] font-mono text-gray-400 mb-3 bg-black/50 p-1.5 rounded border border-white/5">
                        <span className="text-gray-500 block text-[8px] uppercase">Provenance Chain:</span>
                        {node.metadata.evidence_chain.join(' → ')}
                      </div>
                    )}
                    <button 
                      onClick={() => navigate('/graph')}
                      className="w-full py-1.5 bg-[#48D878]/10 hover:bg-[#48D878]/20 text-[#48D878] font-bold text-[10px] uppercase tracking-widest rounded border border-[#48D878]/40 transition-colors cursor-pointer"
                    >
                      Inspect in Graph Workspace
                    </button>
                  </div>
                </Popup>
              </Marker>
            </React.Fragment>
          );
        })}
      </MapContainer>

      {/* 5. Last-Mile Patrol Dispatch Toast Notification */}
      {dispatchStatus && (
        <div className="absolute bottom-10 right-10 z-[1000] bg-black/90 backdrop-blur-md border-l-4 border-blue-500 p-4 max-w-sm shadow-[0_0_25px_rgba(59,130,246,0.3)] animate-fade-in">
          <div className="flex items-center gap-3">
            <div className="w-2.5 h-2.5 bg-blue-500 rounded-full animate-pulse" />
            <span className="text-xs font-mono text-gray-200">
              {dispatchStatus}
            </span>
          </div>
        </div>
      )}
    </div>
  );
}

export default Heatmap;
