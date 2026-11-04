"""Validate the complete demand_predictions_ml topic from its beginning."""

from __future__ import annotations

import argparse
import json
import math
import time
import uuid
from datetime import datetime, timedelta, timezone

from confluent_kafka import Consumer
from confluent_kafka.admin import AdminClient


KAFKA_SERVER = "127.0.0.1:9092"
TOPIC = "demand_predictions_ml"
EXPECTED_ZONE_COUNT = 52
IST = timezone(timedelta(hours=5, minutes=30))


def parse_time(value: str) -> datetime:
    result = datetime.fromisoformat(str(value))
    return result.replace(tzinfo=IST) if result.tzinfo is None else result.astimezone(IST)


def validate_window(origin: datetime, zones_seen: set[str]) -> None:
    if len(zones_seen) != EXPECTED_ZONE_COUNT:
        raise RuntimeError(
            f"Origin {origin.isoformat()} contains {len(zones_seen)} unique zones; "
            f"expected {EXPECTED_ZONE_COUNT}."
        )


def main(idle_timeout: int) -> None:
    admin = AdminClient({"bootstrap.servers": KAFKA_SERVER})
    metadata = admin.list_topics(topic=TOPIC, timeout=10).topics.get(TOPIC)
    if metadata is None or metadata.error is not None:
        raise RuntimeError(f"Topic '{TOPIC}' is unavailable.")
    if len(metadata.partitions) != 1:
        raise RuntimeError(f"Expected one partition in {TOPIC}; found {len(metadata.partitions)}.")

    consumer = Consumer({
        "bootstrap.servers": KAFKA_SERVER,
        "client.id": "demand-prediction-verifier",
        "group.id": f"demand-prediction-verifier-{uuid.uuid4().hex[:8]}",
        "auto.offset.reset": "earliest",
        "enable.auto.commit": False,
    })
    consumer.subscribe([TOPIC])

    total_records = 0
    completed_windows = 0
    first_origin = None
    last_origin = None
    current_origin = None
    current_zones: set[str] = set()
    last_message_time = time.monotonic()

    print(f"Reading {TOPIC} from the beginning...")
    try:
        while True:
            message = consumer.poll(1.0)
            if message is None:
                if time.monotonic() - last_message_time >= idle_timeout:
                    break
                continue
            if message.error():
                raise RuntimeError(f"Kafka consumer error: {message.error()}")

            record = json.loads(message.value().decode("utf-8"))
            origin = parse_time(record["prediction_origin"])
            forecast_start = parse_time(record["forecast_start"])
            forecast_end = parse_time(record["forecast_end"])
            zone_id = str(record["pickup_zone_id"])
            prediction = float(record["predicted_demand_15min"])

            if forecast_start != origin:
                raise RuntimeError(f"Forecast start differs from origin at {origin.isoformat()}.")
            if forecast_end - origin != timedelta(minutes=15):
                raise RuntimeError(f"Incorrect forecast horizon at {origin.isoformat()}.")
            if not math.isfinite(prediction) or prediction < 0:
                raise RuntimeError(f"Invalid prediction for zone {zone_id}: {prediction}.")

            if current_origin is None:
                current_origin = origin
                first_origin = origin
            elif origin != current_origin:
                validate_window(current_origin, current_zones)
                completed_windows += 1
                expected = current_origin + timedelta(minutes=5)
                if origin != expected:
                    raise RuntimeError(
                        f"Non-consecutive prediction origins: expected {expected.isoformat()}, "
                        f"got {origin.isoformat()}."
                    )
                current_origin = origin
                current_zones = set()

            if zone_id in current_zones:
                raise RuntimeError(f"Duplicate prediction for {zone_id} at {origin.isoformat()}.")
            current_zones.add(zone_id)
            total_records += 1
            last_origin = origin
            last_message_time = time.monotonic()

            if total_records % 100_000 == 0:
                print(f"Validated {total_records:,} prediction records...")

        if current_origin is not None:
            validate_window(current_origin, current_zones)
            completed_windows += 1

        if total_records == 0:
            raise RuntimeError("No prediction records were found.")

        print("\n========== PREDICTION VALIDATION ==========")
        print(f"Total records       : {total_records:,}")
        print(f"Complete time windows: {completed_windows:,}")
        print(f"Zones per window    : {EXPECTED_ZONE_COUNT}")
        print(f"First prediction    : {first_origin.isoformat()}")
        print(f"Last prediction     : {last_origin.isoformat()}")
        print("Duplicates          : 0")
        print("Forecast horizon    : 15 minutes")
        print("SUCCESS: Prediction topic passed validation.")
    finally:
        consumer.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Validate Kafka demand predictions.")
    parser.add_argument("--idle-timeout", type=int, default=30)
    args = parser.parse_args()
    if args.idle_timeout <= 0:
        parser.error("--idle-timeout must be positive.")
    main(args.idle_timeout)
