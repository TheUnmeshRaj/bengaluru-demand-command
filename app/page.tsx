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

type LiveState = {
  status: string;
  lastWindow: string | null;
  consumed: number;
  published: number;
  zones: Zone[];
  broker: string;
  inputTopic: string;
  outputTopic: string;
  logs?: { time: string; level: string; message: string }[];
};

type ContextData = {
  events: { id: string; name: string; type: string; zoneId: string; zone: string; start: string; end: string; intensity: number }[];
  weatherSignals: { timestamp: string; weather: string; rain: number }[];
  notes: string[];
};

const formatNumber = (value: number) => new Intl.NumberFormat("en-IN", { maximumFractionDigits: 0 }).format(value);

function WorkspacePage({ page, data, context, rankedZones, selectedZone, onSelect, live, onToggleLive, streamStatus, liveState }: {
  page: string;
  data: DashboardData;
  context: ContextData;
  rankedZones: Zone[];
  selectedZone: string;
  onSelect: (id: string) => void;
  live: boolean;
  onToggleLive: () => void;
  streamStatus: string;
  liveState: LiveState | null;
}) {
  if (page === "Live map") {
    return <section className="workspace-page"><section className="panel map-panel map-page-panel"><div className="panel-header"><div><span className="section-kicker">LIVE MAP / 52 ZONES</span><h3>Move drivers toward the strongest forecast</h3></div><div className="legend"><span><i className="legend-dot low" />Low</span><span><i className="legend-dot mid" />Rising</span><span><i className="legend-dot high" />Hot</span></div></div><DemandMap zones={rankedZones} coordinatesUrl="/data/zone-coordinates.json" selectedZone={selectedZone} onSelect={onSelect} /></section><section className="panel map-side-panel"><span className="section-kicker">SELECTED ZONE</span><h3>{data.zones.find((zone) => zone.id === selectedZone)?.name ?? "Select a zone"}</h3><p className="page-muted">Click any hotspot on the map to see a driver briefing for the next 15 minutes.</p>{rankedZones.slice(0, 8).map((zone, index) => <button key={zone.id} className={zone.id === selectedZone ? "rank-row selected" : "rank-row"} onClick={() => onSelect(zone.id)}><span className="rank">{String(index + 1).padStart(2, "0")}</span><span className="rank-name">{zone.name}<small>{zone.id} · {zone.latest.weather}</small></span><span className="rank-value">{formatNumber(zone.latest.prediction15)}</span></button>)}</section></section>;
  }
  if (page === "Predictions") {
    return <section className="workspace-page"><section className="panel table-panel"><div className="panel-header"><div><span className="section-kicker">FORECAST REGISTER</span><h3>Next 15-minute demand by zone</h3></div><span className="refresh">Updated every 5 min</span></div><div className="prediction-table"><div className="table-row table-head"><span>RANK / ZONE</span><span>LAST 5 MIN</span><span>NEXT 15 MIN</span><span>CHANGE</span><span>CONTEXT</span></div>{rankedZones.map((zone, index) => { const change = zone.latest.prediction15 - zone.latest.demandLast5; return <div className="table-row" key={zone.id}><span className="table-zone"><b>{String(index + 1).padStart(2, "0")}</b><strong>{zone.name}</strong><small>{zone.id}</small></span><span>{formatNumber(zone.latest.demandLast5)}</span><span className="table-prediction">{formatNumber(zone.latest.prediction15)}</span><span className={change >= 0 ? "change-up" : "change-down"}>{change >= 0 ? "▲" : "▼"} {formatNumber(Math.abs(change))}</span><span className="context-tag">{zone.latest.event ? zone.latest.eventType : zone.latest.weather}</span></div>; })}</div></section><section className="panel metrics-panel"><span className="section-kicker">MODEL VALIDATION</span><h3>Test split metrics</h3><p className="page-muted">Reported from the existing contextual and historical model runs.</p>{data.metrics.filter((metric) => metric.Split === "test").map((metric) => <div className="metric-row" key={metric.Model}><span>{metric.Model.replace("_", " ")}</span><strong>{Number(metric.WAPE_percent).toFixed(1)}% <small>WAPE</small></strong></div>)}</section></section>;
  }
  if (page === "Driver plan") {
    const top = rankedZones.slice(0, 3);
    const latestEvent = context.events[context.events.length - 1];
    const rainSignal = context.weatherSignals[0];
    return <section className="driver-plan"><section className="plan-hero"><span className="live-pill">DRIVER PLAN · REPLAY DATE</span><h2>Work smart today</h2><p>Simple guidance for where to wait, when to move, and what may change demand.</p><div className="plan-date">Dataset replay: 29 Aug 2026 · Bengaluru</div></section><div className="alert-stack"><article className="driver-alert alert-hot"><span className="alert-icon">↗</span><div><strong>Start at {top[0]?.name}</strong><p>Highest predicted demand in the next 15 minutes: {formatNumber(top[0]?.latest.prediction15 ?? 0)} requests.</p></div><button onClick={() => onSelect(top[0]?.id ?? "Z30")}>Use</button></article><article className="driver-alert"><span className="alert-icon">◷</span><div><strong>Evening is usually busiest</strong><p>Your project data shows the strongest demand from 17:00 to 21:00, highest around 19:00.</p></div></article>{latestEvent && <article className="driver-alert alert-event"><span className="alert-icon">!</span><div><strong>Event signal in the data</strong><p>{latestEvent.name} at {latestEvent.zone}. This is a synthetic scenario from the supplied event file.</p></div></article>}{rainSignal && <article className="driver-alert alert-weather"><span className="alert-icon">☂</span><div><strong>Check weather before moving</strong><p>{rainSignal.weather} signal at {rainSignal.timestamp}; rain intensity {rainSignal.rain} in the supplied data.</p></div></article>}</div><section className="plan-grid"><div className="panel plan-route"><div className="panel-header"><div><span className="section-kicker">YOUR SIMPLE ROUTE</span><h3>Three good places to try</h3></div></div>{top.map((zone, index) => <button className="plan-stop" key={zone.id} onClick={() => onSelect(zone.id)}><span className="stop-number">{index + 1}</span><span><strong>{zone.name}</strong><small>Expected {formatNumber(zone.latest.prediction15)} requests · next 15 min</small></span><b>→</b></button>)}<button className="big-map-action" onClick={() => onSelect(top[0]?.id ?? "Z30")}>Show these on map</button></div><div className="panel plan-rules"><span className="section-kicker">GOOD TO KNOW</span><h3>Before you start</h3><ul><li>Move only when the hotspot is close and safe to reach.</li><li>Recheck the app after each 5-minute update.</li><li>Weekend demand is higher in the supplied analysis.</li><li>Diwali is not present in the supplied event file, so no Diwali alert is claimed here.</li></ul></div></section></section>;
  }
  return <section className="workspace-page"><section className="panel kafka-page-panel"><div className="panel-header"><div><span className="section-kicker">STREAMING OPERATIONS</span><h3>Kafka pipeline health</h3></div><span className="connected"><span className={`status-dot ${streamStatus === "connected" ? "" : "offline-dot"}`} />{streamStatus === "connected" && live ? "Connected" : streamStatus === "connected" ? "Paused" : "Offline"}</span></div><div className="pipeline-large"><div><b>01</b><strong>Ride replay producer</strong><small>{data.pipeline.inputTopic} · {data.pipeline.broker}</small></div><i>→</i><div><b>02</b><strong>5-minute aggregation</strong><small>Zone-level window close</small></div><i>→</i><div><b>03</b><strong>15-minute prediction</strong><small>Contextual model output</small></div><i>→</i><div><b>04</b><strong>Prediction storage</strong><small>Dashboard-ready records</small></div></div><div className="kafka-counters"><div><span>EVENTS CONSUMED</span><strong>{formatNumber(liveState?.consumed ?? 0)}</strong><small>from ride_requests</small></div><div><span>WINDOW</span><strong>5 min</strong><small>aggregation interval</small></div><div><span>PREDICTIONS</span><strong>{formatNumber(liveState?.published ?? 0)}</strong><small>published to predictions</small></div><div><span>HORIZON</span><strong>15 min</strong><small>forecast target</small></div></div><div className="log-window large-log">{(liveState?.logs?.length ? liveState.logs : [{ time: "—", level: "WAIT", message: "Waiting for live Kafka events…" }]).slice(0, 8).map((log, index) => <div key={`${log.time}-${index}`}><time>{log.time}</time><span className={log.level === "PRED" ? "log-blue" : "log-ok"}>{log.level}</span><p>{log.message}</p></div>)}</div><button className="stream-button" onClick={onToggleLive}>{live ? "Pause live stream" : "Resume live stream"}</button></section></section>;
}

export default function Home() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [selectedZone, setSelectedZone] = useState<string>("Z30");
  const [activeNav, setActiveNav] = useState("Overview");
  const [live, setLive] = useState(true);
  const [streamStatus, setStreamStatus] = useState("offline");
  const [context, setContext] = useState<ContextData | null>(null);
  const [liveState, setLiveState] = useState<LiveState | null>(null);

  useEffect(() => {
    let active = true;
    fetch("/data/context.json").then((response) => response.json()).then((value) => { if (active) setContext(value); });
    fetch("/data/dashboard.json")
      .then((response) => response.json())
      .then((baseline: DashboardData) => {
        if (active) setData(baseline);
        return fetch("http://127.0.0.1:8000/state");
      })
      .then((response) => {
        if (!response.ok) throw new Error(`Streaming API returned ${response.status}`);
        return response.json() as Promise<LiveState>;
      })
      .then((liveState) => {
        if (!active) return;
        setLiveState(liveState);
        setStreamStatus(liveState.status);
        setLiveState(liveState);
        if (liveState.status === "connected" && liveState.zones.length > 0) {
          setData((current) => current ? {
            ...current,
            latestTimestamp: liveState.lastWindow ?? current.latestTimestamp,
            zones: liveState.zones,
            pipeline: { ...current.pipeline, broker: liveState.broker, inputTopic: liveState.inputTopic },
          } : current);
        }
      })
      .catch(() => {
        if (active) setStreamStatus("offline");
      });
    const timer = window.setInterval(() => {
      fetch("http://127.0.0.1:8000/state")
        .then((response) => response.ok ? response.json() as Promise<LiveState> : Promise.reject(new Error("stream unavailable")))
        .then((liveState) => {
          if (active) {
            setStreamStatus(liveState.status);
            if (liveState.status === "connected" && liveState.zones.length > 0) {
              setData((current) => current ? { ...current, latestTimestamp: liveState.lastWindow ?? current.latestTimestamp, zones: liveState.zones } : current);
            }
          }
        })
        .catch(() => { if (active) setStreamStatus("offline"); });
    }, 5000);
    return () => { active = false; window.clearInterval(timer); };
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
        <div className="brand"><div className="brand-mark">⌁</div><div><strong>Ride<span>-Heli</span></strong><small>ಹೇಳಿ · mobility intelligence</small></div></div>
        <div className="workspace-label">WORKSPACE</div>
        <nav>
          {["Overview", "Driver plan", "Live map", "Predictions", "Kafka pipeline"].map((item) => (
            <button key={item} className={activeNav === item ? "nav-item active" : "nav-item"} onClick={() => setActiveNav(item)}>
              <span className="nav-icon">{item === "Overview" ? "▦" : item === "Live map" ? "⌖" : item === "Predictions" ? "↗" : "◌"}</span>{item}
              {item === "Kafka pipeline" && <em>LIVE</em>}
            </button>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="health-card"><span className={`status-dot ${streamStatus === "connected" ? "" : "offline-dot"}`} />{streamStatus === "connected" ? "Kafka pipeline live" : "Kafka service offline"}<div className="health-sub">{streamStatus === "connected" ? "Predictions are live" : "Showing prepared dataset"}</div></div>
          <div className="profile"><div className="avatar">DR</div><div><strong>Driver operator</strong><small>Control room</small></div><span>•••</span></div>
        </div>
      </aside>

      <section className="content">
        <header className="topbar"><div><p className="eyebrow">BENGALURU / OPERATIONS</p><h1>{activeNav === "Overview" ? "Demand command center" : activeNav}</h1></div><div className="top-actions"><span className="updated"><span className={`status-dot ${streamStatus === "connected" ? "" : "offline-dot"}`} />{streamStatus === "connected" ? "Kafka live" : "Kafka offline"}</span></div></header>

        <div className="hero-strip"><div><span className="live-pill">● LIVE FORECAST</span><h2>Where should drivers move next?</h2><p>Zone-level demand predicted for the next 15 minutes, refreshed from the streaming pipeline.</p></div><div className="hero-time"><span>LAST WINDOW</span><strong>{data.latestTimestamp.replace("2026-", "").replace(" ", " · ")}</strong><small>Asia/Kolkata · 5 min window</small></div></div>
        <section className="driver-mobile-card"><span className="section-kicker">DRIVER VIEW</span><h2>Go to {rankedZones[0]?.name}</h2><p>High demand expected in the next 15 minutes.</p><div className="driver-mobile-actions"><button onClick={() => setActiveNav("Live map")}>Show hotspot</button><button className="secondary-action" onClick={() => setSelectedZone(rankedZones[0]?.id ?? "Z30")}>Use this zone</button></div></section>

        <div className="stat-grid">
          <article className="stat-card"><span className="card-label">NEXT 15 MIN DEMAND</span><strong>{formatNumber(totalPrediction)}</strong><small className="positive">▲ Forecast across 52 zones</small></article>
          <article className="stat-card"><span className="card-label">TOP HOTSPOT</span><strong>{rankedZones[0]?.name}</strong><small>{formatNumber(rankedZones[0]?.latest.prediction15 ?? 0)} predicted requests</small></article>
          <article className="stat-card"><span className="card-label">PEAK HOUR</span><strong>{peak?.hour}:00 <small>hrs</small></strong><small>{formatNumber(peak?.demand ?? 0)} requests in dataset</small></article>
          <article className="stat-card"><span className="card-label">MODEL WAPE</span><strong>{xgboost ? `${Number(xgboost.WAPE_percent).toFixed(1)}%` : "—"}</strong><small>Contextual XGBoost · test split</small></article>
        </div>

        {activeNav !== "Overview" && context && <WorkspacePage page={activeNav} data={data} context={context} rankedZones={rankedZones} selectedZone={selectedZone} onSelect={setSelectedZone} live={live} onToggleLive={() => setLive(!live)} streamStatus={streamStatus} liveState={liveState} />}
        {activeNav === "Overview" && <>
        <div className="main-grid">
          <section className="panel map-panel"><div className="panel-header"><div><span className="section-kicker">SPATIAL DEMAND</span><h3>Hotspots across Bengaluru</h3></div><div className="legend"><span><i className="legend-dot low" />Low</span><span><i className="legend-dot mid" />Rising</span><span><i className="legend-dot high" />Hot</span></div></div><DemandMap zones={rankedZones} coordinatesUrl="/data/zone-coordinates.json" selectedZone={selectedZone} onSelect={setSelectedZone} /></section>
          <section className="panel forecast-panel"><div className="panel-header"><div><span className="section-kicker">DRIVER BRIEFING</span><h3>Move to a hotspot</h3></div><span className="refresh">↻ 5 min</span></div><div className="selected-zone"><div className="zone-rank">01</div><div className="zone-copy"><strong>{selected.name}</strong><span>{selected.id} · {selected.latest.weather}</span></div><div className="zone-prediction"><strong>{formatNumber(selected.latest.prediction15)}</strong><span>next 15 min</span></div></div><div className="forecast-bar"><span style={{ width: `${Math.min(100, (selected.latest.prediction15 / Math.max(1, rankedZones[0].latest.prediction15)) * 100)}%` }} /></div><div className="forecast-note"><span className="spark">↗</span><p><strong>Good move right now</strong><br />Demand is {selected.latest.prediction15 >= selected.latest.demandLast5 ? "building" : "steady"} versus the last 5-minute window.</p></div><div className="ranked-list">{rankedZones.slice(0, 5).map((zone, index) => <button key={zone.id} className={zone.id === selected.id ? "rank-row selected" : "rank-row"} onClick={() => setSelectedZone(zone.id)}><span className="rank">{String(index + 1).padStart(2, "0")}</span><span className="rank-name">{zone.name}<small>{zone.id}</small></span><span className="rank-value">{formatNumber(zone.latest.prediction15)}</span><span className="rank-arrow">→</span></button>)}</div></section>
        </div>

        <div className="lower-grid">
          <section className="panel trend-panel"><div className="panel-header"><div><span className="section-kicker">TEMPORAL PATTERN</span><h3>Demand by hour</h3></div><span className="trend-caption">Dataset baseline · Jul–Aug 2026</span></div><div className="bar-chart">{data.hourly.map((point) => <div className="bar-wrap" key={point.hour} title={`${point.hour}:00 · ${formatNumber(point.demand)} requests`}><div className={point.hour >= 17 && point.hour <= 21 ? "bar peak" : "bar"} style={{ height: `${Math.max(4, (point.demand / (peak?.demand ?? 1)) * 100)}%` }} />{point.hour % 3 === 0 && <span>{point.hour}</span>}</div>)}</div><div className="chart-foot"><span>00:00</span><span className="peak-label">Evening peak · 17:00—21:00</span><span>23:00</span></div></section>
          <section className="panel kafka-panel"><div className="panel-header"><div><span className="section-kicker">STREAMING OBSERVABILITY</span><h3>Kafka pipeline</h3></div><span className="connected"><span className={`status-dot ${streamStatus === "connected" ? "" : "offline-dot"}`} />{streamStatus === "connected" ? "Connected" : "Offline"}</span></div><div className="pipeline-flow"><span>PRODUCER</span><b>→</b><span>ride_requests</span><b>→</b><span>5 MIN AGG.</span><b>→</b><span className="accent">15 MIN PRED.</span></div><div className="log-window">{(liveState?.logs?.length ? liveState.logs : [{ time: "—", level: "WAIT", message: "Waiting for producer and consumer events…" }]).slice(0, 4).map((log, index) => <div key={`${log.time}-${index}`}><time>{log.time}</time><span className={log.level === "PRED" ? "log-blue" : "log-ok"}>{log.level}</span><p>{log.message}</p></div>)}</div><div className="kafka-footer"><span>localhost:9092</span><span>{liveState?.consumed ?? 0} consumed</span><span>{liveState?.published ?? 0} predictions</span><button onClick={() => setLive(!live)}>{live ? "Pause stream" : "Resume stream"}</button></div></section>
        </div>
        </>}
        <footer><span>Ride-Heli · Synthetic Bengaluru ride requests · Predictions are decision support, not guaranteed demand.</span><span>OpenStreetMap contributors · Zone coordinates are geocoded map anchors.</span></footer>
      </section>
    </main>
  );
}
