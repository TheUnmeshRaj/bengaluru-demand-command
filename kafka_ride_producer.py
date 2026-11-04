
import csv
import json
import time
import argparse
import os
from pathlib import Path
from datetime import datetime, timezone, timedelta

from confluent_kafka import Producer


# ==================================================
# CONFIGURATION
# ==================================================

KAFKA_SERVER = os.getenv("KAFKA_BROKER", "localhost:9092")
TOPIC_NAME = os.getenv("KAFKA_INPUT_TOPIC", "ride_requests")
LOG_TOPIC = os.getenv("KAFKA_LOG_TOPIC", "pipeline_logs")

DATASET_PATH = Path(os.getenv("RIDE_DATASET_PATH", "rides_contextual_synthetic.csv"))

INDIA_TIMEZONE = timezone(timedelta(hours=5, minutes=30))


# ==================================================
# PRODUCER STATISTICS
# ==================================================

stats = {
    "delivered": 0,
    "failed": 0
}


# ==================================================
# HELPER FUNCTIONS
# ==================================================

def to_float(value):
    if value is None or value.strip() == "":
        return None

    try:
        return float(value)
    except ValueError:
        return None


def to_int(value):
    if value is None or value.strip() == "":
        return None

    try:
        return int(float(value))
    except ValueError:
        return None


# ==================================================
# DELIVERY CALLBACK
# ==================================================

def delivery_report(error, message):

    if error is not None:
        stats["failed"] += 1
        print(f"Delivery failed: {error}")

    else:
        stats["delivered"] += 1

    total = stats["delivered"] + stats["failed"]

    if total % 10000 == 0:
        print(
            f"Delivered: {stats['delivered']:,} | "
            f"Failed: {stats['failed']:,}"
        )


# ==================================================
# CREATE KAFKA PRODUCER
# ==================================================

producer = Producer({
    "bootstrap.servers": KAFKA_SERVER,
    "client.id": "bengaluru-ride-replay-producer",

    "enable.idempotence": True,
    "acks": "all",

    "compression.type": "snappy",
    "linger.ms": 10
})


def publish_pipeline_log(level, message):
    producer.produce(
        topic=LOG_TOPIC,
        key=b"producer",
        value=json.dumps({
            "service": "producer",
            "level": level,
            "message": message,
        }).encode("utf-8"),
    )
    producer.poll(0)


# ==================================================
# CONVERT CSV ROW INTO JSON EVENT
# ==================================================

def create_ride_event(row):

    timestamp_text = row["Timestamp"].strip()

    event_timestamp = datetime.fromisoformat(timestamp_text)

    # Dataset timestamps represent Bengaluru local time.
    if event_timestamp.tzinfo is None:
        event_timestamp = event_timestamp.replace(
            tzinfo=INDIA_TIMEZONE
        )

    event = {
        "schema_version": 1,

        "ride_id": row["Request_ID"],
        "event_time": timestamp_text,
        "timezone": "Asia/Kolkata",

        "pickup_zone_id": row["Pickup_Zone_ID"],
        "pickup_zone": row["Pickup_Zone"],

        "drop_zone_id": row["Drop_Zone_ID"],
        "drop_zone": row["Drop_Zone"],

        "vehicle_type": row["Vehicle_Type"],

        "ride_distance_km": to_float(
            row.get("Ride_Distance_KM")
        ),

        "weather": row.get("Weather"),

        "rain_intensity": to_float(
            row.get("Rain_Intensity")
        ),

        "event_flag": row.get("Event_Flag"),

        "simulated_event_id": row.get("Event_ID"),

        "event_type": row.get("Event_Type"),

        "event_phase": row.get("Event_Phase"),

        "event_intensity": to_int(
            row.get("Event_Intensity")
        )
    }

    timestamp_ms = int(
        event_timestamp.timestamp() * 1000
    )

    return event, timestamp_ms, event_timestamp


# ==================================================
# PUBLISH RIDE EVENTS
# ==================================================

def publish_rides(limit, speedup, max_sleep):

    if not DATASET_PATH.exists():
        raise FileNotFoundError(
            f"Dataset not found: {DATASET_PATH.resolve()}"
        )

    print("\n================================")
    print("BENGALURU KAFKA RIDE PRODUCER")
    print("================================")

    print(f"Dataset: {DATASET_PATH}")
    print(f"Kafka broker: {KAFKA_SERVER}")
    print(f"Topic: {TOPIC_NAME}")
    print(f"Record limit: {limit}")
    print(f"Replay speed: {speedup}x")
    publish_pipeline_log("INFO", f"Producer started · topic={TOPIC_NAME} · limit={limit:,}")

    processed = 0
    previous_timestamp = None

    with DATASET_PATH.open(
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as file:

        reader = csv.DictReader(file)

        required_columns = {
            "Request_ID",
            "Timestamp",
            "Pickup_Zone_ID",
            "Pickup_Zone",
            "Drop_Zone_ID",
            "Drop_Zone",
            "Vehicle_Type",
            "Ride_Distance_KM"
        }

        missing = required_columns - set(
            reader.fieldnames or []
        )

        if missing:
            raise ValueError(
                f"Missing CSV columns: {sorted(missing)}"
            )

        for row in reader:

            if limit > 0 and processed >= limit:
                break

            event, timestamp_ms, current_timestamp = (
                create_ride_event(row)
            )

            # Verify chronological order.
            if (
                previous_timestamp is not None
                and current_timestamp < previous_timestamp
            ):
                raise ValueError(
                    "Dataset is not chronologically sorted."
                )

            # Replay pacing.
            if previous_timestamp is not None and speedup > 0:

                time_gap = (
                    current_timestamp - previous_timestamp
                ).total_seconds()

                delay = min(
                    max(time_gap, 0) / speedup,
                    max_sleep
                )

                if delay > 0:
                    time.sleep(delay)

            # Convert event into JSON bytes.
            message_value = json.dumps(
                event,
                ensure_ascii=False
            ).encode("utf-8")

            # Pickup zone is used as the partition key.
            message_key = (
                event["pickup_zone_id"].encode("utf-8")
            )

            # Publish to Kafka.
            while True:
                try:
                    producer.produce(
                        topic=TOPIC_NAME,
                        key=message_key,
                        value=message_value,
                        timestamp=timestamp_ms,
                        callback=delivery_report
                    )
                    break

                except BufferError:
                    producer.poll(0.5)

            processed += 1
            previous_timestamp = current_timestamp

            producer.poll(0)

            if processed % 10000 == 0:
                print(
                    f"Processed {processed:,} ride events"
                )
                publish_pipeline_log("INFO", f"Producer delivered {processed:,} ride events")

    print("\nWaiting for Kafka acknowledgements...")

    remaining = producer.flush(60)

    print("\n================================")
    print("PRODUCER SUMMARY")
    print("================================")

    print(f"Records processed : {processed:,}")
    print(f"Successfully sent : {stats['delivered']:,}")
    print(f"Failed messages   : {stats['failed']:,}")
    print(f"Pending messages  : {remaining:,}")
    publish_pipeline_log("INFO", f"Producer finished · delivered={stats['delivered']:,} · failed={stats['failed']:,}")
    producer.flush(10)

    print("================================")

    if remaining > 0 or stats["failed"] > 0:
        raise RuntimeError(
            "Kafka delivery was not completely successful."
        )

    print("\nStreaming completed successfully.")


# ==================================================
# MAIN
# ==================================================

if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description="Stream synthetic Bengaluru ride events into Kafka."
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=1000,
        help="Number of rides. Use 0 for the complete dataset."
    )

    parser.add_argument(
        "--speedup",
        type=float,
        default=3600,
        help="Replay speed multiplier. Use 0 for no delay."
    )

    parser.add_argument(
        "--max-sleep",
        type=float,
        default=0.02,
        help="Maximum delay between consecutive records in seconds."
    )

    args = parser.parse_args()

    if args.limit < 0:
        parser.error("--limit cannot be negative.")

    if args.speedup < 0:
        parser.error("--speedup cannot be negative.")

    if args.max_sleep < 0:
        parser.error("--max-sleep cannot be negative.")

    publish_rides(
        limit=args.limit,
        speedup=args.speedup,
        max_sleep=args.max_sleep
    )
