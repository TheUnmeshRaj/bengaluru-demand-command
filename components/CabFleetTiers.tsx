"use client";

export default function CabFleetTiers() {
  const tiers = [
    {
      name: "Heli EV (Clean Mobility)",
      kannada: "ಎಲೆಕ್ಟ್ರಿಕ್ ಟ್ಯಾಕ್ಸಿ",
      model: "Tata Tigor EV / Nexon EV",
      capacity: "4 Passengers · 2 Bags",
      pricing: "₹80 base + ₹17/km",
      perks: "Silent cabin · Zero tailpipe emissions · AC guaranteed",
      badge: "ECO HERO",
      badgeColor: "var(--emerald)",
    },
    {
      name: "Heli Prime Sedan",
      kannada: "ಪ್ರೈಮ್ ಸೆಡಾನ್",
      model: "Toyota Glanza / Honda Amaze",
      capacity: "4 Passengers · 3 Bags",
      pricing: "₹100 base + ₹21/km",
      perks: "Executive legroom · Top-rated 4.9★ chauffeurs · Bottled water",
      badge: "EXECUTIVE",
      badgeColor: "var(--lime)",
    },
    {
      name: "Heli Mini",
      kannada: "ಸಿಟಿ ಮಿನಿ",
      model: "Maruti Swift / WagonR",
      capacity: "4 Passengers · 1 Bag",
      pricing: "₹60 base + ₹14/km",
      perks: "Swift city hop · Pocket-friendly everyday Bengaluru commute",
      badge: "DAILY RIDE",
      badgeColor: "#fff",
    },
    {
      name: "Heli Auto",
      kannada: "ನಮ್ಮ ಆಟೋ",
      model: "Bajaj RE / Piaggio City",
      capacity: "3 Passengers · 1 Bag",
      pricing: "₹30 base + ₹11/km",
      perks: "Quickest through Silk Board & Marathahalli bottlenecks",
      badge: "FAST TRACK",
      badgeColor: "var(--amber)",
    },
  ];

  return (
    <div className="bento-body">
      <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: 14 }}>
        {tiers.map((tier) => (
          <div
            key={tier.name}
            style={{
              background: "var(--bg-surface)",
              border: "1px solid var(--border-hairline)",
              padding: "16px 18px",
              display: "flex",
              flexDirection: "column",
              justifyContent: "space-between",
              gap: 12,
            }}
          >
            <div>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                <div>
                  <strong style={{ fontSize: 14, color: "#fff", display: "block" }}>
                    {tier.name}
                  </strong>
                  <span style={{ fontSize: 11, color: "var(--text-muted)" }}>
                    {tier.kannada} · {tier.model}
                  </span>
                </div>

                <span
                  style={{
                    fontFamily: "var(--font-mono)",
                    fontSize: 9,
                    fontWeight: 700,
                    color: tier.badgeColor,
                    border: `1px solid ${tier.badgeColor}`,
                    padding: "2px 6px",
                  }}
                >
                  {tier.badge}
                </span>
              </div>

              <div
                style={{
                  fontFamily: "var(--font-mono)",
                  fontSize: 11,
                  color: "var(--text-secondary)",
                  marginTop: 10,
                }}
              >
                {tier.capacity}
              </div>

              <div style={{ fontSize: 12, color: "var(--text-muted)", marginTop: 4 }}>
                {tier.perks}
              </div>
            </div>

            <div
              style={{
                borderTop: "1px solid var(--border-hairline)",
                paddingTop: 10,
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
              }}
            >
              <span style={{ fontFamily: "var(--font-mono)", fontSize: 10, color: "var(--text-muted)" }}>
                TRANSPARENT TARIFF
              </span>
              <strong style={{ fontFamily: "var(--font-mono)", fontSize: 13, color: "var(--lime)" }}>
                {tier.pricing}
              </strong>
            </div>
          </div>
        ))}
      </div>

      <div
        style={{
          marginTop: 14,
          padding: "10px 14px",
          background: "#0c0d12",
          border: "1px solid var(--border-hairline)",
          display: "flex",
          justifyContent: "space-between",
          fontFamily: "var(--font-mono)",
          fontSize: 11,
          color: "var(--text-secondary)",
        }}
      >
        <span>DRIVER FIRST INITIATIVE: 85% DIRECT FARE PAYOUT</span>
        <span style={{ color: "var(--lime)" }}>ZERO CANCELLATION PENALTY</span>
      </div>
    </div>
  );
}

