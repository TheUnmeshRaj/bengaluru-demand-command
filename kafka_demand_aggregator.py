
import csv
import json
import time
import uuid
import argparse

from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

from confluent_kafka import Consumer, Producer


# ============================================================
# 1. CONFIGURATION
# ============================================================

KAFKA_SERVER = "127.0.0.1:9092"

SOURCE_TOPIC = "ride_requests"
OUTPUT_TOPIC = "zone_demand_5min"

# New group to replay the original 1,000 messages.
GROUP_ID = "ride-demand-aggregator-test-002"

DATASET_PATH = Path("rides_contextual_synthetic.csv")

WINDOW_MINUTES = 5

IST = timezone(timedelta(hours=5, minutes=30))

# Unique ID for identifying this aggregation run.
RUN_ID = uuid.uuid4().hex[:12]


# ============================================================
# 2. STATISTICS
# ============================================================

stats = {
    "delivered": 0,
    "failed": 0,
    "windows": 0
}


# ============================================================
# 3. LOAD ALL 52 PICKUP ZONES
# ============================================================

def load_zones():

    if not DATASET_PATH.exists():
        raise FileNotFoundError(
            f"Dataset not found: {DATASET_PATH.resolve()}"
        )

    zones = {}

    with DATASET_PATH.open(
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as file:

        reader = csv.DictReader(file)

        required_columns = {
            "Pickup_Zone_ID",
            "Pickup_Zone"
        }

        missing = required_columns - set(
            reader.fieldnames or []
        )

        if missing:
            raise ValueError(
                f"Missing dataset columns: {sorted(missing)}"
            )

        for row in reader:

            zone_id = str(
                row.get("Pickup_Zone_ID") or ""
            ).strip()

            zone_name = str(
                row.get("Pickup_Zone") or ""
            ).strip()

            if zone_id:
                zones[zone_id] = zone_name

            if len(zones) == 52:
                break

    if len(zones) != 52:
        raise ValueError(
            f"Expected 52 zones, found {len(zones)}."
        )

    return dict(sorted(zones.items()))


# ============================================================
# 4. PARSE EVENT TIMESTAMP
# ============================================================

def parse_event_time(timestamp):

    event_time = datetime.fromisoformat(
        str(timestamp)
    )

    # Dataset timestamps represent Bengaluru local time.
    if event_time.tzinfo is None:

        event_time = event_time.replace(
            tzinfo=IST
        )

    else:

        event_time = event_time.astimezone(IST)

    return event_time


# ============================================================
# 5. FIND THE START OF A 5-MINUTE WINDOW
# ============================================================

def get_window_start(event_time):

    minute = (
        event_time.minute // WINDOW_MINUTES
    ) * WINDOW_MINUTES

    return event_time.replace(
        minute=minute,
        second=0,
        microsecond=0
    )


# ============================================================
# 6. KAFKA DELIVERY CALLBACK
# ============================================================

def delivery_report(error, message):

    if error is not None:

        stats["failed"] += 1

        print(
            f"Delivery failed: {error}"
        )

    else:

        stats["delivered"] += 1


# ============================================================
# 7. PRODUCE AGGREGATED WINDOW
# ============================================================

def emit_window(
    window_start,
    window_counts,
    zones,
    output_producer
):

    window_end = window_start + timedelta(
        minutes=WINDOW_MINUTES
    )

    counts = window_counts.get(
        window_start,
        Counter()
    )

    rides_in_window = sum(counts.values())

    print(
        f"Producing window: "
        f"{window_start.strftime('%Y-%m-%d %H:%M')} "
        f"to {window_end.strftime('%H:%M')} "
        f"| Total rides: {rides_in_window}"
    )

    # Produce one record for every zone.
    for zone_id, zone_name in zones.items():

        ride_count = counts.get(
            zone_id,
            0
        )

        output_event = {

            "aggregation_run_id": RUN_ID,

            "window_start": window_start.isoformat(),
            "window_end": window_end.isoformat(),

            "pickup_zone_id": zone_id,
            "pickup_zone": zone_name,

            "ride_count": ride_count,

            "window_minutes": WINDOW_MINUTES
        }

        message_value = json.dumps(
            output_event,
            ensure_ascii=False
        ).encode("utf-8")

        message_key = zone_id.encode("utf-8")

        # Handle full producer queue.
        while True:

            try:

                output_producer.produce(
                    topic=OUTPUT_TOPIC,
                    key=message_key,
                    value=message_value,

                    timestamp=int(
                        window_end.timestamp() * 1000
                    ),

                    callback=delivery_report
                )

                break

            except BufferError:

                output_producer.poll(0.5)

        output_producer.poll(0)

    stats["windows"] += 1


# ============================================================
# 8. MAIN AGGREGATION FUNCTION
# ============================================================

def run_aggregation(max_messages, idle_timeout):

    zones = load_zones()

    print("\n==========================================")
    print("BENGALURU KAFKA DEMAND AGGREGATOR")
    print("==========================================")

    print(f"Kafka broker : {KAFKA_SERVER}")
    print(f"Input topic  : {SOURCE_TOPIC}")
    print(f"Output topic : {OUTPUT_TOPIC}")
    print(f"Consumer group: {GROUP_ID}")
    print(f"Zones        : {len(zones)}")
    print(f"Window       : {WINDOW_MINUTES} minutes")
    print(f"Run ID       : {RUN_ID}")

    print("\nInitializing Kafka consumer...")

    # --------------------------------------------------------
    # KAFKA CONSUMER
    # --------------------------------------------------------

    consumer = Consumer({

        "bootstrap.servers": KAFKA_SERVER,

        "client.id": "bengaluru-demand-consumer",

        "group.id": GROUP_ID,

        "auto.offset.reset": "earliest",

        "enable.auto.commit": False,

        "session.timeout.ms": 10000,

        "max.poll.interval.ms": 300000
    })

    # --------------------------------------------------------
    # KAFKA OUTPUT PRODUCER
    # --------------------------------------------------------

    print("Initializing Kafka output producer...")

    output_producer = Producer({

        "bootstrap.servers": KAFKA_SERVER,

        "client.id": "bengaluru-demand-aggregator",

        # Temporarily disabled to avoid the PID
        # allocation issue observed during testing.
        "enable.idempotence": False,

        "acks": "all",

        "retries": 3,

        "message.timeout.ms": 30000,

        "linger.ms": 5
    })

    print("Kafka producer initialized successfully.")

    # --------------------------------------------------------
    # VERIFY SOURCE TOPIC
    # --------------------------------------------------------

    metadata = consumer.list_topics(
        topic=SOURCE_TOPIC,
        timeout=10
    )

    if SOURCE_TOPIC not in metadata.topics:
        raise RuntimeError(
            f"Kafka topic {SOURCE_TOPIC} does not exist."
        )

    topic_info = metadata.topics[SOURCE_TOPIC]

    if topic_info.error is not None:
        raise RuntimeError(
            f"Cannot access source topic: {topic_info.error}"
        )

    partition_ids = sorted(
        topic_info.partitions.keys()
    )

    print(
        f"Source partitions: {partition_ids}"
    )

    # --------------------------------------------------------
    # SUBSCRIBE
    # --------------------------------------------------------

    consumer.subscribe([SOURCE_TOPIC])

    # Dictionary:
    # {
    #   window_start: {
    #       zone_id: ride_count
    #   }
    # }

    window_counts = defaultdict(Counter)

    processed = 0

    min_window = None
    max_window = None

    last_message_time = time.monotonic()

    # --------------------------------------------------------
    # READ RIDE EVENTS
    # --------------------------------------------------------

    print("\nStarting stream consumption...\n")

    try:

        while (
            max_messages == 0
            or processed < max_messages
        ):

            message = consumer.poll(1.0)

            # No message received.
            if message is None:

                elapsed = (
                    time.monotonic() - last_message_time
                )

                if elapsed >= idle_timeout:

                    if processed == 0:

                        raise TimeoutError(
                            "No ride messages received. "
                            "Check the source topic and consumer group."
                        )

                    if (
                        max_messages == 0
                        or processed < max_messages
                    ):

                        print(
                            "\nInput stream became idle. "
                            "Stopping this aggregation batch."
                        )

                    break

                continue

            if message.error():

                print(
                    f"Consumer error: {message.error()}"
                )

                continue

            try:

                event = json.loads(
                    message.value().decode("utf-8")
                )

                # Extract original event timestamp.
                event_time = parse_event_time(
                    event["event_time"]
                )

                zone_id = str(
                    event["pickup_zone_id"]
                )

                if zone_id not in zones:

                    raise ValueError(
                        f"Unknown pickup zone: {zone_id}"
                    )

                # Determine the corresponding time window.
                window_start = get_window_start(
                    event_time
                )

                # Track earliest and latest observed windows.
                if min_window is None:
                    min_window = window_start
                    max_window = window_start

                else:

                    min_window = min(
                        min_window,
                        window_start
                    )

                    max_window = max(
                        max_window,
                        window_start
                    )

                # Aggregate ride counts.
                window_counts[window_start][zone_id] += 1

                processed += 1

                last_message_time = time.monotonic()

                # Display progress.
                if processed % 100 == 0:

                    print(
                        f"Consumed {processed:,} "
                        f"ride events..."
                    )

            except (KeyError, ValueError, TypeError) as error:

                raise RuntimeError(
                    f"Invalid ride event at "
                    f"partition {message.partition()}, "
                    f"offset {message.offset()}: {error}"
                ) from error

        # ----------------------------------------------------
        # VALIDATE INPUT BATCH
        # ----------------------------------------------------

        print("\nInput consumption finished.")

        print(
            f"Total ride events consumed: {processed:,}"
        )

        if processed == 0:

            raise RuntimeError(
                "No ride events were consumed."
            )

        if (
            max_messages > 0
            and processed < max_messages
        ):

            raise RuntimeError(
                f"Expected {max_messages} messages, "
                f"but received only {processed}. "
                "No output was committed."
            )

        # ----------------------------------------------------
        # GENERATE ALL 5-MINUTE WINDOWS
        # ----------------------------------------------------

        print("\nPreparing 5-minute demand windows...")

        window_starts = []

        current_window = min_window

        while current_window <= max_window:

            window_starts.append(
                current_window
            )

            current_window += timedelta(
                minutes=WINDOW_MINUTES
            )

        print(
            f"Total time windows identified: "
            f"{len(window_starts)}"
        )

        # ----------------------------------------------------
        # PUBLISH ZONE-WISE AGGREGATIONS
        # ----------------------------------------------------

        print("\nPublishing aggregated demand to Kafka...\n")

        for window_start in window_starts:

            emit_window(
                window_start,
                window_counts,
                zones,
                output_producer
            )

        expected_records = (
            len(window_starts) * len(zones)
        )

        print("\nWaiting for Kafka acknowledgements...")

        remaining = output_producer.flush(30)

        # ----------------------------------------------------
        # DELIVERY VALIDATION
        # ----------------------------------------------------

        if remaining > 0:

            raise RuntimeError(
                f"{remaining} Kafka messages are still pending."
            )

        if stats["failed"] > 0:

            raise RuntimeError(
                f"{stats['failed']} aggregated messages failed delivery."
            )

        if stats["delivered"] != expected_records:

            raise RuntimeError(
                f"Expected {expected_records} output records, "
                f"but delivered {stats['delivered']}."
            )

        print("\nAll aggregated messages delivered successfully.")

        # ----------------------------------------------------
        # COMMIT CONSUMER OFFSETS
        # ----------------------------------------------------

        print("Committing consumer offsets...")

        consumer.commit(
            asynchronous=False
        )

        print("Consumer offsets committed successfully.")

        # ----------------------------------------------------
        # FINAL SUMMARY
        # ----------------------------------------------------

        print("\n==========================================")
        print("AGGREGATION SUMMARY")
        print("==========================================")

        print(f"Run ID              : {RUN_ID}")
        print(f"Ride events consumed: {processed:,}")
        print(f"Zones processed     : {len(zones)}")
        print(f"Windows aggregated  : {stats['windows']:,}")

        print(
            f"Expected output records: {expected_records:,}"
        )

        print(
            f"Successfully delivered: {stats['delivered']:,}"
        )

        print(
            f"Failed output records : {stats['failed']:,}"
        )

        print("==========================================")

        print("\nAGGREGATION COMPLETED SUCCESSFULLY.")

    finally:

        consumer.close()


# ============================================================
# 9. ENTRY POINT
# ============================================================

if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description=(
            "Aggregate Bengaluru ride requests "
            "into 5-minute zone-wise demand."
        )
    )

    parser.add_argument(
        "--max-messages",
        type=int,
        default=1000,
        help=(
            "Number of ride events to consume. "
            "Use 0 to consume until the stream becomes idle."
        )
    )

    parser.add_argument(
        "--idle-timeout",
        type=int,
        default=15,
        help="Seconds to wait without incoming messages."
    )

    args = parser.parse_args()

    if args.max_messages < 0:
        parser.error(
            "--max-messages cannot be negative."
        )

    if args.idle_timeout <= 0:
        parser.error(
            "--idle-timeout must be greater than zero."
        )

    run_aggregation(
        max_messages=args.max_messages,
        idle_timeout=args.idle_timeout
    )
