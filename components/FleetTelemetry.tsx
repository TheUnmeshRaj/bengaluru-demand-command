"use client";

import { useState } from "react";

export interface AircraftSpec {
  id: string;
  name: string;
  type: string;
  tailNumber: string;
  engines: string;
  cruiseSpeedKts: number;
  rangeNm: number;
  capacity: string;
  acousticLevelDba: number;
  currentRpm: number;
  torquePercent: number;
  fuelOrBatteryPercent: number;
  flightHours: number;
  status: "MISSION READY" | "AIRBORNE" | "PRE-FLIGHT CHECK";
}

const FLEET_DATA: AircraftSpec[] = [
  {
    id: "s76d",
    name: "Sikorsky S-76D VIP",
    type: "TWIN-TURBINE EXECUTIVE",
    tailNumber: "N760-RH",
    engines: "2x Pratt & Whitney PW210S",
    cruiseSpeedKts: 155,
    rangeNm: 412,
    capacity: "6 VIP Club Seats",
    acousticLevelDba: 64,
    currentRpm: 394,
    torquePercent: 86,
    fuelOrBatteryPercent: 92,
    flightHours: 1420,
    status: "MISSION READY",
  },
  {
    id: "ach145",
    name: "Airbus ACH145 Hermes",
    type: "FENESTRON SHROUDED",
    tailNumber: "N145-RH",
    engines: "2x Safran Arriel 2E",
    cruiseSpeedKts: 140,
    rangeNm: 370,
    capacity: "8 Executive Seats",
    acousticLevelDba: 61,
    currentRpm: 382,
    torquePercent: 82,
    fuelOrBatteryPercent: 88,
    flightHours: 890,
    status: "AIRBORNE",
  },
  {
    id: "bell429",
    name: "Bell 429 GlobalRanger",
    type: "TWIN-ENGINE LIGHT",
    tailNumber: "N429-RH",
    engines: "2x Pratt & Whitney PW207D1",
    cruiseSpeedKts: 150,
    rangeNm: 390,
    capacity: "6 Club Seats",
    acousticLevelDba: 67,
    currentRpm: 388,
    torquePercent: 79,
    fuelOrBatteryPercent: 95,
    flightHours: 640,
    status: "MISSION READY",
  },
  {
    id: "midnight",
    name: "Archer Midnight eVTOL",
    type: "100% ELECTRIC WHISPER-ROTOR",
    tailNumber: "EV900-RH",
    engines: "12x Direct-Drive Dual Electric",
    cruiseSpeedKts: 130,
    rangeNm: 100,
    capacity: "4 VIP Seats",
    acousticLevelDba: 45,
    currentRpm: 420,
    torquePercent: 74,
    fuelOrBatteryPercent: 98,
    flightHours: 310,
    status: "MISSION READY",
  },
];

export default function FleetTelemetry() {
  const [selectedAircraftId, setSelectedAircraftId] = useState<string>("s76d");

  const aircraft =
    FLEET_DATA.find((a) => a.id === selectedAircraftId) || FLEET_DATA[0];

  return (
    <div className="bento-body">
      {/* Fleet Mini Switcher */}
      <div className="fleet-scroll-grid">
        {FLEET_DATA.map((item) => (
          <div
            key={item.id}
            className={`fleet-mini-card ${
              item.id === selectedAircraftId ? "active" : ""
            }`}
            onClick={() => setSelectedAircraftId(item.id)}
          >
            <div className="fleet-type-tag">[{item.type}]</div>
            <div className="fleet-model">{item.name}</div>
            <div className="fleet-tail">{item.tailNumber}</div>
            <div className="fleet-metrics-strip">
              <span>{item.cruiseSpeedKts} KTS</span>
              <span style={{ color: "var(--lime)" }}>
                {item.fuelOrBatteryPercent}% {item.id === "midnight" ? "BATT" : "FUEL"}
              </span>
            </div>
          </div>
        ))}
      </div>

      {/* Selected Aircraft Cockpit Visual & Telemetry */}
      <div className="aircraft-cockpit-view">
        <div className="aircraft-visual">
          <div className="aircraft-svg-wrap">
            {/* Spinning Rotor Graphic */}
            <svg
              viewBox="0 0 100 100"
              style={{
                width: "100%",
                height: "100%",
                animation: "rotor-spin 1.2s linear infinite",
              }}
            >
              <circle
                cx="50"
                cy="50"
                r="45"
                fill="none"
                stroke="rgba(212, 255, 0, 0.15)"
                strokeWidth="1.5"
                strokeDasharray="4 6"
              />
              <line
                x1="5"
                y1="50"
                x2="95"
                y2="50"
                stroke="var(--lime)"
                strokeWidth="2.5"
              />
              <line
                x1="50"
                y1="5"
                x2="50"
                y2="95"
                stroke="var(--lime)"
                strokeWidth="2.5"
              />
              <circle cx="50" cy="50" r="8" fill="#000" stroke="var(--lime)" strokeWidth="2" />
            </svg>
            <div
              style={{
                position: "absolute",
                bottom: -2,
                fontFamily: "var(--font-mono)",
                fontSize: 9,
                color: "var(--lime)",
                fontWeight: 800,
              }}
            >
              ROTOR ACTIVE
            </div>
          </div>

          <div
            style={{
              textAlign: "center",
              fontFamily: "var(--font-mono)",
              fontSize: 10,
              color: "var(--text-secondary)",
            }}
          >
            <div>{aircraft.engines}</div>
            <div style={{ color: "var(--lime)", marginTop: 4, fontWeight: 700 }}>
              STATUS: {aircraft.status}
            </div>
          </div>
        </div>

        {/* Real-time Telemetry Readout Grid */}
        <div className="telemetry-gauge-grid">
          <div className="gauge-cell">
            <span className="gauge-label">MAIN ROTOR RPM</span>
            <div className="gauge-val lime">{aircraft.currentRpm} RPM</div>
            <span style={{ fontSize: 9, fontFamily: "var(--font-mono)", color: "var(--text-muted)" }}>
              GOVERNOR: SYNC LOCKED
            </span>
          </div>

          <div className="gauge-cell">
            <span className="gauge-label">TWIN TORQUE LOAD</span>
            <div className="gauge-val">{aircraft.torquePercent}%</div>
            <span style={{ fontSize: 9, fontFamily: "var(--font-mono)", color: "var(--text-muted)" }}>
              BALANCE: 50/50 DUAL
            </span>
          </div>

          <div className="gauge-cell">
            <span className="gauge-label">
              {aircraft.id === "midnight" ? "BATTERY STATE (SOC)" : "JET-A FUEL RESERVE"}
            </span>
            <div className="gauge-val lime">{aircraft.fuelOrBatteryPercent}%</div>
            <span style={{ fontSize: 9, fontFamily: "var(--font-mono)", color: "var(--text-muted)" }}>
              ENDURANCE: ~2.4 HRS
            </span>
          </div>

          <div className="gauge-cell">
            <span className="gauge-label">NOISE FOOTPRINT</span>
            <div className="gauge-val">{aircraft.acousticLevelDba} dBA</div>
            <span style={{ fontSize: 9, fontFamily: "var(--font-mono)", color: "var(--lime)" }}>
              WHISPER-ROTOR COMPLIANT
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}

