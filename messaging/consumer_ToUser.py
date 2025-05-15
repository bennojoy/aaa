import asyncio
import json
import logging
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from aiokafka.errors import KafkaConnectionError
from aiokafka.structs import TopicPartition
import httpx
from typing import Dict
import uuid

# Kafka config
BOOTSTRAP_SERVERS = "localhost:29092"
INPUT_TOPIC = "messages.ToUser"
OUTPUT_TOPIC = "messages.outgoing"
GROUP_ID = "user-message-consumer"
RETRY_DELAY = 5

# System user config
SYSTEM_PHONE = "+18992455022"
SYSTEM_PASSWORD = "system123"

# Logging config
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s'
)

async def signup_system_user():
    """Try to sign up the system user. Ignore error if user already exists."""
    url = "http://localhost:8000/api/v1/auth/signup"
    data = {
        "phone_number": SYSTEM_PHONE,
        "password": SYSTEM_PASSWORD,
        "alias": "system_user",
        "user_type": "human",
        "language": "en"
    }
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, json=data)
            if response.status_code == 200:
                logging.info("System user signed up successfully.")
            elif response.status_code == 400 and ("already exists" in response.text or "exists" in response.text):
                logging.info("System user already exists, continuing.")
            else:
                logging.warning(f"System user signup response: {response.text}")
        except Exception as e:
            logging.error(f"System user signup error: {e}")

async def get_system_token() -> str:
    """Get system token for API calls"""
    # Ensure system user exists
    await signup_system_user()
    url = "http://localhost:8000/api/v1/auth/signin"
    data = {
        "identifier": SYSTEM_PHONE,
        "password": SYSTEM_PASSWORD
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=data)
        response.raise_for_status()
        return response.json()["access_token"]

async def check_message_permission(
    client: httpx.AsyncClient,
    room_id: str,
    user_id: str,
    trace_id: str,
    token: str
) -> Dict:
    """Check if user can send messages in room and get participants"""
    url = f"http://localhost:8000/api/v1/rooms/{room_id}/message-permission/{user_id}"
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Trace-ID": trace_id
    }
    
    logging.info(f"Checking message permission - URL: {url}, Headers: {headers}")
    response = await client.get(url, headers=headers)
    logging.info(f"Permission check response - Status: {response.status_code}, Body: {response.text}")
    
    if response.status_code != 200:
        raise Exception(f"Permission check failed: {response.text}")
        
    return response.json()

async def consume_user_messages():
    while True:
        # Get system token
        try:
            system_token = await get_system_token()
        except Exception as e:
            logging.error(f"Failed to get system token: {e}")
            await asyncio.sleep(RETRY_DELAY)
            continue

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

        # Create HTTP client with token
        async with httpx.AsyncClient(headers={"Authorization": f"Bearer {system_token}"}) as http_client:
            try:
                await consumer.start()
                await producer.start()
                logging.info(f"✅ Connected to Kafka, consuming from topic: {INPUT_TOPIC}")

                async for msg in consumer:
                    payload = msg.value
                    trace_id = payload.get("trace_id", "unknown")
                    sender_id = payload.get("sender_id", "unknown")
                    room_id = payload.get("room_id", "unknown")

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
                        # Validate UUIDs
                        try:
                            room_uuid = uuid.UUID(room_id)
                            user_uuid = uuid.UUID(sender_id)
                        except ValueError as e:
                            logging.error(json.dumps({
                                "event": "invalid_uuid",
                                "trace_id": trace_id,
                                "room_id": room_id,
                                "user_id": sender_id,
                                "error": str(e)
                            }))
                            continue

                        # Check message permissions
                        permission_result = await check_message_permission(
                            http_client,
                            str(room_uuid),
                            str(user_uuid),
                            trace_id,
                            system_token
                        )

                        if permission_result.get("can_send_message"):
                            # Send message to each participant
                            for participant in permission_result.get("participants", []):
                                receiver_id = participant["user_id"]
                                
                                # Skip sending to the sender
                                if receiver_id == sender_id:
                                    continue

                                # Create message for this participant
                                message_payload = payload.copy()
                                message_payload["receiver_id"] = receiver_id

                                result = await producer.send_and_wait(
                                    topic=OUTPUT_TOPIC,
                                    key=receiver_id,
                                    value=message_payload
                                )

                                logging.info(json.dumps({
                                    "event": "kafka_forwarded_to_outgoing",
                                    "trace_id": trace_id,
                                    "topic": OUTPUT_TOPIC,
                                    "receiver_id": receiver_id,
                                    "partition": result.partition,
                                    "offset": result.offset,
                                    "payload": message_payload
                                }))

                        # Commit the message offset
                        tp = TopicPartition(msg.topic, msg.partition)
                        await consumer.commit({tp: msg.offset + 1})

                    except Exception as e:
                        logging.error(json.dumps({
                            "event": "message_processing_failure",
                            "trace_id": trace_id,
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

