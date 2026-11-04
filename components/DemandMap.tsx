"use client";

import { useEffect, useState } from "react";
import { CircleMarker, MapContainer, Marker, Popup, TileLayer, useMap } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";

type Zone = { id: string; name: string; latest: { prediction15: number; demandLast5: number; weather: string } };
type Coordinates = Record<string, { lat: number; lng: number }>;
type Point = { lat: number; lng: number };

const mockDrivers: Array<Point & { name: string; status: string }> = [
  { lat: 12.9687, lng: 77.6412, name: "Driver A · simulated", status: "Moving to hotspot" },
  { lat: 12.9824, lng: 77.6128, name: "Driver B · simulated", status: "Available" },
  { lat: 12.9396, lng: 77.6251, name: "Driver C · simulated", status: "Available" },
  { lat: 13.0068, lng: 77.5705, name: "Driver D · simulated", status: "Moving to hotspot" },
  { lat: 12.9161, lng: 77.5994, name: "Driver E · simulated", status: "Available" },
];

const markerIcon = (className: string) => L.divIcon({
  className: "",
  html: `<span class="map-marker ${className}"></span>`,
  iconSize: [18, 18],
  iconAnchor: [9, 9],
});

function MapViewport({ selected, userLocation }: { selected?: Point; userLocation?: Point }) {
  const map = useMap();
  useEffect(() => { if (selected) map.flyTo([selected.lat, selected.lng], 11, { duration: 0.8 }); }, [map, selected]);
  useEffect(() => { if (userLocation) map.flyTo([userLocation.lat, userLocation.lng], 13, { duration: 0.8 }); }, [map, userLocation]);
  return null;
}

export default function DemandMap({ zones, coordinatesUrl, selectedZone, onSelect }: { zones: Zone[]; coordinatesUrl: string; selectedZone: string; onSelect: (id: string) => void }) {
  const [coordinates, setCoordinates] = useState<Coordinates>({});
  const [userLocation, setUserLocation] = useState<Point | null>(null);
  const [locationMessage, setLocationMessage] = useState("Find my location");
  useEffect(() => { fetch(coordinatesUrl).then((response) => response.json()).then(setCoordinates); }, [coordinatesUrl]);
  const max = Math.max(...zones.map((zone) => zone.latest.prediction15), 1);
  const selected = coordinates[selectedZone];
  const findLocation = () => {
    if (!navigator.geolocation) { setLocationMessage("Location not available"); return; }
    setLocationMessage("Finding you…");
    navigator.geolocation.getCurrentPosition(
      (position) => { setUserLocation({ lat: position.coords.latitude, lng: position.coords.longitude }); setLocationMessage("My location"); },
      () => setLocationMessage("Location blocked"),
      { enableHighAccuracy: true, timeout: 10000 },
    );
  };
  return <div className="map-wrap"><MapContainer center={[12.9716, 77.5946]} zoom={10.8} scrollWheelZoom className="leaflet-map"><TileLayer attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors' url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" /><MapViewport selected={selected} userLocation={userLocation ?? undefined} />{zones.map((zone) => { const point = coordinates[zone.id]; if (!point) return null; const intensity = zone.latest.prediction15 / max; const color = intensity > 0.72 ? "#f05b61" : intensity > 0.42 ? "#f6a64b" : "#62b8a7"; return <CircleMarker key={zone.id} center={[point.lat, point.lng]} radius={zone.id === selectedZone ? 14 : 7 + intensity * 8} pathOptions={{ color, fillColor: color, fillOpacity: zone.id === selectedZone ? 0.95 : 0.7, weight: zone.id === selectedZone ? 3 : 1 }} eventHandlers={{ click: () => onSelect(zone.id) }}><Popup><strong>{zone.name}</strong><br />{Math.round(zone.latest.prediction15)} predicted requests<br /><small>Next 15 minutes · {zone.latest.weather}</small></Popup></CircleMarker>; })}{mockDrivers.map((driver) => <Marker key={driver.name} position={[driver.lat, driver.lng]} icon={markerIcon(driver.status === "Available" ? "driver-available" : "driver-moving")}><Popup><strong>{driver.name}</strong><br /><small>{driver.status}<br />Mock location for demo</small></Popup></Marker>)}{userLocation && <Marker position={[userLocation.lat, userLocation.lng]} icon={markerIcon("driver-me")}><Popup><strong>You are here</strong><br /><small>Your live location</small></Popup></Marker>}</MapContainer><button className="location-button" onClick={findLocation}>⌖ {locationMessage}</button><div className="map-overlay"><span>●</span> Hotspots · <span className="driver-key">●</span> Simulated drivers</div></div>;
}
