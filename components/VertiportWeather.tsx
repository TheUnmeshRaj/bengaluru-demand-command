"use client";

import { useState } from "react";

export default function VertiportWeather() {
  const [windHeading] = useState<number>(240); // 240 degrees SSW
  const [windSpeed] = useState<number>(14); // knots

  const pads = [
    { id: "p1", name: "PAD ALPHA (PRIMARY)", status: "clear", label: "CLEARED FOR LANDING" },
    { id: "p2", name: "PAD BRAVO (EXECUTIVE)", status: "active", label: "BOARDING IN PROGRESS" },
    { id: "p3", name: "PAD CHARLIE (eVTOL)", status: "charging", label: "400KW MEGAWATT CHARGING" },
  ];

  return (
    <div className="bento-body">
      <div style={{ display: "grid", gridTemplateColumns: "1.1fr 1fr", gap: 14 }}>
        {/* Wind Compass Rose */}
        <div
          style={{
            background: "#080a0f",
            border: "1px solid var(--border-medium)",
            padding: 12,
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            position: "relative",
          }}
        >
          <div
            style={{
              position: "absolute",
              top: 6,
              left: 8,
              fontFamily: "var(--font-mono)",
              fontSize: 9,
              color: "var(--text-muted)",
            }}
          >
            WIND VECTOR
          </div>

          <svg viewBox="0 0 100 100" style={{ width: 85, height: 85 }}>
            {/* Compass Outer Ring */}
            <circle
              cx="50"
              cy="50"
              r="40"
              fill="none"
              stroke="#222a3a"
              strokeWidth="1.5"
            />
            <circle
              cx="50"
              cy="50"
              r="30"
              fill="none"
              stroke="#182030"
              strokeWidth="1"
              strokeDasharray="2 3"
            />

            {/* Compass Cardinal Points */}
            <text x="47" y="18" fill="#d4ff00" fontSize="8" fontFamily="'JetBrains Mono', monospace" fontWeight="bold">N</text>
            <text x="47" y="90" fill="#6e7b91" fontSize="7" fontFamily="'JetBrains Mono', monospace">S</text>
            <text x="83" y="53" fill="#6e7b91" fontSize="7" fontFamily="'JetBrains Mono', monospace">E</text>
            <text x="11" y="53" fill="#6e7b91" fontSize="7" fontFamily="'JetBrains Mono', monospace">W</text>

            {/* Wind Vector Pointer Needle */}
            <g transform={`rotate(${windHeading} 50 50)`}>
              <polygon points="50,16 45,46 55,46" fill="var(--lime)" />
              <polygon points="50,84 46,54 54,54" fill="#3a455a" />
              <circle cx="50" cy="50" r="3" fill="#000" stroke="var(--lime)" strokeWidth="1.5" />
            </g>
          </svg>

          <div
            style={{
              fontFamily: "var(--font-mono)",
              fontSize: 11,
              fontWeight: 700,
              color: "#fff",
              marginTop: 4,
            }}
          >
            {windHeading}° @ <span style={{ color: "var(--lime)" }}>{windSpeed} KTS</span>
          </div>
        </div>

        {/* Atmospheric Metrics */}
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          <div
            style={{
              background: "#090c12",
              border: "1px solid var(--border-medium)",
              padding: "8px 10px",
            }}
          >
            <div style={{ fontFamily: "var(--font-mono)", fontSize: 8, color: "var(--text-muted)" }}>
              CLOUD CEILING
            </div>
            <div style={{ fontFamily: "var(--font-mono)", fontSize: 13, fontWeight: 700, color: "#fff" }}>
              FL045 (4,500 FT)
            </div>
          </div>

          <div
            style={{
              background: "#090c12",
              border: "1px solid var(--border-medium)",
              padding: "8px 10px",
            }}
          >
            <div style={{ fontFamily: "var(--font-mono)", fontSize: 8, color: "var(--text-muted)" }}>
              VISIBILITY / QNH
            </div>
            <div style={{ fontFamily: "var(--font-mono)", fontSize: 13, fontWeight: 700, color: "var(--lime)" }}>
              10+ SM · 29.92 INHG
            </div>
          </div>

          <div
            style={{
              background: "#090c12",
              border: "1px solid var(--border-medium)",
              padding: "8px 10px",
            }}
          >
            <div style={{ fontFamily: "var(--font-mono)", fontSize: 8, color: "var(--text-muted)" }}>
              GROUND TEMP
            </div>
            <div style={{ fontFamily: "var(--font-mono)", fontSize: 13, fontWeight: 700, color: "#fff" }}>
              19°C (66°F) · DRY PAD
            </div>
          </div>
        </div>
      </div>

      {/* Helipad Bay Status */}
      <div style={{ marginTop: 14 }}>
        <div className="vertiport-status-list">
          {pads.map((pad) => (
            <div key={pad.id} className="pad-status-row">
              <span className="pad-name">
                <span
                  style={{
                    width: 7,
                    height: 7,
                    borderRadius: "50%",
                    background:
                      pad.status === "clear"
                        ? "var(--lime)"
                        : pad.status === "active"
                        ? "var(--amber)"
                        : "var(--cyan)",
                  }}
                />
                {pad.name}
              </span>
              <span className={`pad-status-pill ${pad.status}`}>
                {pad.label}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

