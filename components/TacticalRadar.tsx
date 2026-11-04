"use client";

import { useEffect, useRef, useState } from "react";

export interface HeliTarget {
  id: string;
  callsign: string;
  model: string;
  altitude: number; // in feet
  groundSpeed: number; // in knots
  bearing: number; // in degrees
  lat: number;
  lng: number;
  status: "EN ROUTE" | "APPROACH" | "HOVER" | "DEPARTING";
  origin: string;
  destination: string;
  etaMinutes: number;
  pilot: string;
  rotorRpm: number;
}

export interface VertiportNode {
  id: string;
  code: string;
  name: string;
  x: number; // relative 0-100%
  y: number; // relative 0-100%
  pads: number;
  availablePads: number;
}

interface TacticalRadarProps {
  targets: HeliTarget[];
  vertiports: VertiportNode[];
  selectedTargetId: string | null;
  onSelectTarget: (id: string | null) => void;
  activeCity: string;
}

export default function TacticalRadar({
  targets,
  vertiports,
  selectedTargetId,
  onSelectTarget,
  activeCity,
}: TacticalRadarProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const [zoomLevel, setZoomLevel] = useState<number>(1);
  const [showAirways, setShowAirways] = useState<boolean>(true);
  const [showRings, setShowRings] = useState<boolean>(true);
  const angleRef = useRef<number>(0);
  const animFrameRef = useRef<number | null>(null);

  const selectedTarget = targets.find((t) => t.id === selectedTargetId) || null;

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let width = (canvas.width = canvas.parentElement?.clientWidth || 800);
    let height = (canvas.height = canvas.parentElement?.clientHeight || 480);

    const handleResize = () => {
      if (!canvas || !canvas.parentElement) return;
      width = canvas.width = canvas.parentElement.clientWidth;
      height = canvas.height = canvas.parentElement.clientHeight;
    };
    window.addEventListener("resize", handleResize);

    const render = () => {
      // Fade out previous frame slightly for phosphor persistence trail
      ctx.fillStyle = "rgba(8, 10, 15, 0.22)";
      ctx.fillRect(0, 0, width, height);

      const centerX = width / 2;
      const centerY = height / 2;
      const maxRadius = (Math.min(width, height) / 2 - 20) * zoomLevel;

      // Draw Grid Crosshairs
      ctx.strokeStyle = "rgba(40, 50, 70, 0.4)";
      ctx.lineWidth = 1;

      ctx.beginPath();
      ctx.moveTo(centerX, 15);
      ctx.lineTo(centerX, height - 15);
      ctx.moveTo(15, centerY);
      ctx.lineTo(width - 15, centerY);
      ctx.stroke();

      // Diagonal index ticks
      ctx.beginPath();
      ctx.setLineDash([2, 6]);
      ctx.moveTo(centerX - maxRadius, centerY - maxRadius);
      ctx.lineTo(centerX + maxRadius, centerY + maxRadius);
      ctx.moveTo(centerX - maxRadius, centerY + maxRadius);
      ctx.lineTo(centerX + maxRadius, centerY - maxRadius);
      ctx.stroke();
      ctx.setLineDash([]);

      // Draw Range Rings (5nm, 10nm, 15nm)
      if (showRings) {
        const ringSteps = [0.33, 0.66, 1.0];
        const ringLabels = ["5 NM", "10 NM", "15 NM (TERMINAL)"];

        ringSteps.forEach((step, idx) => {
          const r = maxRadius * step;
          ctx.beginPath();
          ctx.arc(centerX, centerY, r, 0, Math.PI * 2);
          ctx.strokeStyle = idx === 2 ? "rgba(212, 255, 0, 0.35)" : "rgba(45, 55, 75, 0.7)";
          ctx.lineWidth = idx === 2 ? 1.5 : 1;
          ctx.stroke();

          // Distance label
          ctx.font = "9px 'JetBrains Mono', monospace";
          ctx.fillStyle = idx === 2 ? "#d4ff00" : "#5e6b7e";
          ctx.fillText(ringLabels[idx], centerX + 8, centerY - r + 12);
        });
      }

      // Draw Vector Airways between Vertiports
      if (showAirways && vertiports.length >= 2) {
        ctx.strokeStyle = "rgba(0, 240, 255, 0.18)";
        ctx.lineWidth = 1.2;
        ctx.setLineDash([4, 4]);

        for (let i = 0; i < vertiports.length - 1; i++) {
          const p1 = vertiports[i];
          const p2 = vertiports[i + 1];

          const x1 = centerX + ((p1.x - 50) / 50) * maxRadius * 0.85;
          const y1 = centerY + ((p1.y - 50) / 50) * maxRadius * 0.85;
          const x2 = centerX + ((p2.x - 50) / 50) * maxRadius * 0.85;
          const y2 = centerY + ((p2.y - 50) / 50) * maxRadius * 0.85;

          ctx.beginPath();
          ctx.moveTo(x1, y1);
          ctx.lineTo(x2, y2);
          ctx.stroke();
        }
        ctx.setLineDash([]);
      }

      // Draw Vertiport Nodes
      vertiports.forEach((vp) => {
        const vx = centerX + ((vp.x - 50) / 50) * maxRadius * 0.85;
        const vy = centerY + ((vp.y - 50) / 50) * maxRadius * 0.85;

        // Helipad circle
        ctx.beginPath();
        ctx.arc(vx, vy, 5, 0, Math.PI * 2);
        ctx.fillStyle = "#0c1017";
        ctx.fill();
        ctx.strokeStyle = "#00f0ff";
        ctx.lineWidth = 1.5;
        ctx.stroke();

        // Inner 'H' mark
        ctx.font = "bold 8px 'JetBrains Mono', monospace";
        ctx.fillStyle = "#00f0ff";
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.fillText("H", vx, vy);

        // Vertiport Label
        ctx.font = "10px 'JetBrains Mono', monospace";
        ctx.fillStyle = "#9da8b9";
        ctx.textAlign = "left";
        ctx.textBaseline = "top";
        ctx.fillText(`[${vp.code}] ${vp.name}`, vx + 8, vy - 6);
      });

      // Rotating Radar Beam
      angleRef.current = (angleRef.current + 0.015) % (Math.PI * 2);
      const sweepAngle = angleRef.current;

      const gradient = ctx.createRadialGradient(
        centerX,
        centerY,
        0,
        centerX,
        centerY,
        maxRadius
      );
      gradient.addColorStop(0, "rgba(212, 255, 0, 0.2)");
      gradient.addColorStop(1, "rgba(212, 255, 0, 0.01)");

      ctx.beginPath();
      ctx.moveTo(centerX, centerY);
      ctx.arc(
        centerX,
        centerY,
        maxRadius,
        sweepAngle - 0.28,
        sweepAngle,
        false
      );
      ctx.closePath();
      ctx.fillStyle = gradient;
      ctx.fill();

      // Sharp Beam Leading Edge
      ctx.beginPath();
      ctx.moveTo(centerX, centerY);
      ctx.lineTo(
        centerX + Math.cos(sweepAngle) * maxRadius,
        centerY + Math.sin(sweepAngle) * maxRadius
      );
      ctx.strokeStyle = "rgba(212, 255, 0, 0.85)";
      ctx.lineWidth = 1.5;
      ctx.stroke();

      // Draw Helicopter Targets
      targets.forEach((target, index) => {
        // Position on radar
        const tAngle = (index * (Math.PI / 2.5) + (angleRef.current * 0.1)) % (Math.PI * 2);
        const distRatio = 0.28 + ((index % 4) * 0.18);
        const tx = centerX + Math.cos(tAngle) * maxRadius * distRatio;
        const ty = centerY + Math.sin(tAngle) * maxRadius * distRatio;

        const isSelected = target.id === selectedTargetId;

        // Draw Target Blip
        ctx.beginPath();
        ctx.arc(tx, ty, isSelected ? 6 : 4, 0, Math.PI * 2);
        ctx.fillStyle = isSelected ? "#d4ff00" : "#d4ff00";
        ctx.fill();

        if (isSelected) {
          // Tactical selection ring
          ctx.beginPath();
          ctx.arc(tx, ty, 14, 0, Math.PI * 2);
          ctx.strokeStyle = "#d4ff00";
          ctx.lineWidth = 1.5;
          ctx.stroke();

          // Selection brackets
          ctx.strokeStyle = "#ffffff";
          ctx.lineWidth = 1;
          const s = 18;
          ctx.strokeRect(tx - s / 2, ty - s / 2, s, s);
        }

        // Velocity vector line
        const vectorLen = (target.groundSpeed / 160) * 22;
        const headingRad = (target.bearing * Math.PI) / 180;
        ctx.beginPath();
        ctx.moveTo(tx, ty);
        ctx.lineTo(
          tx + Math.cos(headingRad) * vectorLen,
          ty + Math.sin(headingRad) * vectorLen
        );
        ctx.strokeStyle = isSelected ? "#d4ff00" : "rgba(212, 255, 0, 0.6)";
        ctx.lineWidth = 1.5;
        ctx.stroke();

        // Target Transponder Tag
        ctx.font = "bold 9px 'JetBrains Mono', monospace";
        ctx.fillStyle = isSelected ? "#d4ff00" : "#e2e8f0";
        ctx.textAlign = "left";
        ctx.textBaseline = "middle";
        ctx.fillText(target.callsign, tx + 10, ty - 6);

        ctx.font = "8px 'JetBrains Mono', monospace";
        ctx.fillStyle = "#8a96a8";
        ctx.fillText(`${target.altitude}FT · ${target.groundSpeed}KT`, tx + 10, ty + 6);
      });

      animFrameRef.current = requestAnimationFrame(render);
    };

    render();

    return () => {
      window.removeEventListener("resize", handleResize);
      if (animFrameRef.current) {
        cancelAnimationFrame(animFrameRef.current);
      }
    };
  }, [targets, vertiports, selectedTargetId, zoomLevel, showAirways, showRings]);

  return (
    <div className="radar-stage">
      <canvas
        ref={canvasRef}
        className="radar-canvas"
        onClick={() => {
          // Cycle selection through targets on canvas click
          const nextIndex =
            targets.findIndex((t) => t.id === selectedTargetId) + 1;
          if (nextIndex < targets.length) {
            onSelectTarget(targets[nextIndex].id);
          } else {
            onSelectTarget(targets[0]?.id || null);
          }
        }}
      />

      <div className="radar-hud-overlay">
        <div className="hud-top-bar">
          <div className="hud-tag">
            <span>AIRSPACE: </span>
            <strong>{activeCity.toUpperCase()} SECTOR</strong>
            <span style={{ marginLeft: 10, color: "#d4ff00" }}>● LIVE FEED</span>
          </div>
          <div className="hud-tag">
            <span>QNH: </span>
            <strong>29.92 INHG</strong>
            <span style={{ marginLeft: 8 }}>VIS: </span>
            <strong>10+ SM</strong>
          </div>
        </div>

        {selectedTarget && (
          <div className="target-telemetry-hud">
            <div
              style={{
                fontFamily: "var(--font-mono)",
                fontSize: 10,
                color: "var(--lime)",
                fontWeight: 800,
                letterSpacing: 1,
                marginBottom: 6,
                display: "flex",
                justifyContent: "space-between",
              }}
            >
              <span>[TARGET ACQUIRED]</span>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onSelectTarget(null);
                }}
                style={{
                  background: "transparent",
                  border: "none",
                  color: "#9da8b9",
                  cursor: "pointer",
                  fontFamily: "var(--font-mono)",
                  fontSize: 11,
                }}
              >
                ✕
              </button>
            </div>
            <div className="telemetry-row">
              <span>CALLSIGN</span>
              <strong className="lime">{selectedTarget.callsign}</strong>
            </div>
            <div className="telemetry-row">
              <span>AIRCRAFT</span>
              <strong>{selectedTarget.model}</strong>
            </div>
            <div className="telemetry-row">
              <span>ALTITUDE</span>
              <strong className="lime">{selectedTarget.altitude} FT</strong>
            </div>
            <div className="telemetry-row">
              <span>GROUND SPEED</span>
              <strong>{selectedTarget.groundSpeed} KTS</strong>
            </div>
            <div className="telemetry-row">
              <span>VECTOR / BEARING</span>
              <strong>{selectedTarget.bearing}° TRUE</strong>
            </div>
            <div className="telemetry-row">
              <span>ROUTE</span>
              <strong>
                {selectedTarget.origin} → {selectedTarget.destination}
              </strong>
            </div>
            <div className="telemetry-row">
              <span>ETA</span>
              <strong className="lime">{selectedTarget.etaMinutes} MIN</strong>
            </div>
            <div className="telemetry-row">
              <span>COMMAND PILOT</span>
              <strong>{selectedTarget.pilot}</strong>
            </div>
            <div className="telemetry-row">
              <span>ROTOR RPM</span>
              <strong className="lime">{selectedTarget.rotorRpm} RPM</strong>
            </div>
          </div>
        )}

        <div className="hud-bottom-bar">
          <div className="radar-controls">
            <button
              className={`radar-btn ${zoomLevel === 0.8 ? "active" : ""}`}
              onClick={() => setZoomLevel(0.8)}
              title="Wide Airspace (25 NM)"
            >
              25 NM
            </button>
            <button
              className={`radar-btn ${zoomLevel === 1 ? "active" : ""}`}
              onClick={() => setZoomLevel(1)}
              title="Terminal Radar (15 NM)"
            >
              15 NM
            </button>
            <button
              className={`radar-btn ${zoomLevel === 1.3 ? "active" : ""}`}
              onClick={() => setZoomLevel(1.3)}
              title="Inner Corridor (8 NM)"
            >
              8 NM
            </button>
          </div>

          <div className="radar-controls">
            <button
              className={`radar-btn ${showAirways ? "active" : ""}`}
              onClick={() => setShowAirways(!showAirways)}
            >
              AIRWAYS
            </button>
            <button
              className={`radar-btn ${showRings ? "active" : ""}`}
              onClick={() => setShowRings(!showRings)}
            >
              RINGS
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

