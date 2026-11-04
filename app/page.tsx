"use client";

import dynamic from "next/dynamic";
import { useEffect, useMemo, useState } from "react";

const DemandMap = dynamic(() => import("../components/DemandMap"), { ssr: false });

type Zone = {
  id: string;
  name: string;
  average15: number;
  total: number;
  latest: {
    timestamp: string;
    demandLast5: number;
    prediction15: number;
    hour: number;
    weather: string;
    rain: number;
    event: boolean;
    eventType: string;
  };
};

type DashboardData = {
  latestTimestamp: string;
  zones: Zone[];
  hourly: { hour: number; demand: number }[];
  metrics: { Model: string; Split: string; MAE: string; RMSE: string; WAPE_percent: string }[];
  pipeline: { broker: string; inputTopic: string; window: string; horizon: string; delivery: string };
};

const formatNumber = (value: number) => new Intl.NumberFormat("en-IN", { maximumFractionDigits: 0 }).format(value);

export default function Home() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [selectedZone, setSelectedZone] = useState<string>("Z30");
  const [activeNav, setActiveNav] = useState("Overview");
  const [live, setLive] = useState(true);

  useEffect(() => {
    fetch("/data/dashboard.json").then((response) => response.json()).then(setData);
  }, []);

  const selected = useMemo(() => data?.zones.find((zone) => zone.id === selectedZone) ?? data?.zones[0], [data, selectedZone]);
  const rankedZones = useMemo(() => [...(data?.zones ?? [])].sort((a, b) => b.latest.prediction15 - a.latest.prediction15), [data]);
  const totalPrediction = rankedZones.reduce((sum, zone) => sum + zone.latest.prediction15, 0);
  const peak = data?.hourly.reduce((best, point) => point.demand > best.demand ? point : best, data.hourly[0]);
  const xgboost = data?.metrics.find((metric) => metric.Model === "XGBoost_contextual" && metric.Split === "test");

  if (!data || !selected) return <main className="loading"><div className="loader" />Loading demand command center…</main>;

  return (
    <main className="shell">
      <aside className="sidebar">
        <div className="brand"><div className="brand-mark">⌁</div><div><strong>flow<span>cast</span></strong><small>mobility intelligence</small></div></div>
        <div className="workspace-label">WORKSPACE</div>
        <nav>
          {["Overview", "Live map", "Predictions", "Kafka pipeline"].map((item) => (
            <button key={item} className={activeNav === item ? "nav-item active" : "nav-item"} onClick={() => setActiveNav(item)}>
              <span className="nav-icon">{item === "Overview" ? "▦" : item === "Live map" ? "⌖" : item === "Predictions" ? "↗" : "◌"}</span>{item}
              {item === "Kafka pipeline" && <em>LIVE</em>}
            </button>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="health-card"><span className="status-dot" />Pipeline healthy<div className="health-sub">All consumers connected</div></div>
          <div className="profile"><div className="avatar">DR</div><div><strong>Demo operator</strong><small>Control room</small></div><span>•••</span></div>
        </div>
      </aside>

      <section className="content">
        <header className="topbar"><div><p className="eyebrow">BENGALURU / OPERATIONS</p><h1>{activeNav === "Overview" ? "Demand command center" : activeNav}</h1></div><div className="top-actions"><span className="updated"><span className="status-dot" />Streaming now</span><button className="date-button">01 Jul — 29 Aug 2026⌄</button><button className="icon-button">⚙</button></div></header>

        <div className="hero-strip"><div><span className="live-pill">● LIVE FORECAST</span><h2>Where should drivers move next?</h2><p>Zone-level demand predicted for the next 15 minutes, refreshed from the streaming pipeline.</p></div><div className="hero-time"><span>LAST WINDOW</span><strong>{data.latestTimestamp.replace("2026-", "").replace(" ", " · ")}</strong><small>Asia/Kolkata · 5 min window</small></div></div>

        <div className="stat-grid">
          <article className="stat-card"><span className="card-label">NEXT 15 MIN DEMAND</span><strong>{formatNumber(totalPrediction)}</strong><small className="positive">▲ Forecast across 52 zones</small></article>
          <article className="stat-card"><span className="card-label">TOP HOTSPOT</span><strong>{rankedZones[0]?.name}</strong><small>{formatNumber(rankedZones[0]?.latest.prediction15 ?? 0)} predicted requests</small></article>
          <article className="stat-card"><span className="card-label">PEAK HOUR</span><strong>{peak?.hour}:00 <small>hrs</small></strong><small>{formatNumber(peak?.demand ?? 0)} requests in dataset</small></article>
          <article className="stat-card"><span className="card-label">MODEL WAPE</span><strong>{xgboost ? `${Number(xgboost.WAPE_percent).toFixed(1)}%` : "—"}</strong><small>Contextual XGBoost · test split</small></article>
        </div>

        <div className="main-grid">
          <section className="panel map-panel"><div className="panel-header"><div><span className="section-kicker">SPATIAL DEMAND</span><h3>Hotspots across Bengaluru</h3></div><div className="legend"><span><i className="legend-dot low" />Low</span><span><i className="legend-dot mid" />Rising</span><span><i className="legend-dot high" />Hot</span></div></div><DemandMap zones={rankedZones} coordinatesUrl="/data/zone-coordinates.json" selectedZone={selectedZone} onSelect={setSelectedZone} /></section>
          <section className="panel forecast-panel"><div className="panel-header"><div><span className="section-kicker">DRIVER BRIEFING</span><h3>Move to a hotspot</h3></div><span className="refresh">↻ 5 min</span></div><div className="selected-zone"><div className="zone-rank">01</div><div className="zone-copy"><strong>{selected.name}</strong><span>{selected.id} · {selected.latest.weather}</span></div><div className="zone-prediction"><strong>{formatNumber(selected.latest.prediction15)}</strong><span>next 15 min</span></div></div><div className="forecast-bar"><span style={{ width: `${Math.min(100, (selected.latest.prediction15 / Math.max(1, rankedZones[0].latest.prediction15)) * 100)}%` }} /></div><div className="forecast-note"><span className="spark">↗</span><p><strong>Good move right now</strong><br />Demand is {selected.latest.prediction15 >= selected.latest.demandLast5 ? "building" : "steady"} versus the last 5-minute window.</p></div><div className="ranked-list">{rankedZones.slice(0, 5).map((zone, index) => <button key={zone.id} className={zone.id === selected.id ? "rank-row selected" : "rank-row"} onClick={() => setSelectedZone(zone.id)}><span className="rank">{String(index + 1).padStart(2, "0")}</span><span className="rank-name">{zone.name}<small>{zone.id}</small></span><span className="rank-value">{formatNumber(zone.latest.prediction15)}</span><span className="rank-arrow">→</span></button>)}</div></section>
        </div>

        <div className="lower-grid">
          <section className="panel trend-panel"><div className="panel-header"><div><span className="section-kicker">TEMPORAL PATTERN</span><h3>Demand by hour</h3></div><span className="trend-caption">Dataset baseline · Jul–Aug 2026</span></div><div className="bar-chart">{data.hourly.map((point) => <div className="bar-wrap" key={point.hour} title={`${point.hour}:00 · ${formatNumber(point.demand)} requests`}><div className={point.hour >= 17 && point.hour <= 21 ? "bar peak" : "bar"} style={{ height: `${Math.max(4, (point.demand / (peak?.demand ?? 1)) * 100)}%` }} />{point.hour % 3 === 0 && <span>{point.hour}</span>}</div>)}</div><div className="chart-foot"><span>00:00</span><span className="peak-label">Evening peak · 17:00—21:00</span><span>23:00</span></div></section>
          <section className="panel kafka-panel"><div className="panel-header"><div><span className="section-kicker">STREAMING OBSERVABILITY</span><h3>Kafka pipeline</h3></div><span className="connected"><span className="status-dot" />Connected</span></div><div className="pipeline-flow"><span>PRODUCER</span><b>→</b><span>ride_requests</span><b>→</b><span>5 MIN AGG.</span><b>→</b><span className="accent">15 MIN PRED.</span></div><div className="log-window"><div><time>19:32:04</time><span className="log-ok">INFO</span><p>Consumed 1,248 ride events</p></div><div><time>19:32:05</time><span className="log-ok">INFO</span><p>Window closed · 52 zones aggregated</p></div><div><time>19:32:05</time><span className="log-blue">PRED</span><p>Forecast published · horizon=15m</p></div><div><time>19:32:06</time><span className="log-ok">INFO</span><p>Predictions committed to storage</p></div></div><div className="kafka-footer"><span>localhost:9092</span><span>acks=all</span><span>idempotence=true</span><button onClick={() => setLive(!live)}>{live ? "Pause stream" : "Resume stream"}</button></div></section>
        </div>
        <footer><span>Flowcast demo · Synthetic Bengaluru ride requests · Predictions are decision support, not guaranteed demand.</span><span>OpenStreetMap contributors · Zone coordinates are geocoded map anchors.</span></footer>
      </section>
    </main>
  );
}
