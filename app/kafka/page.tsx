"use client";

import { useEffect, useState } from "react";

type KafkaState = {
  status: string;
  broker: string;
  inputTopic: string;
  outputTopic: string;
  window: string;
  horizon: string;
  predictor?: string;
  consumed: number;
  published: number;
  errors: number;
  lastWindow: string | null;
  logs?: { time: string; level: string; message: string }[];
};

const initialState: KafkaState = {
  status: "offline",
  broker: "localhost:9092",
  inputTopic: "ride_requests",
  outputTopic: "predictions",
  window: "5 minutes",
  horizon: "15 minutes",
  predictor: "Persistence_baseline",
  consumed: 0,
  published: 0,
  errors: 0,
  lastWindow: null,
};

export default function KafkaLogsPage() {
  const [state, setState] = useState(initialState);

  useEffect(() => {
    const readState = () => fetch("http://127.0.0.1:8000/state")
      .then((response) => response.ok ? response.json() as Promise<KafkaState> : Promise.reject(new Error("offline")))
      .then(setState)
      .catch(() => setState((current) => ({ ...current, status: "offline" })));
    readState();
    const timer = window.setInterval(readState, 3000);
    return () => window.clearInterval(timer);
  }, []);

  const online = state.status === "connected";
  return <main className="kafka-standalone"><header className="kafka-standalone-header"><div><p className="eyebrow">BENGALURU / KAFKA OPERATIONS</p><h1>Kafka log console</h1><p>Live evidence of ride events becoming zone predictions.</p></div><div className={`kafka-status ${online ? "online" : "offline"}`}><span className="status-dot" />{online ? "CONNECTED" : "OFFLINE"}</div></header><section className="kafka-standalone-flow"><div><b>01</b><strong>ride_requests</strong><small>Ride replay producer</small></div><i>→</i><div><b>02</b><strong>5-minute window</strong><small>Zone aggregation</small></div><i>→</i><div><b>03</b><strong>predictions</strong><small>Next 15-minute forecast</small></div></section><section className="kafka-standalone-grid"><div className="kafka-standalone-card"><span>EVENTS CONSUMED</span><strong>{state.consumed.toLocaleString("en-IN")}</strong><small>from {state.inputTopic}</small></div><div className="kafka-standalone-card"><span>PREDICTIONS PUBLISHED</span><strong>{state.published.toLocaleString("en-IN")}</strong><small>to {state.outputTopic}</small></div><div className="kafka-standalone-card"><span>WINDOW / HORIZON</span><strong>{state.window} / {state.horizon}</strong><small>{state.predictor}</small></div><div className="kafka-standalone-card"><span>ERRORS</span><strong>{state.errors}</strong><small>Consumer errors</small></div></section><section className="kafka-standalone-log"><div className="kafka-log-header"><div><span className="section-kicker">LIVE LOG STREAM</span><h2>Pipeline events</h2></div><code>{state.broker}</code></div>{(state.logs?.length ? state.logs : [{ time: "--:--:--", level: "WAIT", message: "Start Docker Compose to receive Kafka events." }]).map((log, index) => <div className="kafka-log-line" key={`${log.time}-${index}`}><time>{log.time}</time><b className={log.level === "PRED" ? "pred-log" : ""}>{log.level}</b><span>{log.message}</span></div>)}</section><a className="back-dashboard" href="/">← Back to demand command center</a></main>;
}
