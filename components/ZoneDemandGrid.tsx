"use client";

import { BENGALURU_ZONES, ZoneNode } from "./CityRideMap";

interface ZoneDemandGridProps {
  selectedPickup: string;
  onSelectPickup: (name: string) => void;
}

export default function ZoneDemandGrid({
  selectedPickup,
  onSelectPickup,
}: ZoneDemandGridProps) {
  return (
    <div className="bento-body">
      <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "1.6fr 1fr 1fr 1fr",
            fontFamily: "var(--font-mono)",
            fontSize: 9,
            letterSpacing: 1,
            color: "var(--text-muted)",
            paddingBottom: 6,
            borderBottom: "1px solid var(--border-hairline)",
          }}
        >
          <span>ZONE / LOCALITY</span>
          <span>AVAILABLE</span>
          <span>AVG WAIT</span>
          <span style={{ textAlign: "right" }}>SURGE INDEX</span>
        </div>

        {BENGALURU_ZONES.map((zone) => {
          const isSelected = zone.name === selectedPickup;
          return (
            <div
              key={zone.id}
              onClick={() => onSelectPickup(zone.name)}
              style={{
                display: "grid",
                gridTemplateColumns: "1.6fr 1fr 1fr 1fr",
                alignItems: "center",
                background: isSelected ? "var(--bg-surface-hover)" : "var(--bg-surface)",
                border: "1px solid",
                borderColor: isSelected ? "var(--lime)" : "var(--border-hairline)",
                padding: "10px 14px",
                cursor: "pointer",
                transition: "all 0.15s ease",
              }}
            >
              <div>
                <strong style={{ fontSize: 13, color: isSelected ? "var(--lime)" : "#fff", display: "block" }}>
                  {zone.name}
                </strong>
                <span style={{ fontSize: 10, color: "var(--text-muted)" }}>
                  {zone.kannadaName} · {zone.id}
                </span>
              </div>

              <div style={{ fontFamily: "var(--font-mono)", fontSize: 12, color: "#fff" }}>
                {zone.cabsAvailable} Cabs
              </div>

              <div style={{ fontFamily: "var(--font-mono)", fontSize: 12, color: "var(--text-secondary)" }}>
                {zone.avgWaitMins} mins
              </div>

              <div style={{ textAlign: "right" }}>
                <span
                  style={{
                    fontFamily: "var(--font-mono)",
                    fontSize: 10,
                    fontWeight: 700,
                    color: "var(--lime)",
                    background: "rgba(212, 255, 0, 0.08)",
                    border: "1px solid var(--lime)",
                    padding: "2px 6px",
                  }}
                >
                  1.0x FAIR
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

