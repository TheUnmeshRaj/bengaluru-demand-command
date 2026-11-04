"""Consume ordered 5-minute zone demand and publish 15-minute XGBoost forecasts.

Input topic:  zone_demand_5min_ml (must have one partition)
Output topic: demand_predictions_ml
Model:        ml_results/models/XGBoost_historical.joblib

The feature definitions below reproduce build_ml_dataset.py and train_model.py.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import time
import uuid
from collections import deque
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from confluent_kafka import Consumer, Producer, TopicPartition
from confluent_kafka.admin import AdminClient


KAFKA_SERVER = "127.0.0.1:9092"
INPUT_TOPIC = "zone_demand_5min_ml"
OUTPUT_TOPIC = "demand_predictions_ml"
CONSUMER_GROUP = "ride-demand-ml-inference-v1"
DATASET_PATH = Path("rides_contextual_synthetic.csv")
MODEL_PATH = Path("ml_results/models/XGBoost_historical.joblib")
WINDOW_MINUTES = 5
FORECAST_MINUTES = 15
HISTORY_SIZE = 13  # Current interval plus the 12-interval (60-minute) lag.
IST = timezone(timedelta(hours=5, minutes=30))
PREDICTION_RUN_ID = uuid.uuid4().hex[:12]

FEATURE_COLUMNS = [
    "Hour",
    "Day_Of_Week",
    "Is_Weekend",
    "Hour_Sin",
    "Hour_Cos",
    "DayOfWeek_Sin",
    "DayOfWeek_Cos",
    "Demand_Last_5min",
    "Demand_Lag_5min",
    "Demand_Lag_10min",
    "Demand_Lag_15min",
    "Demand_Lag_30min",
    "Demand_Lag_60min",
    "Rolling_Mean_15min",
    "Rolling_Mean_30min",
    "Rolling_Mean_60min",
    "Zone_ID",
]

stats = {"predictions_delivered": 0, "predictions_failed": 0, "windows_predicted": 0}


def parse_timestamp(value: str) -> datetime:
    dt = datetime.fromisoformat(str(value))
    if dt.tzinfo is None:
        return dt.replace(tzinfo=IST)
    return dt.astimezone(IST)


def load_zones() -> dict[str, str]:
    if not DATASET_PATH.exists():
        raise FileNotFoundError(f"Dataset not found: {DATASET_PATH.resolve()}")
    zones: dict[str, str] = {}
    with DATASET_PATH.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        for row in reader:
            zone_id = (row.get("Pickup_Zone_ID") or "").strip()
            zone_name = (row.get("Pickup_Zone") or "").strip()
            if zone_id:
                if zone_id in zones and zones[zone_id] != zone_name:
                    raise ValueError(f"Zone {zone_id} maps to multiple names.")
                zones[zone_id] = zone_name
    if len(zones) != 52:
        raise ValueError(f"Expected 52 zones in dataset, found {len(zones)}.")
    return dict(sorted(zones.items()))


def assert_output_topic_is_empty(topic: str) -> None:
    admin = AdminClient({"bootstrap.servers": KAFKA_SERVER})
    metadata = admin.list_topics(topic=topic, timeout=10)
    info = metadata.topics.get(topic)
    if info is None:
        raise RuntimeError(f"Topic '{topic}' does not exist. Create it first.")
    if info.error is not None:
        raise RuntimeError(f"Cannot inspect topic '{topic}': {info.error}")
    checker = Consumer({
        "bootstrap.servers": KAFKA_SERVER,
        "group.id": f"prediction-topic-check-{uuid.uuid4().hex[:8]}",
        "enable.auto.commit": False,
    })
    try:
        non_empty = []
        for partition_id in sorted(info.partitions):
            low, high = checker.get_watermark_offsets(
                TopicPartition(topic, partition_id), timeout=10, cached=False
            )
            if high > low:
                non_empty.append((partition_id, low, high))
        if non_empty:
            raise RuntimeError(
                f"Prediction topic '{topic}' is not empty: {non_empty}. "
                "Refusing to append a second prediction run."
            )
    finally:
        checker.close()


def build_feature_row(
    zone_id: str,
    prediction_origin: datetime,
    history: deque[int],
) -> dict[str, Any]:
    if len(history) != HISTORY_SIZE:
        raise ValueError(f"Zone {zone_id} has {len(history)} history values, expected {HISTORY_SIZE}.")

    hour = prediction_origin.hour
    day_of_week = prediction_origin.weekday()  # Monday=0, Sunday=6.
    hour_angle = 2.0 * math.pi * hour / 24.0
    weekday_angle = 2.0 * math.pi * day_of_week / 7.0
    values = list(history)

    return {
        "Hour": hour,
        "Day_Of_Week": day_of_week,
        "Is_Weekend": int(day_of_week in (5, 6)),
        "Hour_Sin": math.sin(hour_angle),
        "Hour_Cos": math.cos(hour_angle),
        "DayOfWeek_Sin": math.sin(weekday_angle),
        "DayOfWeek_Cos": math.cos(weekday_angle),
        "Demand_Last_5min": values[-1],
        "Demand_Lag_5min": values[-2],
        "Demand_Lag_10min": values[-3],
        "Demand_Lag_15min": values[-4],
        "Demand_Lag_30min": values[-7],
        "Demand_Lag_60min": values[-13],
        "Rolling_Mean_15min": float(np.mean(values[-3:])),
        "Rolling_Mean_30min": float(np.mean(values[-6:])),
        "Rolling_Mean_60min": float(np.mean(values[-12:])),
        "Zone_ID": str(zone_id),
    }


def prediction_delivery_report(error, message) -> None:
    if error is not None:
        stats["predictions_failed"] += 1
    else:
        stats["predictions_delivered"] += 1


def process_complete_window(
    window_end: datetime,
    records_by_zone: dict[str, dict[str, Any]],
    zones: dict[str, str],
    histories: dict[str, deque[int]],
    model,
    output_producer: Producer,
) -> None:
    expected_zones = set(zones)
    actual_zones = set(records_by_zone)
    if actual_zones != expected_zones:
        missing = sorted(expected_zones - actual_zones)
        extra = sorted(actual_zones - expected_zones)
        raise RuntimeError(f"Incomplete zone window. Missing={missing}; extra={extra}")

    feature_rows = []
    for zone_id in zones:
        count = int(records_by_zone[zone_id]["ride_count"])
        if count < 0:
            raise ValueError(f"Negative ride_count for zone {zone_id}: {count}")
        histories[zone_id].append(count)

    # Do not predict until every zone has 13 completed interval observations.
    if any(len(histories[zone_id]) < HISTORY_SIZE for zone_id in zones):
        return

    for zone_id in zones:
        feature_rows.append(build_feature_row(zone_id, window_end, histories[zone_id]))

    X = pd.DataFrame(feature_rows, columns=FEATURE_COLUMNS)
    predictions = np.asarray(model.predict(X), dtype=float).reshape(-1)
    if len(predictions) != len(zones):
        raise RuntimeError(f"Model returned {len(predictions)} predictions for {len(zones)} zones.")

    forecast_end = window_end + timedelta(minutes=FORECAST_MINUTES)
    for zone_id, raw_prediction in zip(zones, predictions):
        if not np.isfinite(raw_prediction):
            raise ValueError(f"Model produced a non-finite prediction for zone {zone_id}.")
        nonnegative_prediction = max(0.0, float(raw_prediction))
        rounded_prediction = int(math.floor(nonnegative_prediction + 0.5))
        record = {
            "prediction_run_id": PREDICTION_RUN_ID,
            "aggregation_run_id": records_by_zone[zone_id].get("aggregation_run_id"),
            "prediction_origin": window_end.isoformat(),
            "forecast_start": window_end.isoformat(),
            "forecast_end": forecast_end.isoformat(),
            "forecast_horizon_minutes": FORECAST_MINUTES,
            "pickup_zone_id": zone_id,
            "pickup_zone": zones[zone_id],
            "predicted_demand_15min": nonnegative_prediction,
            "predicted_demand_rounded": rounded_prediction,
            "model_file": MODEL_PATH.name,
            "observed_demand_last_5min": int(histories[zone_id][-1]),
        }
        payload = json.dumps(record, ensure_ascii=False).encode("utf-8")
        while True:
            try:
                output_producer.produce(
                    topic=OUTPUT_TOPIC,
                    key=zone_id.encode("utf-8"),
                    value=payload,
                    timestamp=int(window_end.timestamp() * 1000),
                    callback=prediction_delivery_report,
                )
                break
            except BufferError:
                output_producer.poll(0.5)
        output_producer.poll(0)

    stats["windows_predicted"] += 1
    if stats["windows_predicted"] % 100 == 0:
        print(
            f"Prediction windows: {stats['windows_predicted']:,} | "
            f"Prediction records queued: "
            f"{stats['windows_predicted'] * len(zones):,}"
        )


def run_inference(idle_timeout: int, max_windows: int) -> None:
    zones = load_zones()
    if not MODEL_PATH.exists():
        raise FileNotFoundError(f"Model not found: {MODEL_PATH.resolve()}")
    assert_output_topic_is_empty(OUTPUT_TOPIC)

    model = joblib.load(MODEL_PATH)
    model_features = getattr(model, "feature_names_in_", None)
    if model_features is not None and list(model_features) != FEATURE_COLUMNS:
        raise RuntimeError(
            "Saved model feature order does not match this inference code.\n"
            f"Model: {list(model_features)}\nCode:  {FEATURE_COLUMNS}"
        )
    model_feature_count = getattr(model, "n_features_in_", None)
    if model_feature_count is not None and int(model_feature_count) != len(FEATURE_COLUMNS):
        raise RuntimeError(
            f"Model expects {model_feature_count} features; code supplies {len(FEATURE_COLUMNS)}."
        )

    admin = AdminClient({"bootstrap.servers": KAFKA_SERVER})
    input_meta = admin.list_topics(topic=INPUT_TOPIC, timeout=10).topics.get(INPUT_TOPIC)
    if input_meta is None or input_meta.error is not None:
        raise RuntimeError(f"Input topic '{INPUT_TOPIC}' is unavailable.")
    if len(input_meta.partitions) != 1:
        raise RuntimeError(
            f"{INPUT_TOPIC} must have exactly one partition for ordered window processing; "
            f"found {len(input_meta.partitions)}."
        )

    consumer = Consumer({
        "bootstrap.servers": KAFKA_SERVER,
        "client.id": "bengaluru-xgboost-inference-consumer",
        "group.id": CONSUMER_GROUP,
        "auto.offset.reset": "earliest",
        "enable.auto.commit": False,
        "session.timeout.ms": 30_000,
        "max.poll.interval.ms": 7_200_000,
    })
    output_producer = Producer({
        "bootstrap.servers": KAFKA_SERVER,
        "client.id": "bengaluru-xgboost-prediction-producer",
        "enable.idempotence": True,
        "acks": "all",
        "compression.type": "snappy",
        "linger.ms": 5,
        "message.timeout.ms": 120_000,
    })

    histories = {zone_id: deque(maxlen=HISTORY_SIZE) for zone_id in zones}
    current_window_end: datetime | None = None
    current_records: dict[str, dict[str, Any]] = {}
    previous_completed_window: datetime | None = None
    input_records = 0
    last_message_time = time.monotonic()
    consumer.subscribe([INPUT_TOPIC])

    print("\n========== XGBOOST KAFKA INFERENCE ==========")
    print(f"Input topic : {INPUT_TOPIC}")
    print(f"Output topic: {OUTPUT_TOPIC}")
    print(f"Model       : {MODEL_PATH}")
    print(f"Zones       : {len(zones)}")
    print(f"Feature count: {len(FEATURE_COLUMNS)}")
    print("Waiting for ordered 5-minute zone windows...")

    try:
        while max_windows == 0 or stats["windows_predicted"] < max_windows:
            message = consumer.poll(1.0)
            if message is None:
                if time.monotonic() - last_message_time >= idle_timeout:
                    if input_records == 0:
                        raise TimeoutError(f"No records received from {INPUT_TOPIC}.")
                    break
                continue
            if message.error():
                raise RuntimeError(f"Kafka consumer error: {message.error()}")

            try:
                record = json.loads(message.value().decode("utf-8"))
                window_end = parse_timestamp(record["window_end"])
                zone_id = str(record["pickup_zone_id"])
                if zone_id not in zones:
                    raise ValueError(f"Unknown zone in demand topic: {zone_id}")
                if zone_id in current_records and current_window_end == window_end:
                    raise ValueError(f"Duplicate zone record for {zone_id} at {window_end.isoformat()}.")

                if current_window_end is None:
                    current_window_end = window_end
                elif window_end != current_window_end:
                    if len(current_records) != len(zones):
                        raise RuntimeError(
                            f"Window {current_window_end.isoformat()} ended with "
                            f"{len(current_records)}/{len(zones)} zones."
                        )
                    if previous_completed_window is not None:
                        expected_next = previous_completed_window + timedelta(minutes=WINDOW_MINUTES)
                        if current_window_end != expected_next:
                            raise RuntimeError(
                                f"Non-consecutive windows: expected {expected_next.isoformat()}, "
                                f"got {current_window_end.isoformat()}."
                            )
                    process_complete_window(
                        current_window_end, current_records, zones, histories, model, output_producer
                    )
                    previous_completed_window = current_window_end
                    current_window_end = window_end
                    current_records = {}

                if window_end != current_window_end:
                    raise RuntimeError("Window ordering changed unexpectedly.")

                current_records[zone_id] = record
                input_records += 1
                last_message_time = time.monotonic()

                if len(current_records) == len(zones):
                    if previous_completed_window is not None:
                        expected_next = previous_completed_window + timedelta(minutes=WINDOW_MINUTES)
                        if current_window_end != expected_next:
                            raise RuntimeError(
                                f"Non-consecutive windows: expected {expected_next.isoformat()}, "
                                f"got {current_window_end.isoformat()}."
                            )
                    process_complete_window(
                        current_window_end, current_records, zones, histories, model, output_producer
                    )
                    previous_completed_window = current_window_end
                    current_window_end = None
                    current_records = {}

                if input_records % 100_000 == 0:
                    print(f"Consumed {input_records:,} zone-demand records...")

            except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
                raise RuntimeError(
                    f"Invalid demand record at partition {message.partition()}, "
                    f"offset {message.offset()}: {exc}"
                ) from exc

        if current_records:
            raise RuntimeError(
                f"Input ended with an incomplete final window: "
                f"{len(current_records)}/{len(zones)} zones."
            )

        pending = output_producer.flush(600)
        expected_predictions = stats["windows_predicted"] * len(zones)
        if pending > 0 or stats["predictions_failed"] > 0 or stats["predictions_delivered"] != expected_predictions:
            raise RuntimeError(
                f"Prediction delivery failed: expected={expected_predictions}, "
                f"delivered={stats['predictions_delivered']}, "
                f"failed={stats['predictions_failed']}, pending={pending}."
            )

        consumer.commit(asynchronous=False)
        print("\n========== INFERENCE SUMMARY ==========")
        print(f"Input demand records : {input_records:,}")
        print(f"Complete windows read: {input_records // len(zones):,}")
        print(f"Prediction windows   : {stats['windows_predicted']:,}")
        print(f"Prediction records   : {stats['predictions_delivered']:,}")
        print("Inference completed successfully.")
    finally:
        consumer.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate 15-minute zone demand predictions using the trained XGBoost pipeline."
    )
    parser.add_argument("--idle-timeout", type=int, default=30,
                        help="Seconds without input records before finishing the replay.")
    parser.add_argument("--max-windows", type=int, default=0,
                        help="Maximum complete windows to predict; 0 means all windows.")
    args = parser.parse_args()
    if args.idle_timeout <= 0:
        parser.error("--idle-timeout must be positive.")
    if args.max_windows < 0:
        parser.error("--max-windows cannot be negative.")
    run_inference(args.idle_timeout, args.max_windows)
