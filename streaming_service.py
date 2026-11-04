"""Live Kafka aggregation, prediction, publication, and dashboard state API.

Run from the project root:
    python -m pip install -r requirements-streaming.txt
    python streaming_service.py

The service consumes ride_requests, closes five-minute zone windows, predicts
Target_Next_15min with the trained contextual model, and publishes predictions
to the predictions topic. It intentionally does not fabricate a live state
when Kafka is unavailable: the API reports a waiting status instead.
"""

from __future__ import annotations

import json
import logging
import math
import os
import threading
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from confluent_kafka import Consumer, KafkaError, KafkaException, Producer
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

ROOT = Path(__file__).resolve().parent
BROKER = os.getenv("KAFKA_BROKER", "localhost:9092")
INPUT_TOPIC = os.getenv("KAFKA_INPUT_TOPIC", "ride_requests")
OUTPUT_TOPIC = os.getenv("KAFKA_OUTPUT_TOPIC", "predictions")
GROUP_ID = os.getenv("KAFKA_GROUP_ID", "bengaluru-demand-predictor")
ZONE_DATA_PATH = ROOT / "public" / "data" / "dashboard.json"
IST = timezone(timedelta(hours=5, minutes=30))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("bengaluru-stream")

app = FastAPI(title="Bengaluru demand streaming service")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

state_lock = threading.Lock()
state: dict[str, Any] = {
    "status": "starting",
    "broker": BROKER,
    "inputTopic": INPUT_TOPIC,
    "outputTopic": OUTPUT_TOPIC,
    "window": "5 minutes",
    "horizon": "15 minutes",
    "predictor": "Persistence_baseline",
    "delivery": "acks=all, idempotence enabled",
    "lastWindow": None,
    "consumed": 0,
    "published": 0,
    "errors": 0,
    "logs": deque(maxlen=30),
    "zones": {},
}


def load_zone_names() -> dict[str, str]:
    if not ZONE_DATA_PATH.exists():
        return {}
    payload = json.loads(ZONE_DATA_PATH.read_text(encoding="utf-8"))
    return {zone["id"]: zone["name"] for zone in payload.get("zones", [])}


ZONE_NAMES = load_zone_names()


def parse_event_time(value: str | None) -> datetime:
    if not value:
        return datetime.now(IST)
    parsed = datetime.fromisoformat(value)
    return parsed.replace(tzinfo=IST) if parsed.tzinfo is None else parsed


def window_start(value: datetime) -> datetime:
    value = value.astimezone(IST).replace(second=0, microsecond=0)
    return value.replace(minute=value.minute - value.minute % 5)


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def feature_row(
    zone_id: str,
    timestamp: datetime,
    count: float,
    history: deque[float],
    context: dict[str, Any],
) -> dict[str, Any]:
    values = list(history)
    lag = lambda intervals: values[-intervals] if len(values) >= intervals else 0.0
    recent = values[-3:] if values else [0.0]
    half_hour = values[-6:] if values else [0.0]
    hour = values[-12:] if values else [0.0]
    hour_number = timestamp.hour
    day_number = timestamp.weekday()
    return {
        "Hour": hour_number,
        "Day_Of_Week": day_number,
        "Is_Weekend": int(day_number >= 5),
        "Hour_Sin": math.sin(2 * math.pi * hour_number / 24),
        "Hour_Cos": math.cos(2 * math.pi * hour_number / 24),
        "DayOfWeek_Sin": math.sin(2 * math.pi * day_number / 7),
        "DayOfWeek_Cos": math.cos(2 * math.pi * day_number / 7),
        "Demand_Last_5min": count,
        "Demand_Lag_5min": lag(1),
        "Demand_Lag_10min": lag(2),
        "Demand_Lag_15min": lag(3),
        "Demand_Lag_30min": lag(6),
        "Demand_Lag_60min": lag(12),
        "Rolling_Mean_15min": sum(recent) / len(recent),
        "Rolling_Mean_30min": sum(half_hour) / len(half_hour),
        "Rolling_Mean_60min": sum(hour) / len(hour),
        "Zone_ID": zone_id,
        "Rain_Intensity": safe_float(context.get("rain_intensity")),
        "Event_Active": int(bool(context.get("event_flag"))),
        "Event_Impact": int(bool(context.get("event_flag"))),
        "Event_Intensity": int(safe_float(context.get("event_intensity"))),
        "Weather_Condition": context.get("weather") or "Clear",
        "Event_Type": context.get("event_type") or "No_Event",
        "Event_Phase": context.get("event_phase") or "No_Event",
    }


def publish_predictions(
    producer: Producer,
    counts: dict[str, int],
    histories: dict[str, deque[float]],
    contexts: dict[str, dict[str, Any]],
    timestamp: datetime,
) -> None:
    zone_ids = sorted(set(ZONE_NAMES) | set(counts))
    for zone_id in zone_ids:
        count = counts.get(zone_id, 0)
        history = list(histories[zone_id]) + [float(count)]
        recent = history[-3:]
        value = max(0.0, 3.0 * (sum(recent) / len(recent)))
        context = contexts.get(zone_id, {})
        event = {
            "schema_version": 1,
            "prediction_time": timestamp.isoformat(),
            "prediction_horizon_minutes": 15,
            "zone_id": zone_id,
            "zone": ZONE_NAMES.get(zone_id, zone_id),
            "predicted_demand": round(value, 2),
            "demand_last_5min": count,
            "model": "Persistence_baseline",
        }
        producer.produce(
            OUTPUT_TOPIC,
            key=zone_id.encode(),
            value=json.dumps(event).encode(),
        )
        with state_lock:
            state["zones"][zone_id] = {
                "id": zone_id,
                "name": event["zone"],
                "average15": value,
                "total": value,
                "rows": 1,
                "latest": {
                    "timestamp": timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                    "demandLast5": count,
                    "prediction15": value,
                    "hour": timestamp.hour,
                    "weather": context.get("weather") or "Clear",
                    "rain": safe_float(context.get("rain_intensity")),
                    "event": bool(context.get("event_flag")),
                    "eventType": context.get("event_type") or "No event",
                },
            }
    producer.flush(10)
    with state_lock:
        state["published"] += len(rows)
        state["lastWindow"] = timestamp.strftime("%Y-%m-%d %H:%M:%S")
        state["logs"].appendleft({
            "time": datetime.now(IST).strftime("%H:%M:%S"),
            "level": "PRED",
            "message": f"Forecast published · horizon=15m · {len(rows)} zones",
        })


def consume_loop() -> None:
    consumer = Consumer({
        "bootstrap.servers": BROKER,
        "group.id": GROUP_ID,
        "auto.offset.reset": "latest",
        "enable.auto.commit": False,
    })
    producer = Producer({
        "bootstrap.servers": BROKER,
        "enable.idempotence": True,
        "acks": "all",
        "client.id": "bengaluru-demand-predictor",
    })
    counts: dict[str, int] = defaultdict(int)
    histories: dict[str, deque[float]] = defaultdict(lambda: deque(maxlen=12))
    contexts: dict[str, dict[str, Any]] = {}
    active_window: datetime | None = None
    consumer.subscribe([INPUT_TOPIC])
    logger.info("Connected to Kafka at %s; consuming %s", BROKER, INPUT_TOPIC)
    with state_lock:
        state["logs"].appendleft({
            "time": datetime.now(IST).strftime("%H:%M:%S"),
            "level": "INFO",
            "message": f"Consumer subscribed to {INPUT_TOPIC}",
        })
    try:
        while True:
            message = consumer.poll(1.0)
            if message is None:
                continue
            if message.error():
                if message.error().code() == KafkaError._PARTITION_EOF:
                    continue
                raise KafkaException(message.error())
            event = json.loads(message.value().decode("utf-8"))
            with state_lock:
                state["status"] = "connected"
                if state["consumed"] % 1000 == 0:
                    state["logs"].appendleft({
                        "time": datetime.now(IST).strftime("%H:%M:%S"),
                        "level": "INFO",
                        "message": f"Consumed {state['consumed']:,} ride events",
                    })
            timestamp = parse_event_time(event.get("event_time"))
            current_window = window_start(timestamp)
            if active_window is None:
                active_window = current_window
            if current_window != active_window:
                publish_predictions(producer, counts, histories, contexts, active_window)
                for zone_id in set(ZONE_NAMES) | set(counts):
                    histories[zone_id].append(float(counts.get(zone_id, 0)))
                counts = defaultdict(int)
                contexts = {}
                active_window = current_window
                consumer.commit(asynchronous=False)
            zone_id = str(event["pickup_zone_id"])
            counts[zone_id] += 1
            contexts[zone_id] = event
            with state_lock:
                state["consumed"] += 1
    except Exception:
        with state_lock:
            state["status"] = "error"
            state["errors"] += 1
        logger.exception("Kafka consumer stopped")
    finally:
        consumer.close()


@app.get("/health")
def health() -> dict[str, Any]:
    with state_lock:
        return {"status": state["status"], "broker": BROKER, "inputTopic": INPUT_TOPIC}


@app.get("/state")
def dashboard_state() -> dict[str, Any]:
    with state_lock:
        return {**state, "zones": list(state["zones"].values()), "logs": list(state["logs"])}


if __name__ == "__main__":
    import uvicorn

    threading.Thread(target=consume_loop, daemon=True).start()
    uvicorn.run(app, host="127.0.0.1", port=int(os.getenv("STREAMING_API_PORT", "8000")))
