"use client";

import { useState } from "react";
import { BENGALURU_ZONES } from "./CityRideMap";

export interface CabBookingDetails {
  pickup: string;
  drop: string;
  cabType: "mini" | "prime" | "ev" | "auto";
  estimatedFare: number;
  distanceKm: number;
  etaMins: number;
  driverName: string;
  vehicleModel: string;
  plateNumber: string;
  otp: string;
}

interface CabBookingProps {
  selectedPickup: string;
  selectedDrop: string;
  onChangePickup: (pickup: string) => void;
  onChangeDrop: (drop: string) => void;
  onBookRide: (booking: CabBookingDetails) => void;
  onTriggerVoice: () => void;
}

export default function CabBooking({
  selectedPickup,
  selectedDrop,
  onChangePickup,
  onChangeDrop,
  onBookRide,
  onTriggerVoice,
}: CabBookingProps) {
  const [cabType, setCabType] = useState<"mini" | "prime" | "ev" | "auto">("ev");

  // Dynamic distance estimate
  const pickupNode = BENGALURU_ZONES.find((z) => z.name === selectedPickup) || BENGALURU_ZONES[0];
  const dropNode = BENGALURU_ZONES.find((z) => z.name === selectedDrop) || BENGALURU_ZONES[1];

  const dx = (pickupNode.x - dropNode.x);
  const dy = (pickupNode.y - dropNode.y);
  const distanceKm = Math.max(3, Math.round(Math.hypot(dx, dy) * 0.42));
  const etaMins = Math.max(12, Math.round(distanceKm * 2.8));

  // Transparent pricing calculation
  const fareRates = {
    mini: { base: 60, perKm: 14, minEta: 3, name: "Heli Mini", model: "Maruti WagonR / Swift" },
    prime: { base: 100, perKm: 21, minEta: 4, name: "Heli Prime", model: "Toyota Glanza / Honda Amaze" },
    ev: { base: 80, perKm: 17, minEta: 2, name: "Heli EV", model: "Tata Tigor EV / Nexon EV" },
    auto: { base: 30, perKm: 11, minEta: 1, name: "Heli Auto", model: "Bajaj RE / Piaggio City" },
  };

  const selectedRate = fareRates[cabType];
  const estimatedFare = Math.round(selectedRate.base + distanceKm * selectedRate.perKm);

  const handleBook = () => {
    onBookRide({
      pickup: selectedPickup,
      drop: selectedDrop,
      cabType,
      estimatedFare,
      distanceKm,
      etaMins,
      driverName: "Suresh Gowda",
      vehicleModel: selectedRate.model,
      plateNumber: "KA-01-MJ-4092",
      otp: String(Math.floor(1000 + Math.random() * 9000)),
    });
  };

  return (
    <div className="bento-body">
      <div className="booking-stack">
        {/* Voice Trigger Banner: Heli = Speak */}
        <div className="voice-banner" onClick={onTriggerVoice}>
          <div className="voice-info">
            <div className="voice-mic-icon">🎙</div>
            <div className="voice-copy">
              <strong>“ಹೇಳಿ” (Heli) — Just Say Your Destination</strong>
              <small>Tap to speak in Kannada or English · Zero typing</small>
            </div>
          </div>
          <span className="voice-pill">VOICE DISPATCH</span>
        </div>

        {/* Pickup & Drop Selectors */}
        <div className="route-inputs">
          <div className="location-row">
            <label className="location-label">
              <span>01 / PICKUP LOCATION</span>
              <span className="tag">GPS ANCHOR</span>
            </label>
            <select
              className="location-select"
              value={selectedPickup}
              onChange={(e) => onChangePickup(e.target.value)}
            >
              {BENGALURU_ZONES.map((z) => (
                <option key={`p-${z.id}`} value={z.name} disabled={z.name === selectedDrop}>
                  {z.name} ({z.kannadaName}) · {z.cabsAvailable} cabs nearby
                </option>
              ))}
            </select>
          </div>

          <div className="location-row">
            <label className="location-label">
              <span>02 / DESTINATION</span>
              <span className="tag">DIRECT COMMUTE</span>
            </label>
            <select
              className="location-select"
              value={selectedDrop}
              onChange={(e) => onChangeDrop(e.target.value)}
            >
              {BENGALURU_ZONES.map((z) => (
                <option key={`d-${z.id}`} value={z.name} disabled={z.name === selectedPickup}>
                  {z.name} ({z.kannadaName}) · {distanceKm} km approx
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Cab Category Tiers */}
        <div>
          <div className="stat-kicker">SELECT CAB FLEET TIER</div>
          <div className="cab-tier-grid">
            <div
              className={`cab-tier-card ${cabType === "mini" ? "selected" : ""}`}
              onClick={() => setCabType("mini")}
            >
              <div>
                <div className="tier-title">Heli Mini</div>
                <div className="tier-eta">3m away · Hatch</div>
              </div>
              <div className="tier-fare">₹{Math.round(60 + distanceKm * 14)}</div>
            </div>

            <div
              className={`cab-tier-card ${cabType === "prime" ? "selected" : ""}`}
              onClick={() => setCabType("prime")}
            >
              <div>
                <div className="tier-title">Heli Prime</div>
                <div className="tier-eta">4m away · Sedan</div>
              </div>
              <div className="tier-fare">₹{Math.round(100 + distanceKm * 21)}</div>
            </div>

            <div
              className={`cab-tier-card ${cabType === "ev" ? "selected" : ""}`}
              onClick={() => setCabType("ev")}
            >
              <div>
                <div className="tier-title" style={{ display: "flex", alignItems: "center", gap: 4 }}>
                  <span>Heli EV</span>
                  <span style={{ fontSize: 9, color: "var(--emerald)", background: "rgba(16,185,129,0.15)", padding: "1px 4px" }}>
                    ECO
                  </span>
                </div>
                <div className="tier-eta">2m away · Silent</div>
              </div>
              <div className="tier-fare">₹{Math.round(80 + distanceKm * 17)}</div>
            </div>

            <div
              className={`cab-tier-card ${cabType === "auto" ? "selected" : ""}`}
              onClick={() => setCabType("auto")}
            >
              <div>
                <div className="tier-title">Heli Auto</div>
                <div className="tier-eta">1m away · 3-Wheeler</div>
              </div>
              <div className="tier-fare">₹{Math.round(30 + distanceKm * 11)}</div>
            </div>
          </div>
        </div>

        {/* Fare Summary & Booking CTA */}
        <div className="booking-summary-row">
          <div className="fare-total">
            <span>GUARANTEED FIXED FARE</span>
            <strong>₹{estimatedFare} <small style={{ fontSize: 13, color: "var(--text-secondary)", fontWeight: 400 }}>· {distanceKm} km</small></strong>
          </div>

          <button
            type="button"
            className="btn-book-ride"
            onClick={handleBook}
          >
            <span>CONFIRM RIDE-HELI</span>
            <span>→</span>
          </button>
        </div>
      </div>
    </div>
  );
}

