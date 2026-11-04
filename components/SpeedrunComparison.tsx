"use client";

interface SpeedrunComparisonProps {
  flightTimeMin: number;
  groundTimeMin: number;
  originCode: string;
  destCode: string;
}

export default function SpeedrunComparison({
  flightTimeMin,
  groundTimeMin,
  originCode,
  destCode,
}: SpeedrunComparisonProps) {
  const timeSaved = Math.max(15, groundTimeMin - flightTimeMin);
  const groundRatio = 100;
  const airRatio = Math.max(10, Math.round((flightTimeMin / groundTimeMin) * 100));

  return (
    <div className="bento-body">
      <div className="speedrun-card">
        <div className="comparison-tracks">
          {/* Air Route Speedrun */}
          <div className="track-row highlight-air">
            <div className="track-header">
              <div className="track-mode">
                <span style={{ color: "var(--lime)" }}>▲</span>
                <span>RIDE-HELI DIRECT SKYWAY</span>
              </div>
              <div className="track-time lime">{flightTimeMin} MIN</div>
            </div>
            <div className="progress-bar-rail">
              <div
                className="progress-fill lime-active"
                style={{ width: `${airRatio}%` }}
              />
            </div>
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                fontFamily: "var(--font-mono)",
                fontSize: 9,
                color: "var(--text-secondary)",
              }}
            >
              <span>CRUISING: 155 KTS (FL015)</span>
              <span>ZERO TRAFFIC / DIRECT AIRWAY</span>
            </div>
          </div>

          {/* Ground Vehicle Gridlock */}
          <div className="track-row">
            <div className="track-header">
              <div className="track-mode">
                <span style={{ color: "var(--text-muted)" }}>▼</span>
                <span>GROUND ARTERIAL GRIDLOCK</span>
              </div>
              <div className="track-time">{groundTimeMin} MIN</div>
            </div>
            <div className="progress-bar-rail">
              <div
                className="progress-fill"
                style={{ width: `${groundRatio}%` }}
              />
            </div>
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                fontFamily: "var(--font-mono)",
                fontSize: 9,
                color: "var(--text-muted)",
              }}
            >
              <span>SURFACE ROADS & BRIDGES</span>
              <span>ESTIMATED CONGESTION DELAY: +38 MIN</span>
            </div>
          </div>
        </div>

        {/* Time Saved Kicker */}
        <div className="time-saved-badge">
          <div>
            <div
              style={{
                fontFamily: "var(--font-mono)",
                fontSize: 10,
                color: "var(--text-muted)",
                letterSpacing: 1.2,
              }}
            >
              TIME RECLAIMED
            </div>
            <div
              style={{
                fontFamily: "var(--font-display)",
                fontSize: 22,
                fontWeight: 800,
                color: "#fff",
              }}
            >
              +{timeSaved} MINUTES
            </div>
          </div>
          <div
            style={{
              background: "var(--lime)",
              color: "#000",
              fontFamily: "var(--font-mono)",
              fontSize: 11,
              fontWeight: 800,
              padding: "6px 10px",
              boxShadow: "2px 2px 0px #000",
            }}
          >
            {Math.round((timeSaved / groundTimeMin) * 100)}% FASTER
          </div>
        </div>

        {/* Flight Profile Elevation SVG */}
        <div
          style={{
            background: "#080a0f",
            border: "1px solid var(--border-medium)",
            padding: 12,
          }}
        >
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              fontFamily: "var(--font-mono)",
              fontSize: 9,
              color: "var(--text-muted)",
              marginBottom: 6,
            }}
          >
            <span>VERTICAL TRAJECTORY PROFILE</span>
            <span style={{ color: "var(--lime)" }}>CEILING: 1,500 FT AGL</span>
          </div>

          <svg
            viewBox="0 0 320 60"
            style={{ width: "100%", height: 60, overflow: "visible" }}
          >
            {/* Grid line */}
            <line
              x1="0"
              y1="55"
              x2="320"
              y2="55"
              stroke="#1f2533"
              strokeWidth="1"
            />
            <line
              x1="0"
              y1="15"
              x2="320"
              y2="15"
              stroke="#1f2533"
              strokeWidth="1"
              strokeDasharray="2 4"
            />

            {/* Flight Curve */}
            <path
              d="M 10 55 C 50 15, 80 15, 160 15 C 240 15, 270 15, 310 55"
              fill="none"
              stroke="var(--lime)"
              strokeWidth="2"
            />

            {/* Shaded Area under curve */}
            <path
              d="M 10 55 C 50 15, 80 15, 160 15 C 240 15, 270 15, 310 55 L 310 55 L 10 55 Z"
              fill="rgba(212, 255, 0, 0.06)"
            />

            {/* Waypoint dots */}
            <circle cx="10" cy="55" r="3" fill="#00f0ff" />
            <circle cx="160" cy="15" r="3.5" fill="var(--lime)" />
            <circle cx="310" cy="55" r="3" fill="#00f0ff" />

            {/* Text labels */}
            <text
              x="10"
              y="48"
              fill="#9da8b9"
              fontSize="7"
              fontFamily="'JetBrains Mono', monospace"
            >
              [{originCode}]
            </text>
            <text
              x="142"
              y="10"
              fill="var(--lime)"
              fontSize="7"
              fontFamily="'JetBrains Mono', monospace"
            >
              CRUISE 1,500 FT
            </text>
            <text
              x="290"
              y="48"
              fill="#9da8b9"
              fontSize="7"
              fontFamily="'JetBrains Mono', monospace"
            >
              [{destCode}]
            </text>
          </svg>
        </div>
      </div>
    </div>
  );
}

