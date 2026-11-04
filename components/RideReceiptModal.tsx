"use client";

import { CabBookingDetails } from "./CabBooking";

interface RideReceiptModalProps {
  booking: CabBookingDetails;
  onClose: () => void;
}

export default function RideReceiptModal({
  booking,
  onClose,
}: RideReceiptModalProps) {
  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="receipt-sheet" onClick={(e) => e.stopPropagation()}>
        <div className="receipt-header">
          <div>
            <div style={{ fontFamily: "var(--font-mono)", fontSize: 10, color: "var(--lime)", fontWeight: 700 }}>
              RIDE CONFIRMED // DISPATCH ACTIVE
            </div>
            <strong style={{ fontSize: 16, color: "#fff" }}>Ride-Heli Cab Pass</strong>
          </div>
          <button className="receipt-close" onClick={onClose}>
            ✕
          </button>
        </div>

        <div className="receipt-body">
          {/* OTP Code Callout */}
          <div className="otp-box">
            <div>
              <div className="otp-label">START TRIP OTP</div>
              <div style={{ fontSize: 11, color: "var(--text-secondary)" }}>
                Share with driver when cab arrives
              </div>
            </div>
            <div className="otp-code">{booking.otp}</div>
          </div>

          {/* Driver & Cab Details */}
          <div className="driver-detail-card">
            <div className="driver-avatar">SG</div>
            <div className="driver-info" style={{ flex: 1 }}>
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <strong>{booking.driverName}</strong>
                <span style={{ color: "var(--lime)", fontWeight: 700 }}>★ 4.9 (1,420 trips)</span>
              </div>
              <span>{booking.vehicleModel} · {booking.plateNumber}</span>
            </div>
          </div>

          {/* Route Details */}
          <div
            style={{
              background: "var(--bg-surface)",
              border: "1px solid var(--border-hairline)",
              padding: 14,
              display: "flex",
              flexDirection: "column",
              gap: 10,
            }}
          >
            <div style={{ display: "flex", gap: 10 }}>
              <span style={{ color: "var(--lime)" }}>●</span>
              <div>
                <span style={{ fontSize: 10, color: "var(--text-muted)", fontFamily: "var(--font-mono)" }}>
                  PICKUP (DRIVER ARRIVING IN 3 MINS)
                </span>
                <div style={{ fontSize: 13, color: "#fff", fontWeight: 600 }}>{booking.pickup}</div>
              </div>
            </div>

            <div style={{ borderLeft: "1px dashed var(--border-strong)", marginLeft: 4, height: 12 }} />

            <div style={{ display: "flex", gap: 10 }}>
              <span style={{ color: "#fff" }}>■</span>
              <div>
                <span style={{ fontSize: 10, color: "var(--text-muted)", fontFamily: "var(--font-mono)" }}>
                  DESTINATION
                </span>
                <div style={{ fontSize: 13, color: "#fff", fontWeight: 600 }}>{booking.drop}</div>
              </div>
            </div>
          </div>

          {/* Fare & Distance Row */}
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(3, 1fr)",
              gap: 10,
              fontFamily: "var(--font-mono)",
            }}
          >
            <div style={{ background: "var(--bg-surface)", padding: 10, border: "1px solid var(--border-hairline)" }}>
              <div style={{ fontSize: 9, color: "var(--text-muted)" }}>DISTANCE</div>
              <div style={{ fontSize: 14, fontWeight: 700, color: "#fff", marginTop: 2 }}>
                {booking.distanceKm} KM
              </div>
            </div>
            <div style={{ background: "var(--bg-surface)", padding: 10, border: "1px solid var(--border-hairline)" }}>
              <div style={{ fontSize: 9, color: "var(--text-muted)" }}>EST. TRAVEL</div>
              <div style={{ fontSize: 14, fontWeight: 700, color: "#fff", marginTop: 2 }}>
                {booking.etaMins} MINS
              </div>
            </div>
            <div style={{ background: "var(--bg-surface)", padding: 10, border: "1px solid var(--border-hairline)" }}>
              <div style={{ fontSize: 9, color: "var(--text-muted)" }}>FIXED FARE</div>
              <div style={{ fontSize: 14, fontWeight: 700, color: "var(--lime)", marginTop: 2 }}>
                ₹{booking.estimatedFare}
              </div>
            </div>
          </div>

          {/* Safety & Action buttons */}
          <div style={{ display: "flex", gap: 10 }}>
            <button
              onClick={() => {
                alert(`Live tracking link copied! Driver Suresh (KA-01-MJ-4092) is 3 minutes away.`);
              }}
              style={{
                flex: 1,
                background: "var(--lime)",
                color: "#000",
                border: "1px solid var(--lime)",
                fontFamily: "var(--font-sans)",
                fontSize: 12,
                fontWeight: 800,
                padding: "12px",
                cursor: "pointer",
              }}
            >
              SHARE LIVE TRIP
            </button>
            <button
              onClick={onClose}
              style={{
                background: "var(--bg-surface)",
                color: "var(--text-secondary)",
                border: "1px solid var(--border-hairline)",
                fontFamily: "var(--font-sans)",
                fontSize: 12,
                padding: "12px 18px",
                cursor: "pointer",
              }}
            >
              CLOSE
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

