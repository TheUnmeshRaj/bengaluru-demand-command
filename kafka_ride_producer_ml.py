"""Replay the synthetic Bengaluru ride dataset into a fresh Kafka topic.

This is an isolated ML experiment. It deliberately uses ride_requests_ml
rather than the earlier ride_requests topic, which already contains test data.
The producer refuses to append to a non-empty topic to prevent accidental
replays of the same Request_ID values.
"""

from __future__ import annotations

import argparse
import csv
import json
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

from confluent_kafka import Consumer, Producer, TopicPartition
from confluent_kafka.admin import AdminClient


KAFKA_SERVER = "127.0.0.1:9092"
TOPIC_NAME = "ride_requests_ml"
DATASET_PATH = Path("rides_contextual_synthetic.csv")
IST = timezone(timedelta(hours=5, minutes=30))

stats = {"delivered": 0, "failed": 0}


def to_float(value: Any) -> float | None:
    if value is None or str(value).strip() == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def to_int(value: Any) -> int | None:
    if value is None or str(value).strip() == "":
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def parse_dataset_timestamp(value: str) -> tuple[datetime, int]:
    dt = datetime.fromisoformat(value.strip())
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=IST)
    else:
        dt = dt.astimezone(IST)
    return dt, int(dt.timestamp() * 1000)


def assert_topic_is_empty(topic: str) -> None:
    """Fail safely when the dedicated replay topic already contains records."""
    admin = AdminClient({"bootstrap.servers": KAFKA_SERVER})
    metadata = admin.list_topics(topic=topic, timeout=10)
    topic_metadata = metadata.topics.get(topic)
    if topic_metadata is None:
        raise RuntimeError(
            f"Topic '{topic}' does not exist. Create it before running the producer."
        )
    if topic_metadata.error is not None:
        raise RuntimeError(f"Cannot inspect topic '{topic}': {topic_metadata.error}")

    checker = Consumer({
        "bootstrap.servers": KAFKA_SERVER,
        "group.id": f"topic-empty-check-{int(time.time())}",
        "enable.auto.commit": False,
    })
    try:
        non_empty = []
        for partition_id in sorted(topic_metadata.partitions):
            low, high = checker.get_watermark_offsets(
                TopicPartition(topic, partition_id),
                timeout=10,
                cached=False,
            )
            if high > low:
                non_empty.append((partition_id, low, high))
        if non_empty:
            raise RuntimeError(
                f"Topic '{topic}' is not empty: {non_empty}. "
                "Refusing to replay duplicate ride events. Use a newly created topic."
            )
    finally:
        checker.close()


def create_ride_event(row: dict[str, str]) -> tuple[dict[str, Any], int, datetime]:
    timestamp_text = row["Timestamp"].strip()
    event_dt, timestamp_ms = parse_dataset_timestamp(timestamp_text)

    ride_id = row["Request_ID"].strip()
    zone_id = row["Pickup_Zone_ID"].strip()
    if not ride_id:
        raise ValueError("Encountered an empty Request_ID.")
    if not zone_id:
        raise ValueError(f"Ride {ride_id} has an empty Pickup_Zone_ID.")

    event = {
        "schema_version": 1,
        "ride_id": ride_id,
        "event_time": timestamp_text,
        "timezone": "Asia/Kolkata",
        "pickup_zone_id": zone_id,
        "pickup_zone": row["Pickup_Zone"].strip(),
        "drop_zone_id": row["Drop_Zone_ID"].strip(),
        "drop_zone": row["Drop_Zone"].strip(),
        "vehicle_type": row["Vehicle_Type"].strip(),
        "ride_distance_km": to_float(row.get("Ride_Distance_KM")),
        "weather": row.get("Weather"),
        "rain_intensity": to_float(row.get("Rain_Intensity")),
        "event_flag": row.get("Event_Flag"),
        "simulated_event_id": row.get("Event_ID"),
        "event_type": row.get("Event_Type"),
        "event_phase": row.get("Event_Phase"),
        "event_intensity": to_int(row.get("Event_Intensity")),
    }
    return event, timestamp_ms, event_dt


def delivery_report(error, message) -> None:
    if error is not None:
        stats["failed"] += 1
    else:
        stats["delivered"] += 1

    completed = stats["delivered"] + stats["failed"]
    if completed and completed % 50_000 == 0:
        print(
            f"Delivery callbacks: {completed:,} | "
            f"Delivered: {stats['delivered']:,} | Failed: {stats['failed']:,}"
        )


def publish_rides(limit: int, speedup: float, max_sleep: float) -> None:
    if not DATASET_PATH.exists():
        raise FileNotFoundError(f"Dataset not found: {DATASET_PATH.resolve()}")

    print("\n========== KAFKA RIDE PRODUCER (CLEAN ML RUN) ==========")
    print(f"Dataset: {DATASET_PATH.resolve()}")
    print(f"Broker : {KAFKA_SERVER}")
    print(f"Topic  : {TOPIC_NAME}")
    print(f"Limit  : {'all rows' if limit == 0 else f'{limit:,} rows'}")
    print(f"Speed  : {'no delay' if speedup == 0 else f'{speedup:g}x'}")

    assert_topic_is_empty(TOPIC_NAME)

    producer = Producer({
        "bootstrap.servers": KAFKA_SERVER,
        "client.id": "bengaluru-ride-replay-producer-ml",
        "enable.idempotence": True,
        "acks": "all",
        "compression.type": "snappy",
        "linger.ms": 10,
        "message.timeout.ms": 120_000,
    })

    processed = 0
    previous_timestamp: datetime | None = None
    required_columns = {
        "Request_ID", "Timestamp", "Pickup_Zone_ID", "Pickup_Zone",
        "Drop_Zone_ID", "Drop_Zone", "Vehicle_Type", "Ride_Distance_KM",
    }

    with DATASET_PATH.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        missing = required_columns - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"Missing CSV columns: {sorted(missing)}")

        for row in reader:
            if limit > 0 and processed >= limit:
                break

            event, timestamp_ms, current_timestamp = create_ride_event(row)
            if previous_timestamp is not None and current_timestamp < previous_timestamp:
                raise ValueError(
                    "Dataset is not chronologically sorted: "
                    f"{current_timestamp.isoformat()} follows "
                    f"{previous_timestamp.isoformat()}."
                )

            if previous_timestamp is not None and speedup > 0:
                gap_seconds = (current_timestamp - previous_timestamp).total_seconds()
                delay = min(max(gap_seconds, 0.0) / speedup, max_sleep)
                if delay > 0:
                    time.sleep(delay)

            payload = json.dumps(event, ensure_ascii=False).encode("utf-8")
            key = event["pickup_zone_id"].encode("utf-8")

            while True:
                try:
                    producer.produce(
                        topic=TOPIC_NAME,
                        key=key,
                        value=payload,
                        timestamp=timestamp_ms,
                        callback=delivery_report,
                    )
                    break
                except BufferError:
                    producer.poll(0.5)

            processed += 1
            previous_timestamp = current_timestamp
            producer.poll(0)

            if processed % 50_000 == 0:
                print(f"Read and queued {processed:,} ride events...")

    print("Waiting for Kafka acknowledgements...")
    remaining = producer.flush(300)

    print("\n========== PRODUCER SUMMARY ==========")
    print(f"Rows processed : {processed:,}")
    print(f"Delivered      : {stats['delivered']:,}")
    print(f"Failed         : {stats['failed']:,}")
    print(f"Pending        : {remaining:,}")

    if processed == 0:
        raise RuntimeError("No ride rows were read from the dataset.")
    if remaining > 0 or stats["failed"] > 0 or stats["delivered"] != processed:
        raise RuntimeError("Producer delivery validation failed; do not start aggregation.")

    print("Producer completed successfully. Do not run it again on this topic.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Replay synthetic Bengaluru rides into the clean ML Kafka topic."
    )
    parser.add_argument("--limit", type=int, default=0,
                        help="Rows to publish; 0 means the entire CSV (default).")
    parser.add_argument("--speedup", type=float, default=0,
                        help="Replay speed multiplier; 0 means no artificial delay (default).")
    parser.add_argument("--max-sleep", type=float, default=0.02,
                        help="Maximum delay per adjacent record when speedup is enabled.")
    args = parser.parse_args()
    if args.limit < 0:
        parser.error("--limit cannot be negative.")
    if args.speedup < 0:
        parser.error("--speedup cannot be negative.")
    if args.max_sleep < 0:
        parser.error("--max-sleep cannot be negative.")
    publish_rides(args.limit, args.speedup, args.max_sleep)
