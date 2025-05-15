import json
import logging
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from ..config import BOOTSTRAP_SERVERS

async def setup_kafka_consumer(topic: str, group_id: str) -> AIOKafkaConsumer:
    """Setup and return a Kafka consumer"""
    logging.info(f"Setting up Kafka consumer for topic: {topic}, group: {group_id}")
    consumer = AIOKafkaConsumer(
        topic,
        bootstrap_servers=BOOTSTRAP_SERVERS,
        group_id=group_id,
        value_deserializer=lambda m: json.loads(m.decode("utf-8")),
        key_deserializer=lambda m: m.decode("utf-8") if m else None,
        enable_auto_commit=False,
        auto_offset_reset="earliest",
        max_poll_interval_ms=300000,  # 5 minutes
        session_timeout_ms=60000,     # 1 minute
        heartbeat_interval_ms=20000   # 20 seconds
    )
    logging.info(f"Kafka consumer configured for topic: {topic}")
    return consumer

async def setup_kafka_producer() -> AIOKafkaProducer:
    """Setup and return a Kafka producer"""
    logging.info("Setting up Kafka producer")
    producer = AIOKafkaProducer(
        bootstrap_servers=BOOTSTRAP_SERVERS,
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        key_serializer=lambda k: k if isinstance(k, bytes) else str(k).encode("utf-8")
    )
    logging.info("Kafka producer configured")
    return producer

async def send_message(
    producer: AIOKafkaProducer,
    topic: str,
    key: str,
    value: dict
) -> None:
    """Send a message to Kafka"""
    try:
        # Convert key to string if it's not already
        key_str = str(key)
        
        result = await producer.send_and_wait(
            topic=topic,
            key=key_str,
            value=value
        )
        
        logging.info(json.dumps({
            "event": "kafka_message_sent",
            "topic": topic,
            "key": key_str,
            "partition": result.partition,
            "offset": result.offset,
            "payload": value
        }))
    except Exception as e:
        logging.error(json.dumps({
            "event": "kafka_send_error",
            "topic": topic,
            "key": key_str,
            "error": str(e),
            "payload": value
        }))
        raise 