import json
import logging
import asyncio
import httpx
from .base_consumer import BaseConsumer
from ..config import TOPICS, CONSUMER_GROUPS

class AssistantConsumer(BaseConsumer):
    def __init__(self):
        super().__init__(
            topic=TOPICS["TO_ASSISTANT"],
            group_id=CONSUMER_GROUPS["ASSISTANT"]
        )
        logging.info(f"AssistantConsumer initialized for topic: {self.topic}")

    async def process_message(self, msg):
        """Process a message from the ToAssistant topic"""
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
            logging.info(f"Permission data: {json.dumps(permission_data)}")
        except Exception as e:
            logging.error(f"Permission check failed for trace_id: {trace_id}, error: {e}")
            return

        # Get participants and visibility
        all_participants = [p["user_id"] for p in permission_data.get("participants", [])]
        # Get visibility from the original message payload, not from permission_data
        visibility = payload.get("visibility", "public")
        
        logging.info(json.dumps({
            "event": "visibility_check",
            "trace_id": trace_id,
            "message_visibility": visibility,
            "all_participants": all_participants,
            "sender_id": payload["sender_id"]
        }))
        
        # Determine recipients based on visibility
        if visibility == "private":
            recipients = [payload["sender_id"]]
            logging.info(f"Private message - sending only to sender: {recipients}")
        else:
            recipients = all_participants
            logging.info(f"Public message - sending to all participants: {recipients}")
        
        logging.info(json.dumps({
            "event": "processing_ai_response",
            "trace_id": trace_id,
            "recipients": recipients,
            "visibility": visibility,
            "sender_id": payload["sender_id"]
        }))

        # Get AI response
        ai_response = await self.get_ai_response(payload, trace_id)
        if not ai_response:
            logging.warning(f"No AI response generated for trace_id: {trace_id}")
            return

        # Send AI response to all participants
        response_payload = payload.copy()
        response_payload["content"] = ai_response
        response_payload["sender_id"] = "system"
        
        logging.info(json.dumps({
            "event": "sending_ai_response",
            "trace_id": trace_id,
            "recipients": recipients,
            "visibility": visibility,
            "response": ai_response
        }))
        
        await self.send_to_recipients(response_payload, recipients, "system", visibility)

    async def get_ai_response(self, payload: dict, trace_id: str) -> str:
        """Get response from AI service"""
        logging.info(f"Getting AI response for trace_id: {trace_id}")
        return "hi from ai"

async def main():
    consumer = AssistantConsumer()
    await consumer.run()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main()) 