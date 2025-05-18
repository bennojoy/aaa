from aiokafka import AIOKafkaProducer
import json
from datetime import datetime
from typing import Optional
from uuid import UUID
from .config import settings, logger
from .models import ReminderMessage

class UUIDEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, UUID):
            return str(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

class ReminderProducer:
    def __init__(self):
        self.producer: Optional[AIOKafkaProducer] = None

    async def start(self):
        """Start the Kafka producer."""
        try:
            self.producer = AIOKafkaProducer(
                bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
                value_serializer=lambda v: json.dumps(v, cls=UUIDEncoder).encode('utf-8')
            )
            await self.producer.start()
            logger.info({
                "event": "producer_started",
                "bootstrap_servers": settings.KAFKA_BOOTSTRAP_SERVERS
            })
        except Exception as e:
            logger.error({
                "event": "producer_start_failed",
                "error": str(e)
            })
            raise

    async def stop(self):
        """Stop the Kafka producer."""
        if self.producer:
            await self.producer.stop()
            logger.info({"event": "producer_stopped"})

    async def send_reminder(self, message: ReminderMessage):
        """Send a reminder message to Kafka."""
        if not self.producer:
            raise RuntimeError("Producer not started")

        try:
            # Convert message to dict and ensure proper serialization
            message_dict = message.model_dump()
            
            # Send to Kafka
            await self.producer.send_and_wait(
                topic=settings.KAFKA_TOPIC,
                value=message_dict
            )
            
            logger.info({
                "event": "reminder_sent",
                "room_id": str(message.room_id),
                "sender_id": str(message.sender_id),
                "trace_id": message.trace_id,
                "timestamp": message.timestamp.isoformat()
            })
        except Exception as e:
            logger.error({
                "event": "reminder_send_failed",
                "room_id": str(message.room_id),
                "sender_id": str(message.sender_id),
                "trace_id": message.trace_id,
                "timestamp": message.timestamp.isoformat(),
                "error": str(e)
            })
            raise
