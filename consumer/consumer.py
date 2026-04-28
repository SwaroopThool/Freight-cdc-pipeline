"""
Kafka consumer that reads Materialize sink topics and prints events.
Topics: mz.active_shipments, mz.revenue_by_route, mz.job_summary
"""

import json
import logging
import os
import time

from kafka import KafkaConsumer
from kafka.errors import NoBrokersAvailable

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [consumer] %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

BROKERS = os.environ.get("REDPANDA_BROKERS", "redpanda:9092").split(",")
TOPICS = os.environ.get("TOPICS", "mz.active_shipments,mz.revenue_by_route,mz.job_summary").split(",")

COLORS = {
    "mz.active_shipments": "\033[94m",  # blue
    "mz.revenue_by_route": "\033[92m",  # green
    "mz.job_summary":      "\033[93m",  # yellow
}
RESET = "\033[0m"


def create_consumer(retries: int = 30) -> KafkaConsumer:
    for i in range(retries):
        try:
            consumer = KafkaConsumer(
                *TOPICS,
                bootstrap_servers=BROKERS,
                group_id="freight-cdc-consumer",
                auto_offset_reset="earliest",
                enable_auto_commit=True,
                value_deserializer=lambda b: json.loads(b.decode("utf-8")) if b else None,
                key_deserializer=lambda b: b.decode("utf-8") if b else None,
                consumer_timeout_ms=-1,
            )
            log.info("Connected to Redpanda, subscribed to: %s", TOPICS)
            return consumer
        except NoBrokersAvailable:
            log.info("Broker not available, retry %d/%d ...", i + 1, retries)
            time.sleep(5)
    raise RuntimeError("Could not connect to Redpanda.")


def format_event(topic: str, key, value) -> str:
    color = COLORS.get(topic, "")
    # ENVELOPE UPSERT sends the row directly (no before/after/op wrapper)
    return (
        f"{color}[{topic}]{RESET} "
        f"key={key}  "
        f"{json.dumps(value, default=str)}"
    )


def main() -> None:
    consumer = create_consumer()
    log.info("Listening for events...")

    try:
        for msg in consumer:
            try:
                line = format_event(msg.topic, msg.key, msg.value)
                print(line, flush=True)
            except Exception as e:
                log.warning("Could not format message: %s", e)
    except KeyboardInterrupt:
        log.info("Consumer stopped.")
    finally:
        consumer.close()


if __name__ == "__main__":
    main()
