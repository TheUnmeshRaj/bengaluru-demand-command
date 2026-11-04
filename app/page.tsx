"use client";

import { useState } from "react";
import CityRideMap from "../components/CityRideMap";
import CabBooking, { CabBookingDetails } from "../components/CabBooking";
import VoiceHeliAssistant from "../components/VoiceHeliAssistant";
import ZoneDemandGrid from "../components/ZoneDemandGrid";
import CabFleetTiers from "../components/CabFleetTiers";
import RideReceiptModal from "../components/RideReceiptModal";

export default function Home() {
  const [selectedPickup, setSelectedPickup] = useState<string>("Indiranagar");
  const [selectedDrop, setSelectedDrop] = useState<string>("KIAL Airport");
  const [activeBooking, setActiveBooking] = useState<CabBookingDetails | null>(null);

  const handleVoiceRoute = (pickup: string, drop: string) => {
    setSelectedPickup(pickup);
    setSelectedDrop(drop);
  };

  const handleTriggerVoiceDemo = () => {
    // Quick shortcut when clicking the voice banner
    handleVoiceRoute("Koramangala", "MG Road / CBD");
  };

  return (
    <main>
      {/* Swiss Modernist Navigation Bar */}
      <nav className="nav-header">
        <div className="brand-unit">
          <div className="brand-tag">RIDE</div>
          <div className="brand-title">
            HELI<span className="accent">.</span>
          </div>
          <div className="brand-kannada">
            <strong>ಹೇಳಿ (Heli)</strong>
            <span>“Just say where to go”</span>
          </div>
        </div>

        <div className="header-status-strip">
          <div className="status-indicator">
            <span className="status-dot" />
            <span>312 CABS ACTIVE</span>
          </div>
          <div className="status-indicator">
            <span>MEDIAN WAIT: <strong>2.8 MIN</strong></span>
          </div>
          <div className="city-badge">
            <span>BENGALURU</span>
            <span style={{ color: "var(--lime)" }}>● LIVE</span>
          </div>
        </div>
      </nav>

      {/* Bento Shell */}
      <div className="bento-container">
        {/* Hero Statement Banner */}
        <section className="hero-statement">
          <div className="hero-main">
            <h1>
              Just say where to go. <span className="kannada-word">“ಹೇಳಿ”</span>
            </h1>
            <p>
              Ride-Heli brings voice-first, surge-free cab and taxi mobility to Bengaluru.
              Speak your destination in Kannada or English, and we dispatch the closest cab in under 3 minutes.
            </p>
          </div>

          <div className="hero-stat-cell">
            <div className="stat-kicker">AVERAGE PICKUP</div>
            <div className="stat-metric">
              2.8 <span className="lime">MIN</span>
            </div>
            <div className="stat-note">Rapid neighborhood dispatch</div>
          </div>

          <div className="hero-stat-cell">
            <div className="stat-kicker">FAIR FARE POLICY</div>
            <div className="stat-metric">
              <span className="lime">1.0X</span> BASE
            </div>
            <div className="stat-note">Zero hidden surge gouging</div>
          </div>
        </section>

        {/* Master Bento Grid */}
        <div className="bento-grid">
          {/* Tile 01: Bengaluru City Spatial Map */}
          <div className="bento-card col-7">
            <div className="bento-header">
              <div className="bento-meta">
                <span className="bento-kicker">01 // LIVE CITY SPATIAL MAP</span>
                <span className="bento-title">Bengaluru Fleet Distribution &amp; Corridors</span>
              </div>
              <span
                style={{
                  fontFamily: "var(--font-mono)",
                  fontSize: 10,
                  color: "var(--lime)",
                  border: "1px solid var(--lime)",
                  padding: "3px 8px",
                }}
              >
                CLICK ZONE TO SET PICKUP
              </span>
            </div>

            <CityRideMap
              selectedPickup={selectedPickup}
              selectedDrop={selectedDrop}
              onSelectZone={(zoneName) => {
                if (zoneName !== selectedDrop) {
                  setSelectedPickup(zoneName);
                }
              }}
            />
          </div>

          {/* Tile 02: Cab Booking Module */}
          <div className="bento-card col-5 highlight">
            <div className="bento-header">
              <div className="bento-meta">
                <span className="bento-kicker">02 // INSTANT CAB DISPATCH</span>
                <span className="bento-title">Book a Cab or Taxi</span>
              </div>
              <span style={{ fontFamily: "var(--font-mono)", fontSize: 10, color: "var(--text-muted)" }}>
                TRANSPARENT RATES
              </span>
            </div>

            <CabBooking
              selectedPickup={selectedPickup}
              selectedDrop={selectedDrop}
              onChangePickup={setSelectedPickup}
              onChangeDrop={setSelectedDrop}
              onBookRide={(booking) => setActiveBooking(booking)}
              onTriggerVoice={handleTriggerVoiceDemo}
            />
          </div>

          {/* Tile 03: "Heli" (ಹೇಳಿ) Voice Assistant Module */}
          <div className="bento-card col-6">
            <div className="bento-header">
              <div className="bento-meta">
                <span className="bento-kicker">03 // VOICE-FIRST INTELLIGENCE</span>
                <span className="bento-title">“ಹೇಳಿ” (Heli) Speech Dispatch Assistant</span>
              </div>
              <span style={{ fontFamily: "var(--font-mono)", fontSize: 10, color: "var(--lime)" }}>
                ಕನ್ನಡ &amp; ENGLISH
              </span>
            </div>

            <VoiceHeliAssistant onApplyVoiceRoute={handleVoiceRoute} />
          </div>

          {/* Tile 04: Zone Demand & Fair Pricing Monitor */}
          <div className="bento-card col-6">
            <div className="bento-header">
              <div className="bento-meta">
                <span className="bento-kicker">04 // NEIGHBORHOOD AVAILABILITY</span>
                <span className="bento-title">Bengaluru Hub Demand &amp; Wait Times</span>
              </div>
              <span style={{ fontFamily: "var(--font-mono)", fontSize: 10, color: "var(--text-secondary)" }}>
                52 ZONES
              </span>
            </div>

            <ZoneDemandGrid
              selectedPickup={selectedPickup}
              onSelectPickup={setSelectedPickup}
            />
          </div>

          {/* Tile 05: Fleet Categories & Driver Transparency */}
          <div className="bento-card col-12">
            <div className="bento-header">
              <div className="bento-meta">
                <span className="bento-kicker">05 // VEHICLE CATEGORIES</span>
                <span className="bento-title">Fleet Specifications &amp; Driver-First Transparency</span>
              </div>
              <span style={{ fontFamily: "var(--font-mono)", fontSize: 10, color: "var(--lime)" }}>
                FAIR COMMISSIONS
              </span>
            </div>

            <CabFleetTiers />
          </div>
        </div>
      </div>

      {/* Ride Confirmation Receipt Modal */}
      {activeBooking && (
        <RideReceiptModal
          booking={activeBooking}
          onClose={() => setActiveBooking(null)}
        />
      )}

      {/* Swiss Modernist Footer */}
      <footer className="app-footer">
        <div>
          <span>RIDE-HELI MOBILITY // </span>
          <span className="lime">NAMMA BENGALURU CAB &amp; TAXI NETWORK</span>
        </div>
        <div>
          <span>ಹೇಳಿ (HELI) = “TELL ME” IN KANNADA · VOICE-FIRST URBAN TRANSIT</span>
        </div>
      </footer>
    </main>
  );
}
