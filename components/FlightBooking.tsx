"use client";

import { useState } from "react";
import { VertiportNode } from "./TacticalRadar";

export interface BookingDetails {
  originCode: string;
  originName: string;
  destCode: string;
  destName: string;
  flightType: "shuttle" | "charter";
  selectedSeat: string;
  distanceNm: number;
  flightTimeMin: number;
  groundTimeMin: number;
  aircraftModel: string;
  passengersCount: number;
  luggageTier: "standard" | "executive";
  totalPrice: number;
  departureTime: string;
}

interface FlightBookingProps {
  vertiports: VertiportNode[];
  onBookFlight: (booking: BookingDetails) => void;
}

export default function FlightBooking({
  vertiports,
  onBookFlight,
}: FlightBookingProps) {
  const [originId, setOriginId] = useState<string>(vertiports[0]?.id || "vp-1");
  const [destId, setDestId] = useState<string>(vertiports[1]?.id || "vp-2");
  const [flightType, setFlightType] = useState<"shuttle" | "charter">("shuttle");
  const [selectedSeat, setSelectedSeat] = useState<string>("2A");
  const [luggageTier, setLuggageTier] = useState<"standard" | "executive">(
    "standard"
  );
  const [timeSlot, setTimeSlot] = useState<string>("IN 15 MIN");

  const origin = vertiports.find((v) => v.id === originId) || vertiports[0];
  const dest =
    vertiports.find((v) => v.id === destId) || vertiports[1] || vertiports[0];

  // Calculate simulated nautical miles & flight time
  const dx = (origin.x - dest.x);
  const dy = (origin.y - dest.y);
  const distanceNm = Math.max(4, Math.round(Math.hypot(dx, dy) * 0.45));
  const flightTimeMin = Math.max(5, Math.round((distanceNm / 145) * 60) + 3);
  const groundTimeMin = Math.max(40, distanceNm * 4.5 + 25);

  // Pricing calculation
  const baseRate = flightType === "shuttle" ? 225 : 1450;
  const distanceSurcharge = Math.round(distanceNm * (flightType === "shuttle" ? 14 : 75));
  const luggageCost = luggageTier === "executive" ? (flightType === "shuttle" ? 45 : 0) : 0;
  const vertiportFee = flightType === "shuttle" ? 38 : 120;
  const totalPrice = baseRate + distanceSurcharge + luggageCost + vertiportFee;

  const handleSwap = () => {
    const temp = originId;
    setOriginId(destId);
    setDestId(temp);
  };

  const handleTriggerBooking = () => {
    onBookFlight({
      originCode: origin.code,
      originName: origin.name,
      destCode: dest.code,
      destName: dest.name,
      flightType,
      selectedSeat: flightType === "charter" ? "ALL VIP SUITE (1-6)" : selectedSeat,
      distanceNm,
      flightTimeMin,
      groundTimeMin,
      aircraftModel: flightType === "shuttle" ? "Sikorsky S-76D Executive" : "Airbus ACH145 Hermes",
      passengersCount: flightType === "shuttle" ? 1 : 6,
      luggageTier,
      totalPrice,
      departureTime: timeSlot,
    });
  };

  const cabinSeats = [
    { id: "1A", label: "1A", type: "WINDOW", side: "LEFT", occupied: false },
    { id: "1B", label: "1B", type: "WINDOW", side: "RIGHT", occupied: true },
    { id: "2A", label: "2A", type: "CLUB EXECUTIVE", side: "LEFT", occupied: false },
    { id: "2B", label: "2B", type: "CLUB EXECUTIVE", side: "RIGHT", occupied: false },
    { id: "3A", label: "3A", type: "WINDOW AFT", side: "LEFT", occupied: false },
    { id: "3B", label: "3B", type: "WINDOW AFT", side: "RIGHT", occupied: false },
  ];

  return (
    <div className="bento-body">
      <div className="booking-form">
        {/* Shuttle Seat vs Charter Switch */}
        <div className="flight-type-toggle">
          <button
            type="button"
            className={`type-toggle-btn ${flightType === "shuttle" ? "active" : ""}`}
            onClick={() => setFlightType("shuttle")}
          >
            <span>BY-THE-SEAT SHUTTLE</span>
            <small>Guaranteed single/double seat dispatch</small>
          </button>
          <button
            type="button"
            className={`type-toggle-btn ${flightType === "charter" ? "active" : ""}`}
            onClick={() => setFlightType("charter")}
          >
            <span>PRIVATE VIP CHARTER</span>
            <small>Entire 6-passenger twin-engine cabin</small>
          </button>
        </div>

        {/* Origin / Destination Vertiport Selector */}
        <div className="route-selector-box">
          <div className="vertiport-field">
            <label className="field-label">
              <span>01 / DEPARTURE VERTIPORT</span>
              <span className="loc-code">[{origin.code}]</span>
            </label>
            <select
              className="field-select"
              value={originId}
              onChange={(e) => setOriginId(e.target.value)}
            >
              {vertiports.map((vp) => (
                <option key={`orig-${vp.id}`} value={vp.id} disabled={vp.id === destId}>
                  [{vp.code}] {vp.name} ({vp.availablePads} pads ready)
                </option>
              ))}
            </select>
          </div>

          <button
            type="button"
            className="route-swap-btn"
            onClick={handleSwap}
            title="Swap Origin and Destination"
          >
            ⇄
          </button>

          <div className="vertiport-field">
            <label className="field-label">
              <span>02 / ARRIVAL VERTIPORT</span>
              <span className="loc-code">[{dest.code}]</span>
            </label>
            <select
              className="field-select"
              value={destId}
              onChange={(e) => setDestId(e.target.value)}
            >
              {vertiports.map((vp) => (
                <option key={`dest-${vp.id}`} value={vp.id} disabled={vp.id === originId}>
                  [{vp.code}] {vp.name} ({vp.availablePads} pads ready)
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Departure Window Selector */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(3, 1fr)",
            gap: 8,
          }}
        >
          {["IN 15 MIN", "IN 45 MIN", "CUSTOM SCHEDULE"].map((slot) => (
            <button
              key={slot}
              type="button"
              onClick={() => setTimeSlot(slot)}
              style={{
                background: timeSlot === slot ? "var(--lime)" : "#0c1017",
                color: timeSlot === slot ? "#000" : "var(--text-secondary)",
                border: "1px solid",
                borderColor: timeSlot === slot ? "var(--lime)" : "var(--border-medium)",
                fontFamily: "var(--font-mono)",
                fontSize: 10,
                fontWeight: 700,
                padding: "8px 4px",
                cursor: "pointer",
                textAlign: "center",
              }}
            >
              {slot}
            </button>
          ))}
        </div>

        {/* VIP Cabin Seat Selection (if shuttle mode) */}
        {flightType === "shuttle" ? (
          <div className="seat-matrix-wrapper">
            <div className="field-label">
              <span>SELECT CABIN SEAT</span>
              <span className="loc-code">[ACTIVE: {selectedSeat}]</span>
            </div>

            <div className="cabin-diagram">
              <div className="cockpit-row">
                <div className="cockpit-pilot-tag">CAPT. PILOT</div>
                <div className="cockpit-pilot-tag">FIRST OFFICER</div>
              </div>

              <div className="passenger-cabin-seats">
                {cabinSeats.map((seat) => (
                  <div
                    key={seat.id}
                    className={`seat-box ${
                      seat.occupied
                        ? "occupied"
                        : selectedSeat === seat.id
                        ? "selected"
                        : ""
                    }`}
                    onClick={() => {
                      if (!seat.occupied) setSelectedSeat(seat.id);
                    }}
                  >
                    <span className="seat-label">{seat.label}</span>
                    <span className="seat-pos">{seat.type}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        ) : (
          <div
            style={{
              background: "#0d1119",
              border: "1px solid var(--border-medium)",
              padding: 12,
              fontFamily: "var(--font-mono)",
              fontSize: 11,
              color: "var(--text-secondary)",
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
            }}
          >
            <span>FULL AIRCRAFT CHARTER PRIVILEGE</span>
            <strong style={{ color: "var(--lime)" }}>6 VIP SEATS RESERVED</strong>
          </div>
        )}

        {/* Luggage Tier */}
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            background: "#090c12",
            border: "1px solid var(--border-medium)",
            padding: "8px 12px",
            fontFamily: "var(--font-mono)",
            fontSize: 11,
          }}
        >
          <span style={{ color: "var(--text-muted)" }}>LUGGAGE ALLOTMENT</span>
          <div style={{ display: "flex", gap: 6 }}>
            <button
              type="button"
              onClick={() => setLuggageTier("standard")}
              style={{
                background: luggageTier === "standard" ? "var(--lime)" : "transparent",
                color: luggageTier === "standard" ? "#000" : "var(--text-secondary)",
                border: "1px solid var(--border-bright)",
                fontFamily: "var(--font-mono)",
                fontSize: 10,
                padding: "4px 8px",
                cursor: "pointer",
                fontWeight: 600,
              }}
            >
              25 KG STD
            </button>
            <button
              type="button"
              onClick={() => setLuggageTier("executive")}
              style={{
                background: luggageTier === "executive" ? "var(--lime)" : "transparent",
                color: luggageTier === "executive" ? "#000" : "var(--text-secondary)",
                border: "1px solid var(--border-bright)",
                fontFamily: "var(--font-mono)",
                fontSize: 10,
                padding: "4px 8px",
                cursor: "pointer",
                fontWeight: 600,
              }}
            >
              EXECUTIVE HEAVY (+$45)
            </button>
          </div>
        </div>

        {/* Dynamic Pricing Breakdown */}
        <div className="pricing-breakdown">
          <div className="price-line">
            <span>FLIGHT DURATION / DISTANCE</span>
            <strong>
              {flightTimeMin} MIN · {distanceNm} NM
            </strong>
          </div>
          <div className="price-line">
            <span>AIRCRAFT BASE RATE</span>
            <strong>${baseRate}</strong>
          </div>
          <div className="price-line">
            <span>SKYWAY CORRIDOR SURCHARGE</span>
            <strong>${distanceSurcharge}</strong>
          </div>
          <div className="price-line">
            <span>VERTIPORT LANDING & SECURITY TAX</span>
            <strong>${vertiportFee}</strong>
          </div>
          <div className="price-line total-line">
            <span>TOTAL AUTHORIZATION</span>
            <span className="amount">${totalPrice}</span>
          </div>
        </div>

        {/* Action Button */}
        <button
          type="button"
          className="btn-book-primary"
          onClick={handleTriggerBooking}
        >
          <span>AUTHORIZE SKY-DISPATCH // INSTANT TICKET</span>
          <span>→</span>
        </button>
      </div>
    </div>
  );
}

