import os
import json
import uuid
import asyncio
import logging
from fastapi import FastAPI, Request
from aiokafka import AIOKafkaProducer
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure structured logging
logging.basicConfig(level=logging.INFO, format='%(message)s')

# FastAPI app
app = FastAPI()

producer: AIOKafkaProducer = None

@app.on_event("startup")
async def connect_to_kafka():
    global producer
    kafka_broker = os.getenv("KAFKA_BROKER", "kafka:9092")

    for attempt in range(10):
        try:
            producer = AIOKafkaProducer(
                bootstrap_servers=kafka_broker,
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                key_serializer=lambda k: k.encode("utf-8") if k else None,
                acks='all'
            )
            await producer.start()
            logging.info(json.dumps({
                "event": "kafka_connection_success",
                "broker": kafka_broker
            }))
            break
        except Exception as e:
            logging.warning(json.dumps({
                "event": "kafka_connection_retry",
                "attempt": attempt + 1,
                "error": str(e)
            }))
            await asyncio.sleep(5)
    else:
        logging.error(json.dumps({
            "event": "kafka_connection_failed",
            "error": "Kafka not available after 10 retries"
        }))
        raise RuntimeError("Kafka not available")

@app.on_event("shutdown")
async def shutdown_kafka():
    if producer:
        await producer.stop()
        logging.info(json.dumps({"event": "kafka_disconnected"}))

@app.post("/mqtt/webhook")
async def receive_webhook(req: Request):
    data = await req.json()
    headers = dict(req.headers)

    raw_payload = data.get("payload")
    try:
        payload = json.loads(raw_payload) if isinstance(raw_payload, str) else raw_payload
    except json.JSONDecodeError:
        payload = {}

    trace_id = payload.get("trace_id") or str(uuid.uuid4())
    sender_id = headers.get("x-emqx-sub", "unknown")
    room_id = payload.get("room_id", "unknown")
    room_type = payload.get("room_type", "unknown")

    # Add metadata to payload
    payload["trace_id"] = trace_id
    payload["sender_id"] = sender_id

    # Route based on room type
    if room_type == "assistant":
        topic = "messages.ToAssistant"
    elif room_type == "user":
        topic = "messages.ToUser"
    else:
        topic = "messages.Unknown"

    logging.info(json.dumps({
        "event": "webhook_received",
        "trace_id": trace_id,
        "sender_id": sender_id,
        "room_id": room_id,
        "room_type": room_type,
        "target_topic": topic,
        "payload": payload
    }))

    # Send to Kafka
    try:
        result = await producer.send_and_wait(
            topic=topic,
            key=room_id,
            value=payload
        )
        logging.info(json.dumps({
            "event": "kafka_publish_success",
            "trace_id": trace_id,
            "topic": result.topic,
            "partition": result.partition,
            "offset": result.offset,
            "room_id": room_id
        }))
    except Exception as e:
        logging.error(json.dumps({
            "event": "kafka_publish_failure",
            "trace_id": trace_id,
            "room_id": room_id,
            "error": str(e)
        }))

    return {"status": "ok"}

