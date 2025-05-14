import asyncio
import json
import logging
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from aiokafka.errors import KafkaConnectionError
from aiokafka.structs import TopicPartition

# Kafka config
BOOTSTRAP_SERVERS = "localhost:29092"
INPUT_TOPIC = "messages.ToUser"
OUTPUT_TOPIC = "messages.outgoing"
GROUP_ID = "user-message-consumer"
RETRY_DELAY = 5

# Logging config
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s'
)

async def consume_user_messages():
    while True:
        consumer = AIOKafkaConsumer(
            INPUT_TOPIC,
            bootstrap_servers=BOOTSTRAP_SERVERS,
            group_id=GROUP_ID,
            value_deserializer=lambda m: json.loads(m.decode("utf-8")),
            key_deserializer=lambda m: m.decode("utf-8") if m else None,
            enable_auto_commit=False,
            auto_offset_reset="earliest"
        )

        producer = AIOKafkaProducer(
            bootstrap_servers=BOOTSTRAP_SERVERS,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            key_serializer=lambda k: k.encode("utf-8")
        )

        try:
            await consumer.start()
            await producer.start()
            logging.info(f"✅ Connected to Kafka, consuming from topic: {INPUT_TOPIC}")

            async for msg in consumer:
                payload = msg.value
                trace_id = payload.get("trace_id", "unknown")
                sender_id = payload.get("sender_id", "unknown")
                room_id = payload.get("room_id", "unknown")
                receiver_id = "333-333-333"
                payload["receiver_id"] = receiver_id

                logging.info(json.dumps({
                    "event": "user_message_received",
                    "trace_id": trace_id,
                    "sender_id": sender_id,
                    "room_id": room_id,
                    "topic": msg.topic,
                    "partition": msg.partition,
                    "offset": msg.offset,
                    "payload": payload
                }))

                try:
                    result = await producer.send_and_wait(
                        topic=OUTPUT_TOPIC,
                        key=receiver_id,
                        value=payload
                    )
                    logging.info(json.dumps({
                        "event": "kafka_forwarded_to_outgoing",
                        "trace_id": trace_id,
                        "topic": OUTPUT_TOPIC,
                        "receiver_id": receiver_id,
                        "partition": result.partition,
                        "offset": result.offset,
                        "payload": payload
                    }))

                    tp = TopicPartition(msg.topic, msg.partition)
                    await consumer.commit({tp: msg.offset + 1})

                except Exception as e:
                    logging.error(json.dumps({
                        "event": "kafka_publish_failure",
                        "trace_id": trace_id,
                        "receiver_id": receiver_id,
                        "topic": OUTPUT_TOPIC,
                        "error": str(e)
                    }))

        except KafkaConnectionError as ke:
            logging.warning(f"❌ Kafka connection error: {ke}. Retrying in {RETRY_DELAY}s...")
            await asyncio.sleep(RETRY_DELAY)
        except Exception as e:
            logging.error(json.dumps({
                "event": "consumer_loop_exception",
                "error": str(e)
            }))
            await asyncio.sleep(RETRY_DELAY)
        finally:
            try:
                await consumer.stop()
                await producer.stop()
                logging.info("🛑 Cleaned up Kafka consumer and producer.")
            except Exception as e:
                logging.error(f"⚠️ Error during shutdown: {e}")


if __name__ == "__main__":
    asyncio.run(consume_user_messages())

