import asyncio
import json
import logging
import uuid
from typing import Dict, List, Any
from aiokafka.structs import TopicPartition
from aiokafka.errors import KafkaConnectionError
import httpx
import aiohttp

from ..config import RETRY_DELAY, OUTPUT_TOPIC, TOPICS
from ..utils.auth import get_system_token
from ..utils.kafka import setup_kafka_consumer, setup_kafka_producer, send_message
from ..utils.permissions import check_message_permission

class BaseConsumer:
    def __init__(self, topic: str, group_id: str):
        self.topic = topic
        self.group_id = group_id
        self.consumer = None
        self.producer = None
        self.http_client = None
        self.system_token = None
        self.api_base_url = "http://localhost:8000/api/v1"

    async def setup(self):
        """Setup consumer, producer, and HTTP client"""
        logging.info(f"Setting up consumer for topic: {self.topic}, group: {self.group_id}")
        try:
            self.system_token = await get_system_token()
            logging.info("Got system token successfully")
            
            self.consumer = await setup_kafka_consumer(self.topic, self.group_id)
            logging.info(f"Kafka consumer initialized for topic: {self.topic}")
            
            self.producer = await setup_kafka_producer()
            logging.info("Kafka producer initialized")
            
            self.http_client = httpx.AsyncClient(headers={"Authorization": f"Bearer {self.system_token}"})
            logging.info("HTTP client initialized")
        except Exception as e:
            logging.error(f"Error during setup: {str(e)}")
            raise

    async def cleanup(self):
        """Cleanup resources"""
        try:
            if self.consumer:
                await self.consumer.stop()
            if self.producer:
                await self.producer.stop()
            if self.http_client:
                await self.http_client.aclose()
            logging.info("🛑 Cleaned up resources.")
        except Exception as e:
            logging.error(f"⚠️ Error during cleanup: {e}")

    async def validate_message(self, payload: Dict) -> bool:
        """Validate message payload"""
        try:
            room_uuid = uuid.UUID(payload.get("room_id", ""))
            user_uuid = uuid.UUID(payload.get("sender_id", ""))
            return True
        except ValueError as e:
            logging.error(json.dumps({
                "event": "invalid_uuid",
                "trace_id": payload.get("trace_id", "unknown"),
                "room_id": payload.get("room_id"),
                "user_id": payload.get("sender_id"),
                "error": str(e)
            }))
            return False

    async def check_permissions(self, room_id: str, user_id: str, trace_id: str) -> Dict:
        """Check message permissions"""
        return await check_message_permission(
            self.http_client,
            room_id,
            user_id,
            trace_id,
            self.system_token
        )

    async def send_to_recipients(
        self,
        payload: Dict,
        recipients: List[str],
        sender_id: str,
        visibility: str = "public"
    ):
        """Send message to recipients"""
        logging.info(json.dumps({
            "event": "sending_to_recipients",
            "trace_id": payload.get("trace_id", "unknown"),
            "recipients": recipients,
            "sender_id": sender_id,
            "visibility": visibility
        }))
        
        for receiver_id in recipients:
            try:
                message_payload = payload.copy()
                message_payload["receiver_id"] = receiver_id
                message_payload["sender_id"] = sender_id
                await send_message(
                    self.producer,
                    OUTPUT_TOPIC,
                    receiver_id,
                    message_payload
                )
                logging.info(json.dumps({
                    "event": "message_sent_to_recipient",
                    "trace_id": payload.get("trace_id", "unknown"),
                    "receiver_id": receiver_id,
                    "sender_id": sender_id
                }))
            except Exception as e:
                logging.error(json.dumps({
                    "event": "failed_to_send_to_recipient",
                    "trace_id": payload.get("trace_id", "unknown"),
                    "receiver_id": receiver_id,
                    "error": str(e)
                }))
                raise

    async def process_message(self, msg):
        """Process a single message - to be implemented by subclasses"""
        raise NotImplementedError

    async def run(self):
        """Main consumer loop"""
        logging.info(f"Starting consumer loop for topic: {self.topic}")
        while True:
            try:
                await self.setup()
                await self.consumer.start()
                await self.producer.start()
                logging.info(f"✅ Connected to Kafka, consuming from topic: {self.topic}")

                async for msg in self.consumer:
                    try:
                        logging.info(f"Received message from topic {msg.topic}, partition {msg.partition}, offset {msg.offset}")
                        await self.process_message(msg)
                        # Commit the message offset
                        tp = TopicPartition(msg.topic, msg.partition)
                        await self.consumer.commit({tp: msg.offset + 1})
                        logging.info(f"Committed offset {msg.offset + 1} for partition {msg.partition}")
                    except Exception as e:
                        logging.error(json.dumps({
                            "event": "message_processing_failure",
                            "trace_id": msg.value.get("trace_id", "unknown"),
                            "error": str(e),
                            "topic": msg.topic,
                            "partition": msg.partition,
                            "offset": msg.offset
                        }))

            except KafkaConnectionError as ke:
                logging.warning(f"❌ Kafka connection error: {ke}. Retrying in {RETRY_DELAY}s...")
                await asyncio.sleep(RETRY_DELAY)
            except Exception as e:
                logging.error(json.dumps({
                    "event": "consumer_loop_exception",
                    "error": str(e),
                    "topic": self.topic
                }))
                await asyncio.sleep(RETRY_DELAY)
            finally:
                await self.cleanup()

    async def get_language_preferences(self, user_id: str, room_id: str) -> Dict[str, Any]:
        """Get language preferences for a user in a room"""
        try:
            response = await self.http_client.get(
                f"http://localhost:8000/api/users/{user_id}/rooms/{room_id}/language-preferences",
                headers={"X-Trace-ID": str(uuid.uuid4())}
            )
            if response.status_code == 200:
                return response.json()
            logging.warning(f"Failed to get language preferences: {response.status_code}")
            return None
        except Exception as e:
            logging.error(f"Error getting language preferences: {str(e)}")
            return None

    async def publish_to_translation(self, payload: Dict[str, Any]):
        """Publish message to translation topic"""
        try:
            # Implementation depends on your Kafka setup
            # This is a placeholder for the actual Kafka producer code
            await self.producer.send(
                TOPICS["TO_TRANSLATION"],
                value=payload
            )
        except Exception as e:
            logging.error(f"Error publishing to translation topic: {str(e)}")
            raise

    async def send_to_recipient(self, message: Dict[str, Any], recipient_id: str):
        """Send message to a specific recipient"""
        try:
            # Implementation depends on your message sending setup
            # This is a placeholder for the actual message sending code
            await self.producer.send(
                TOPICS["OUTGOING"],
                value={
                    **message,
                    "recipient_id": recipient_id
                }
            )
        except Exception as e:
            logging.error(f"Error sending message to recipient: {str(e)}")
            raise 