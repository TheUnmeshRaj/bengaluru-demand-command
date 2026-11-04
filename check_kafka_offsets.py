
from confluent_kafka import Consumer, TopicPartition

BROKER = "127.0.0.1:9092"
TOPIC = "ride_requests"

consumer = Consumer({
    "bootstrap.servers": BROKER,
    "group.id": "offset-diagnostic",
    "enable.auto.commit": False
})

metadata = consumer.list_topics(
    topic=TOPIC,
    timeout=10
)

topic_metadata = metadata.topics[TOPIC]

total_available = 0

print("\nRIDE REQUEST TOPIC - OFFSET CHECK")
print("=" * 55)

for partition_id in sorted(topic_metadata.partitions):

    partition = TopicPartition(
        TOPIC,
        partition_id
    )

    earliest, latest = consumer.get_watermark_offsets(
        partition,
        timeout=10,
        cached=False
    )

    available = latest - earliest
    total_available += available

    print(
        f"Partition {partition_id}: "
        f"Earliest={earliest}, "
        f"Latest={latest}, "
        f"Available={available}"
    )

print("=" * 55)
print(f"TOTAL AVAILABLE MESSAGES: {total_available:,}")

consumer.close()
