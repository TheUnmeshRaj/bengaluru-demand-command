"use client";

import { useEffect, useState } from "react";
import { CircleMarker, MapContainer, Popup, TileLayer, useMap } from "react-leaflet";
import "leaflet/dist/leaflet.css";

type Zone = { id: string; name: string; latest: { prediction15: number; demandLast5: number; weather: string } };
type Coordinates = Record<string, { lat: number; lng: number }>;

function MapViewport({ selected }: { selected?: { lat: number; lng: number } }) {
  const map = useMap();
  useEffect(() => { if (selected) map.flyTo([selected.lat, selected.lng], 11, { duration: 0.8 }); }, [map, selected]);
  return null;
}

export default function DemandMap({ zones, coordinatesUrl, selectedZone, onSelect }: { zones: Zone[]; coordinatesUrl: string; selectedZone: string; onSelect: (id: string) => void }) {
  const [coordinates, setCoordinates] = useState<Coordinates>({});
  useEffect(() => { fetch(coordinatesUrl).then((response) => response.json()).then(setCoordinates); }, [coordinatesUrl]);
  const max = Math.max(...zones.map((zone) => zone.latest.prediction15), 1);
  const selected = coordinates[selectedZone];
  return <div className="map-wrap"><MapContainer center={[12.9716, 77.5946]} zoom={10.8} scrollWheelZoom className="leaflet-map"><TileLayer attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors' url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" /><MapViewport selected={selected} />{zones.map((zone) => { const point = coordinates[zone.id]; if (!point) return null; const intensity = zone.latest.prediction15 / max; const color = intensity > 0.72 ? "#f05b61" : intensity > 0.42 ? "#f6a64b" : "#62b8a7"; return <CircleMarker key={zone.id} center={[point.lat, point.lng]} radius={zone.id === selectedZone ? 14 : 7 + intensity * 8} pathOptions={{ color, fillColor: color, fillOpacity: zone.id === selectedZone ? 0.95 : 0.7, weight: zone.id === selectedZone ? 3 : 1 }} eventHandlers={{ click: () => onSelect(zone.id) }}><Popup><strong>{zone.name}</strong><br />{Math.round(zone.latest.prediction15)} predicted requests<br /><small>Next 15 minutes · {zone.latest.weather}</small></Popup></CircleMarker>; })}</MapContainer><div className="map-overlay"><span>⌖</span> Click a zone to brief drivers</div></div>;
}
