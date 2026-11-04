"""Aggregate the clean ride_requests_ml topic into ordered 5-minute zone windows.

The output topic must have exactly one partition so that all 52 zone records
for a window, followed by the next window, have one global Kafka order. This
is a finite replay/batch stage, not a continuously running event-time engine.
"""

from __future__ import annotations

import argparse
import csv
import json
import time
import uuid
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from confluent_kafka import Consumer, Producer, TopicPartition
from confluent_kafka.admin import AdminClient


KAFKA_SERVER = "127.0.0.1:9092"
SOURCE_TOPIC = "ride_requests_ml"
OUTPUT_TOPIC = "zone_demand_5min_ml"
GROUP_ID = "ride-demand-aggregator-ml-v1"
DATASET_PATH = Path("rides_contextual_synthetic.csv")
WINDOW_MINUTES = 5
IST = timezone(timedelta(hours=5, minutes=30))
RUN_ID = uuid.uuid4().hex[:12]

stats = {"delivered": 0, "failed": 0}


def load_zones() -> dict[str, str]:
    if not DATASET_PATH.exists():
        raise FileNotFoundError(f"Dataset not found: {DATASET_PATH.resolve()}")
    zones: dict[str, str] = {}
    with DATASET_PATH.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        required = {"Pickup_Zone_ID", "Pickup_Zone"}
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"Missing dataset columns: {sorted(missing)}")
        for row in reader:
            zone_id = (row.get("Pickup_Zone_ID") or "").strip()
            zone_name = (row.get("Pickup_Zone") or "").strip()
            if zone_id:
                if zone_id in zones and zones[zone_id] != zone_name:
                    raise ValueError(f"Zone {zone_id} maps to multiple names.")
                zones[zone_id] = zone_name
    if len(zones) != 52:
        raise ValueError(f"Expected 52 unique zones, found {len(zones)}.")
    return dict(sorted(zones.items()))


def parse_event_time(value: str) -> datetime:
    dt = datetime.fromisoformat(str(value))
    if dt.tzinfo is None:
        return dt.replace(tzinfo=IST)
    return dt.astimezone(IST)


def get_window_start(event_time: datetime) -> datetime:
    minute = (event_time.minute // WINDOW_MINUTES) * WINDOW_MINUTES
    return event_time.replace(minute=minute, second=0, microsecond=0)


def assert_topic_is_empty(topic: str) -> None:
    admin = AdminClient({"bootstrap.servers": KAFKA_SERVER})
    metadata = admin.list_topics(topic=topic, timeout=10)
    info = metadata.topics.get(topic)
    if info is None:
        raise RuntimeError(f"Topic '{topic}' does not exist. Create it first.")
    if info.error is not None:
        raise RuntimeError(f"Cannot inspect topic '{topic}': {info.error}")
    checker = Consumer({
        "bootstrap.servers": KAFKA_SERVER,
        "group.id": f"topic-empty-check-{uuid.uuid4().hex[:8]}",
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
                f"Output topic '{topic}' is not empty: {non_empty}. "
                "Refusing to append a second aggregation run."
            )
    finally:
        checker.close()


def delivery_report(error, message) -> None:
    if error is not None:
        stats["failed"] += 1
    else:
        stats["delivered"] += 1


def emit_window(
    window_start: datetime,
    window_counts: dict[datetime, Counter],
    zones: dict[str, str],
    producer: Producer,
) -> None:
    window_end = window_start + timedelta(minutes=WINDOW_MINUTES)
    counts = window_counts.get(window_start, Counter())
    total_rides = sum(counts.values())

    for zone_id, zone_name in zones.items():
        record: dict[str, Any] = {
            "aggregation_run_id": RUN_ID,
            "window_start": window_start.isoformat(),
            "window_end": window_end.isoformat(),
            "pickup_zone_id": zone_id,
            "pickup_zone": zone_name,
            "ride_count": int(counts.get(zone_id, 0)),
            "window_minutes": WINDOW_MINUTES,
        }
        value = json.dumps(record, ensure_ascii=False).encode("utf-8")
        while True:
            try:
                producer.produce(
                    topic=OUTPUT_TOPIC,
                    key=zone_id.encode("utf-8"),
                    value=value,
                    timestamp=int(window_end.timestamp() * 1000),
                    callback=delivery_report,
                )
                break
            except BufferError:
                producer.poll(0.5)
        producer.poll(0)


def run_aggregation(max_messages: int, idle_timeout: int) -> None:
    zones = load_zones()
    assert_topic_is_empty(OUTPUT_TOPIC)

    admin = AdminClient({"bootstrap.servers": KAFKA_SERVER})
    output_meta = admin.list_topics(topic=OUTPUT_TOPIC, timeout=10).topics[OUTPUT_TOPIC]
    if len(output_meta.partitions) != 1:
        raise RuntimeError(
            f"{OUTPUT_TOPIC} must have exactly one partition; found {len(output_meta.partitions)}."
        )

    print("\n========== CLEAN ML DEMAND AGGREGATOR ==========")
    print(f"Source topic : {SOURCE_TOPIC}")
    print(f"Output topic : {OUTPUT_TOPIC} (1 partition)")
    print(f"Consumer group: {GROUP_ID}")
    print(f"Zones        : {len(zones)}")
    print(f"Run ID       : {RUN_ID}")

    consumer = Consumer({
        "bootstrap.servers": KAFKA_SERVER,
        "client.id": "bengaluru-demand-aggregator-ml-consumer",
        "group.id": GROUP_ID,
        "auto.offset.reset": "earliest",
        "enable.auto.commit": False,
        "session.timeout.ms": 30_000,
        "max.poll.interval.ms": 7_200_000,
    })
    producer = Producer({
        "bootstrap.servers": KAFKA_SERVER,
        "client.id": "bengaluru-demand-aggregator-ml-producer",
        "enable.idempotence": True,
        "acks": "all",
        "compression.type": "snappy",
        "linger.ms": 5,
        "message.timeout.ms": 120_000,
    })

    window_counts: dict[datetime, Counter] = defaultdict(Counter)
    processed = 0
    min_window: datetime | None = None
    max_window: datetime | None = None
    last_message_time = time.monotonic()
    consumer.subscribe([SOURCE_TOPIC])

    try:
        while max_messages == 0 or processed < max_messages:
            message = consumer.poll(1.0)
            if message is None:
                if time.monotonic() - last_message_time >= idle_timeout:
                    if processed == 0:
                        raise TimeoutError(
                            f"No messages received from {SOURCE_TOPIC}. Check the producer/topic."
                        )
                    break
                continue
            if message.error():
                raise RuntimeError(f"Kafka consumer error: {message.error()}")

            try:
                event = json.loads(message.value().decode("utf-8"))
                ride_id = str(event["ride_id"])
                if not ride_id:
                    raise ValueError("Empty ride_id")
                event_time = parse_event_time(event["event_time"])
                zone_id = str(event["pickup_zone_id"])
                if zone_id not in zones:
                    raise ValueError(f"Unknown pickup zone: {zone_id}")
                window_start = get_window_start(event_time)
                window_counts[window_start][zone_id] += 1
                min_window = window_start if min_window is None else min(min_window, window_start)
                max_window = window_start if max_window is None else max(max_window, window_start)
                processed += 1
                last_message_time = time.monotonic()
                if processed % 100_000 == 0:
                    print(f"Consumed {processed:,} ride events...")
            except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
                raise RuntimeError(
                    f"Invalid ride event at partition {message.partition()}, "
                    f"offset {message.offset()}: {exc}"
                ) from exc

        if processed == 0 or min_window is None or max_window is None:
            raise RuntimeError("No valid ride events were aggregated.")
        if max_messages > 0 and processed < max_messages:
            raise RuntimeError(
                f"Expected {max_messages} messages but received {processed}; refusing partial output."
            )

        # Match build_ml_dataset.py exactly: create the complete 5-minute
        # calendar from midnight on the first ride date through 23:55 on
        # the final ride date. This includes all-zero windows before the
        # first ride and after the last ride on those dates.
        first_day = min_window.replace(hour=0, minute=0, second=0, microsecond=0)
        last_day = max_window.replace(hour=0, minute=0, second=0, microsecond=0)
        final_window_start = last_day + timedelta(days=1) - timedelta(minutes=WINDOW_MINUTES)

        window_starts = []
        current = first_day
        while current <= final_window_start:
            window_starts.append(current)
            current += timedelta(minutes=WINDOW_MINUTES)

        print(f"\nRide events consumed : {processed:,}")
        print(f"Calendar start       : {first_day.isoformat()}")
        print(f"Calendar end         : {final_window_start.isoformat()}")
        print(f"5-minute windows     : {len(window_starts):,}")
        print(f"Expected output rows : {len(window_starts) * len(zones):,}")
        print("Publishing ordered zone-window records...")

        for index, window_start in enumerate(window_starts, start=1):
            emit_window(window_start, window_counts, zones, producer)
            if index % 500 == 0:
                print(f"Published windows queued: {index:,}/{len(window_starts):,}")

        pending = producer.flush(600)
        expected_records = len(window_starts) * len(zones)
        if pending > 0 or stats["failed"] > 0 or stats["delivered"] != expected_records:
            raise RuntimeError(
                f"Output delivery failed: expected={expected_records}, "
                f"delivered={stats['delivered']}, failed={stats['failed']}, pending={pending}."
            )

        consumer.commit(asynchronous=False)
        print("\n========== AGGREGATION SUMMARY ==========")
        print(f"Run ID               : {RUN_ID}")
        print(f"Ride events consumed : {processed:,}")
        print(f"Zones per window     : {len(zones)}")
        print(f"Windows              : {len(window_starts):,}")
        print(f"Output records       : {stats['delivered']:,}")
        print("Aggregation completed successfully.")
    finally:
        consumer.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Aggregate the clean ride topic into ordered 5-minute zone demand."
    )
    parser.add_argument("--max-messages", type=int, default=0,
                        help="Maximum source events; 0 consumes until the topic is idle (default).")
    parser.add_argument("--idle-timeout", type=int, default=30,
                        help="Seconds without new source messages before ending the batch.")
    args = parser.parse_args()
    if args.max_messages < 0:
        parser.error("--max-messages cannot be negative.")
    if args.idle_timeout <= 0:
        parser.error("--idle-timeout must be positive.")
    run_aggregation(args.max_messages, args.idle_timeout)
