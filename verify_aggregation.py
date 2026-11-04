
import json
from collections import defaultdict

from confluent_kafka import (
    Consumer,
    TopicPartition,
    KafkaError,
    OFFSET_BEGINNING
)

BROKER = "127.0.0.1:9092"
TOPIC = "zone_demand_5min"

# Successful aggregation run from your terminal
RUN_ID = "e83dd88caf2a"


consumer = Consumer({
    "bootstrap.servers": BROKER,
    "group.id": "aggregation-output-audit",
    "enable.auto.commit": False,
    "enable.partition.eof": True
})

metadata = consumer.list_topics(
    topic=TOPIC,
    timeout=10
)

topic_info = metadata.topics[TOPIC]

if topic_info.error is not None:
    raise RuntimeError(topic_info.error)

partitions = [
    TopicPartition(TOPIC, pid, OFFSET_BEGINNING)
    for pid in sorted(topic_info.partitions)
]

consumer.assign(partitions)

window_zones = defaultdict(set)
window_ride_totals = defaultdict(int)

records_found = 0
duplicates = 0

seen_records = set()
eof_partitions = set()

print("Verifying aggregation run:", RUN_ID)

while len(eof_partitions) < len(partitions):

    message = consumer.poll(2.0)

    if message is None:
        continue

    if message.error():

        if message.error().code() == KafkaError._PARTITION_EOF:
            eof_partitions.add(message.partition())
            continue

        raise RuntimeError(message.error())

    event = json.loads(
        message.value().decode("utf-8")
    )

    if event.get("aggregation_run_id") != RUN_ID:
        continue

    window = event["window_start"]
    zone_id = event["pickup_zone_id"]
    ride_count = int(event["ride_count"])

    key = (window, zone_id)

    if key in seen_records:
        duplicates += 1
    else:
        seen_records.add(key)
        window_zones[window].add(zone_id)

    window_ride_totals[window] += ride_count
    records_found += 1

consumer.close()

print("\n========== VALIDATION REPORT ==========")

print("Aggregation run ID:", RUN_ID)
print("Total output records:", records_found)
print("Unique windows:", len(window_zones))
print("Expected zones per window: 52")
print("Duplicate records:", duplicates)

print("\nWindow-wise validation:")

for window in sorted(window_zones):

    zone_count = len(window_zones[window])
    ride_total = window_ride_totals[window]

    print(
        f"{window} | "
        f"Zones: {zone_count} | "
        f"Total rides: {ride_total}"
    )

print("\n======================================")

valid = (
    records_found == 624
    and len(window_zones) == 12
    and all(len(zones) == 52 for zones in window_zones.values())
    and duplicates == 0
)

if valid:
    print("SUCCESS: All 624 aggregated records verified.")
else:
    print("VALIDATION NEEDS INVESTIGATION.")
