import json
import logging
import asyncio
from .base_consumer import BaseConsumer
from ..config import TOPICS, CONSUMER_GROUPS

class UserConsumer(BaseConsumer):
    def __init__(self):
        super().__init__(
            topic=TOPICS["TO_USER"],
            group_id=CONSUMER_GROUPS["USER"]
        )
        logging.info(f"UserConsumer initialized for topic: {self.topic}")

    async def process_message(self, msg):
        """Process a message from the ToUser topic"""
        payload = msg.value
        trace_id = payload.get("trace_id", "unknown")
        
        logging.info(json.dumps({
            "event": "received_message",
            "trace_id": trace_id,
            "topic": msg.topic,
            "partition": msg.partition,
            "offset": msg.offset,
            "key": msg.key,
            "payload": payload
        }))

        # Validate message
        if not await self.validate_message(payload):
            logging.warning(f"Message validation failed for trace_id: {trace_id}")
            return

        # Check permissions
        try:
            permission_data = await self.check_permissions(
                payload["room_id"],
                payload["sender_id"],
                trace_id
            )
            logging.info(f"Permission check successful for trace_id: {trace_id}")
        except Exception as e:
            logging.error(f"Permission check failed for trace_id: {trace_id}, error: {e}")
            return

        # Get participants and send message
        all_participants = [p["user_id"] for p in permission_data.get("participants", [])]
        # Filter out the sender from recipients
        recipients = [p for p in all_participants if p != payload["sender_id"]]
        logging.info(f"Sending message to recipients: {recipients} for trace_id: {trace_id}")
        await self.send_to_recipients(payload, recipients, payload["sender_id"])

async def main():
    consumer = UserConsumer()
    await consumer.run()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main()) 