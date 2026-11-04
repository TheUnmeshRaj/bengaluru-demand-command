"use client";

import { useEffect, useRef, useState } from "react";

export interface ZoneNode {
  id: string;
  name: string;
  kannadaName: string;
  x: number; // percentage
  y: number; // percentage
  cabsAvailable: number;
  avgWaitMins: number;
  demandLevel: "normal" | "active" | "high";
}

export const BENGALURU_ZONES: ZoneNode[] = [
  { id: "Z30", name: "Indiranagar", kannadaName: "ಇಂದಿರಾನಗರ", x: 62, y: 46, cabsAvailable: 28, avgWaitMins: 2, demandLevel: "high" },
  { id: "Z31", name: "Koramangala", kannadaName: "ಕೋರಮಂಗಲ", x: 58, y: 64, cabsAvailable: 34, avgWaitMins: 3, demandLevel: "high" },
  { id: "Z32", name: "MG Road / CBD", kannadaName: "ಎಂ ಜಿ ರಸ್ತೆ", x: 50, y: 44, cabsAvailable: 22, avgWaitMins: 2, demandLevel: "active" },
  { id: "Z01", name: "Whitefield", kannadaName: "ವೈಟ್‌ಫೀಲ್ಡ್", x: 86, y: 42, cabsAvailable: 38, avgWaitMins: 4, demandLevel: "active" },
  { id: "Z13", name: "HSR Layout", kannadaName: "ಹೆಚ್ ಎಸ್ ಆರ್", x: 66, y: 72, cabsAvailable: 26, avgWaitMins: 3, demandLevel: "active" },
  { id: "Z02", name: "Electronic City", kannadaName: "ಎಲೆಕ್ಟ್ರಾನಿಕ್ ಸಿಟಿ", x: 68, y: 90, cabsAvailable: 31, avgWaitMins: 4, demandLevel: "normal" },
  { id: "Z46", name: "KIAL Airport", kannadaName: "ಕೆಂಪೇಗೌಡ ವಿಮಾನ ನಿಲ್ದಾಣ", x: 74, y: 12, cabsAvailable: 52, avgWaitMins: 3, demandLevel: "high" },
  { id: "Z38", name: "Majestic (KBS)", kannadaName: "ಮೆಜೆಸ್ಟಿಕ್", x: 42, y: 48, cabsAvailable: 41, avgWaitMins: 2, demandLevel: "high" },
  { id: "Z10", name: "Jayanagar", kannadaName: "ಜಯನಗರ", x: 46, y: 68, cabsAvailable: 19, avgWaitMins: 3, demandLevel: "normal" },
];

interface CityRideMapProps {
  selectedPickup: string;
  selectedDrop: string;
  onSelectZone: (zoneName: string) => void;
}

export default function CityRideMap({
  selectedPickup,
  selectedDrop,
  onSelectZone,
}: CityRideMapProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const animFrameRef = useRef<number | null>(null);
  const [activeHoverZone, setActiveHoverZone] = useState<ZoneNode | null>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let width = (canvas.width = canvas.parentElement?.clientWidth || 700);
    let height = (canvas.height = canvas.parentElement?.clientHeight || 480);

    const handleResize = () => {
      if (!canvas || !canvas.parentElement) return;
      width = canvas.width = canvas.parentElement.clientWidth;
      height = canvas.height = canvas.parentElement.clientHeight;
    };
    window.addEventListener("resize", handleResize);

    // Mock Cab positions that gently glide along corridors
    const cabs = Array.from({ length: 24 }).map((_, i) => ({
      x: 30 + Math.random() * 55,
      y: 20 + Math.random() * 65,
      vx: (Math.random() - 0.5) * 0.08,
      vy: (Math.random() - 0.5) * 0.08,
      type: i % 4 === 0 ? "ev" : i % 3 === 0 ? "prime" : "mini",
    }));

    const render = () => {
      ctx.fillStyle = "#0c0d12";
      ctx.fillRect(0, 0, width, height);

      // Clean Swiss grid overlay
      ctx.strokeStyle = "rgba(255, 255, 255, 0.03)";
      ctx.lineWidth = 1;
      const step = 32;
      for (let x = 0; x < width; x += step) {
        ctx.beginPath();
        ctx.moveTo(x, 0);
        ctx.lineTo(x, height);
        ctx.stroke();
      }
      for (let y = 0; y < height; y += step) {
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(width, y);
        ctx.stroke();
      }

      // Draw Major Arterial Corridors (ORR, Hosur Road, Airport Expressway)
      ctx.strokeStyle = "rgba(255, 255, 255, 0.1)";
      ctx.lineWidth = 1.5;

      // Bellary Road to Airport
      ctx.beginPath();
      ctx.moveTo((width * 46) / 100, (height * 44) / 100);
      ctx.lineTo((width * 74) / 100, (height * 12) / 100);
      ctx.stroke();

      // Outer Ring Road (ORR) Loop
      ctx.beginPath();
      ctx.moveTo((width * 58) / 100, (height * 64) / 100);
      ctx.lineTo((width * 66) / 100, (height * 72) / 100);
      ctx.lineTo((width * 86) / 100, (height * 42) / 100);
      ctx.stroke();

      // Hosur Road to Electronic City
      ctx.beginPath();
      ctx.moveTo((width * 58) / 100, (height * 64) / 100);
      ctx.lineTo((width * 68) / 100, (height * 90) / 100);
      ctx.stroke();

      // Draw Selected Route connection if pickup & drop match known zones
      const pickupNode = BENGALURU_ZONES.find((z) => z.name === selectedPickup);
      const dropNode = BENGALURU_ZONES.find((z) => z.name === selectedDrop);

      if (pickupNode && dropNode && pickupNode.id !== dropNode.id) {
        const px = (width * pickupNode.x) / 100;
        const py = (height * pickupNode.y) / 100;
        const dx = (width * dropNode.x) / 100;
        const dy = (height * dropNode.y) / 100;

        ctx.strokeStyle = "#d4ff00";
        ctx.lineWidth = 2.5;
        ctx.beginPath();
        ctx.moveTo(px, py);
        ctx.lineTo(dx, dy);
        ctx.stroke();

        // Pulsing line trace
        ctx.strokeStyle = "rgba(212, 255, 0, 0.3)";
        ctx.lineWidth = 6;
        ctx.stroke();
      }

      // Draw active moving cabs
      cabs.forEach((cab) => {
        cab.x += cab.vx;
        cab.y += cab.vy;
        if (cab.x < 15 || cab.x > 90) cab.vx *= -1;
        if (cab.y < 10 || cab.y > 90) cab.vy *= -1;

        const cx = (width * cab.x) / 100;
        const cy = (height * cab.y) / 100;

        ctx.beginPath();
        ctx.arc(cx, cy, 2.5, 0, Math.PI * 2);
        ctx.fillStyle = cab.type === "ev" ? "#10b981" : "#d4ff00";
        ctx.fill();
      });

      // Draw City Zones
      BENGALURU_ZONES.forEach((zone) => {
        const zx = (width * zone.x) / 100;
        const zy = (height * zone.y) / 100;
        const isPickup = zone.name === selectedPickup;
        const isDrop = zone.name === selectedDrop;

        // Base node
        ctx.beginPath();
        ctx.arc(zx, zy, isPickup || isDrop ? 7 : 4, 0, Math.PI * 2);
        ctx.fillStyle = isPickup ? "#d4ff00" : isDrop ? "#ffffff" : "#1e222d";
        ctx.fill();
        ctx.strokeStyle = isPickup || isDrop ? "#000000" : "#434d61";
        ctx.lineWidth = 1.5;
        ctx.stroke();

        // Zone label
        ctx.font = isPickup || isDrop ? "bold 11px 'Plus Jakarta Sans', sans-serif" : "10px 'Plus Jakarta Sans', sans-serif";
        ctx.fillStyle = isPickup ? "#d4ff00" : isDrop ? "#ffffff" : "#9aa2b2";
        ctx.fillText(zone.name, zx + 10, zy + 3);

        ctx.font = "8px 'JetBrains Mono', monospace";
        ctx.fillStyle = "#5d6677";
        ctx.fillText(`${zone.cabsAvailable} CABS · ${zone.avgWaitMins}M`, zx + 10, zy + 13);
      });

      animFrameRef.current = requestAnimationFrame(render);
    };

    render();

    return () => {
      window.removeEventListener("resize", handleResize);
      if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current);
    };
  }, [selectedPickup, selectedDrop]);

  return (
    <div className="city-map-wrapper">
      <canvas
        ref={canvasRef}
        className="city-map-canvas"
        onClick={(e) => {
          const rect = e.currentTarget.getBoundingClientRect();
          const clickX = ((e.clientX - rect.left) / rect.width) * 100;
          const clickY = ((e.clientY - rect.top) / rect.height) * 100;

          // Find closest zone within tolerance
          let closest: ZoneNode | null = null;
          let minDist = 12; // percent tolerance
          BENGALURU_ZONES.forEach((z) => {
            const dist = Math.hypot(z.x - clickX, z.y - clickY);
            if (dist < minDist) {
              minDist = dist;
              closest = z;
            }
          });

          if (closest) {
            onSelectZone((closest as ZoneNode).name);
          }
        }}
      />

      <div className="map-hud">
        <div className="map-hud-pill">
          <span>SPATIAL COVERAGE: </span>
          <strong>BENGALURU METROPOLITAN (52 ZONES)</strong>
        </div>
        <div className="map-hud-pill">
          <span>FLEET READY: </span>
          <strong>312 CABS ON ROAD · 2.8 MIN MEDIAN ARRIVAL</strong>
        </div>
      </div>
    </div>
  );
}

