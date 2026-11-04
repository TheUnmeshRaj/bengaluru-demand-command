"use client";

import { BookingDetails } from "./FlightBooking";

interface BoardingPassModalProps {
  booking: BookingDetails;
  onClose: () => void;
}

export default function BoardingPassModal({
  booking,
  onClose,
}: BoardingPassModalProps) {
  const timestamp = new Date().toISOString().slice(11, 19) + "Z";
  const passId = "RH-" + Math.floor(100000 + Math.random() * 900000);

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div
        className="boarding-pass-modal"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="boarding-pass-header">
          <span>// RIDE-HELI BOARDING AUTHORIZATION</span>
          <button className="modal-close-btn" onClick={onClose}>
            ✕
          </button>
        </div>

        <div className="boarding-pass-body">
          {/* Flight Route Banner */}
          <div className="pass-flight-highlight">
            <div className="pass-port">
              <span className="code">{booking.originCode}</span>
              <span className="name">{booking.originName}</span>
            </div>
            <div className="pass-arrow">➔</div>
            <div className="pass-port" style={{ textAlign: "right" }}>
              <span className="code">{booking.destCode}</span>
              <span className="name">{booking.destName}</span>
            </div>
          </div>

          {/* Passenger & Flight Details */}
          <div className="pass-data-table">
            <div className="pass-cell">
              <div className="pass-cell-label">PASSENGER CLASS</div>
              <div className="pass-cell-val">VIP EXECUTIVE</div>
            </div>
            <div className="pass-cell">
              <div className="pass-cell-label">SEAT ASSIGNMENT</div>
              <div className="pass-cell-val">{booking.selectedSeat}</div>
            </div>
            <div className="pass-cell">
              <div className="pass-cell-label">BOARDING PAD</div>
              <div className="pass-cell-val">PAD ALPHA 01</div>
            </div>
            <div className="pass-cell">
              <div className="pass-cell-label">FLIGHT DURATION</div>
              <div className="pass-cell-val">{booking.flightTimeMin} MIN</div>
            </div>
            <div className="pass-cell">
              <div className="pass-cell-label">DEPARTURE SLOT</div>
              <div className="pass-cell-val">{booking.departureTime}</div>
            </div>
            <div className="pass-cell">
              <div className="pass-cell-label">ZULU TIMESTAMP</div>
              <div className="pass-cell-val">{timestamp}</div>
            </div>
          </div>

          {/* Scannable Aztec / QR Matrix */}
          <div className="qr-code-zone">
            <div className="qr-mock">
              {/* High-contrast geometric Aztec / QR pattern */}
              <svg viewBox="0 0 40 40" fill="#000">
                <rect x="0" y="0" width="12" height="12" />
                <rect x="2" y="2" width="8" height="8" fill="#fff" />
                <rect x="4" y="4" width="4" height="4" />

                <rect x="28" y="0" width="12" height="12" />
                <rect x="30" y="2" width="8" height="8" fill="#fff" />
                <rect x="32" y="4" width="4" height="4" />

                <rect x="0" y="28" width="12" height="12" />
                <rect x="2" y="30" width="8" height="8" fill="#fff" />
                <rect x="4" y="32" width="4" height="4" />

                <rect x="16" y="2" width="4" height="8" />
                <rect x="22" y="6" width="4" height="4" />
                <rect x="14" y="14" width="12" height="12" />
                <rect x="18" y="18" width="4" height="4" fill="#fff" />
                <rect x="2" y="16" width="6" height="4" />
                <rect x="30" y="18" width="6" height="4" />
                <rect x="16" y="30" width="8" height="4" />
                <rect x="26" y="28" width="4" height="8" />
              </svg>
            </div>
            <div className="qr-info">
              <strong>SECURITY ACCESS TOKEN: {passId}</strong>
              <span>VERIFIED VIA SKYWAVE CRYPTO DISPATCH</span>
              <span>LUGGAGE: {booking.luggageTier.toUpperCase()} // PRIORITY ESCORT</span>
              <span style={{ color: "var(--lime)" }}>
                PAID IN FULL: ${booking.totalPrice} USD
              </span>
            </div>
          </div>

          {/* Action buttons */}
          <div style={{ display: "flex", gap: 10 }}>
            <button
              onClick={() => alert(`Boarding Pass ${passId} saved to Apple Wallet / Google Wallet!`)}
              style={{
                flex: 1,
                background: "var(--lime)",
                color: "#000",
                border: "2px solid #000",
                fontFamily: "var(--font-mono)",
                fontSize: 12,
                fontWeight: 800,
                padding: "12px",
                cursor: "pointer",
                boxShadow: "3px 3px 0px #000",
              }}
            >
              SAVE TO MOBILE WALLET
            </button>
            <button
              onClick={onClose}
              style={{
                background: "#000",
                color: "#fff",
                border: "1px solid var(--border-bright)",
                fontFamily: "var(--font-mono)",
                fontSize: 12,
                padding: "12px 18px",
                cursor: "pointer",
              }}
            >
              DISMISS
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

