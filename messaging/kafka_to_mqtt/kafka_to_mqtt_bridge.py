import os
import json
import time
import asyncio
import logging
import jwt
from aiokafka import AIOKafkaConsumer
from aiokafka.errors import KafkaConnectionError
from aiokafka.structs import TopicPartition
from asyncio_mqtt import Client as MQTTClient, MqttError
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Logging setup
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s - %(message)s')

# Environment variables
KAFKA_BROKER = os.getenv("KAFKA_BROKER", "kafka:9092")
KAFKA_TOPIC = "messages.outgoing"
MQTT_BROKER = os.getenv("MQTT_BROKER", "emqx")
MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))
RETRY_DELAY = 5
MAX_PUBLISH_RETRIES = 3

# JWT Setup
JWT_SECRET = "your-secret-key-here"
JWT_ALGORITHM = "HS256"

def generate_jwt():
    payload = {
        "exp": int(time.time()) + 90 * 24 * 60 * 60,  # 3 months
        "iss": "bee",
        "client_attrs": {
            "role": "admin",
            "sub": "mqtt-fanout",
            "sn": "mqtt-bridge"
        }
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def get_kafka_consumer():
    return AIOKafkaConsumer(
        KAFKA_TOPIC,
        bootstrap_servers=KAFKA_BROKER,
        value_deserializer=lambda m: json.loads(m.decode("utf-8")),
        key_deserializer=lambda m: m.decode("utf-8") if m else None,
        group_id="mqtt-fanout",
        enable_auto_commit=False,
        auto_offset_reset="earliest"
    )

async def kafka_to_mqtt():
    while True:
        consumer = get_kafka_consumer()
        try:
            await consumer.start()
            logging.info("✅ Kafka consumer connected")

            while True:
                try:
                    jwt_token = generate_jwt()
                    async with MQTTClient(
                        hostname=MQTT_BROKER,
                        port=MQTT_PORT,
                        client_id="mqtt-fanout",      # Stable client ID for durable session
                        clean_session=False,          # Durable session
                        username=jwt_token,
                        password=jwt_token
                    ) as mqtt_client:
                        logging.info("✅ MQTT client connected")

                        async for msg in consumer:
                            payload = msg.value
                            trace_id = payload.get("trace_id", "unknown")
                            recipient_id = payload.get("receiver_id") or payload.get("recipient_id")

                            if not recipient_id:
                                logging.warning(json.dumps({
                                    "event": "missing_recipient_id",
                                    "trace_id": trace_id,
                                    "payload": payload
                                }))
                                continue

                            mqtt_topic = f"user/{recipient_id}/message"
                            message = json.dumps(payload)

                            for attempt in range(1, MAX_PUBLISH_RETRIES + 1):
                                try:
                                    logging.info(json.dumps({
                                        "event": "mqtt_payload_publish_attempt",
                                        "trace_id": trace_id,
                                        "mqtt_topic": mqtt_topic,
                                        "payload": payload
                                    }))

                                    await mqtt_client.publish(
                                        topic=mqtt_topic,
                                        payload=message,
                                        qos=1,
                                        retain=False  # Don't retain — rely on durable delivery
                                    )

                                    logging.info(json.dumps({
                                        "event": "kafka_to_mqtt_published",
                                        "trace_id": trace_id,
                                        "recipient_id": recipient_id,
                                        "mqtt_topic": mqtt_topic,
                                        "kafka_partition": msg.partition,
                                        "kafka_offset": msg.offset
                                    }))

                                    tp = TopicPartition(msg.topic, msg.partition)
                                    await consumer.commit({tp: msg.offset + 1})
                                    break

                                except Exception as e:
                                    logging.error(json.dumps({
                                        "event": "mqtt_publish_retry_error",
                                        "trace_id": trace_id,
                                        "attempt": attempt,
                                        "error": str(e)
                                    }))
                                    await asyncio.sleep(RETRY_DELAY)
                            else:
                                logging.error(json.dumps({
                                    "event": "mqtt_publish_failed_after_retries",
                                    "trace_id": trace_id,
                                    "mqtt_topic": mqtt_topic
                                }))

                except MqttError as me:
                    logging.error(f"❌ MQTT connection failed: {me}")
                    logging.info(f"🔄 Reconnecting to MQTT in {RETRY_DELAY}s...")
                    await asyncio.sleep(RETRY_DELAY)

        except KafkaConnectionError as ke:
            logging.warning(f"❌ Kafka error: {ke}. Retrying in {RETRY_DELAY}s")
            await asyncio.sleep(RETRY_DELAY)
        except Exception as e:
            logging.exception(f"❌ Unexpected consumer error: {e}")
            await asyncio.sleep(RETRY_DELAY)
        finally:
            try:
                await consumer.stop()
                logging.info("🛑 Kafka consumer stopped")
            except Exception as e:
                logging.error(f"⚠️ Error stopping Kafka consumer: {e}")

if __name__ == "__main__":
    asyncio.run(kafka_to_mqtt())

