import json
import logging
import asyncio
import httpx
import uuid
from datetime import datetime, timezone, timedelta
from .base_consumer import BaseConsumer
from ..config import TOPICS, CONSUMER_GROUPS, SYSTEM_USER_UUID
from messaging.ai_agents.runner import run_assistant_agent
from messaging.ai_agents.agent_context import UserContext

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

        # Calculate timezone offset from client timestamp
        timezone_offset = None
        client_timestamp = payload.get("client_timestamp")
        if client_timestamp:
            try:
                client_time = datetime.fromisoformat(client_timestamp)
                server_time = datetime.now(timezone.utc)
                # Calculate offset in minutes
                offset_minutes = int((client_time - server_time).total_seconds() / 60)
                timezone_offset = offset_minutes
                logging.info(f"Updated timezone offset to {offset_minutes} minutes for trace_id: {trace_id}")
            except Exception as e:
                logging.error(f"Error calculating timezone offset for trace_id: {trace_id}, error: {e}")

        # Build user context for the agent
        user_context = UserContext(
            name=None,  # You can fill this if available
            language=payload.get("language", "en"),
            sender_id=payload["sender_id"],
            receiver_id=None,
            room=payload["room_id"],
            token=self.system_token,
            timezone_offset=timezone_offset
        )

        # Format message for the agent
        # If the message starts with @ai, remove it
        user_message = payload["content"]
        if user_message.startswith("@ai"):
            user_message = user_message[4:].strip()

        # Call the runner to get the AI reply
        try:
            ai_response = await run_assistant_agent(
                user_message=user_message,
                user_context=user_context,
                trace_id=trace_id
            )
        except Exception as e:
            logging.error({
                "event": "message_processing_failure",
                "trace_id": trace_id,
                "error": str(e),
                "topic": msg.topic,
                "partition": msg.partition,
                "offset": msg.offset
            })
            return

        if not ai_response:
            logging.warning(f"No AI response generated for trace_id: {trace_id}")
            return

        # Send AI response to all participants
        response_payload = payload.copy()
        logging.info(json.dumps({
            "event": "message_id_before_change",
            "trace_id": trace_id,
            "original_message_id": payload.get("id"),
            "payload": payload
        }))

        # Calculate timestamp relative to client timezone
        current_time = datetime.now(timezone.utc)
        if timezone_offset is not None:
            # Convert to client's timezone using the offset
            current_time = current_time + timedelta(minutes=timezone_offset)
        
        response_payload["content"] = ai_response
        response_payload["sender_id"] = SYSTEM_USER_UUID
        response_payload.pop("id", None)  # Remove the original message ID
        response_payload["id"] = str(uuid.uuid4())  # Generate new unique ID
        response_payload["timestamp"] = current_time.isoformat()
        response_payload["status"] = "delivered"  # Set initial status for response message

        logging.info(json.dumps({
            "event": "message_id_after_change",
            "trace_id": trace_id,
            "new_message_id": response_payload["id"],
            "payload": response_payload,
            "timestamp": response_payload["timestamp"]
        }))
        
        logging.info(json.dumps({
            "event": "sending_ai_response",
            "trace_id": trace_id,
            "recipients": recipients,
            "visibility": visibility,
            "response": ai_response
        }))
        
        await self.send_to_recipients(response_payload, recipients, SYSTEM_USER_UUID, visibility)

async def main():
    consumer = AssistantConsumer()
    await consumer.run()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main()) 