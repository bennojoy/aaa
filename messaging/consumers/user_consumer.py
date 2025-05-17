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

        # Get participants and process message
        all_participants = [p["user_id"] for p in permission_data.get("participants", [])]
        recipients = [p for p in all_participants if p != payload["sender_id"]]
        
        logging.info(json.dumps({
            "event": "processing_recipients",
            "trace_id": trace_id,
            "recipients": recipients
        }))
        
        # Process each recipient
        for recipient in recipients:
            try:
                logging.info(json.dumps({
                    "event": "checking_preferences",
                    "trace_id": trace_id,
                    "recipient": recipient
                }))
                
                # Get preferences
                recipient_prefs = await self.get_language_preferences(recipient, payload["room_id"])
                sender_prefs = await self.get_language_preferences(payload["sender_id"], payload["room_id"])
                
                logging.info(json.dumps({
                    "event": "got_preferences",
                    "trace_id": trace_id,
                    "recipient_prefs": recipient_prefs,
                    "sender_prefs": sender_prefs
                }))
                
                target_language = None
                if recipient_prefs and recipient_prefs.get("incoming_language"):
                    target_language = recipient_prefs["incoming_language"]
                elif sender_prefs and sender_prefs.get("outgoing_language"):
                    target_language = sender_prefs["outgoing_language"]
                
                logging.info(json.dumps({
                    "event": "determined_target_language",
                    "trace_id": trace_id,
                    "target_language": target_language
                }))
                
                if target_language:
                    # Publish to translation topic
                    await self.publish_to_translation({
                        "original_message": payload,
                        "target_language": target_language,
                        "recipient_id": recipient,
                        "sender_id": payload["sender_id"],
                        "room_id": payload["room_id"],
                        "trace_id": trace_id,
                        "token": self.system_token
                    })
                    
                    logging.info(json.dumps({
                        "event": "sent_to_translation",
                        "trace_id": trace_id,
                        "recipient_id": recipient,
                        "target_language": target_language
                    }))
                else:
                    # Send original message directly
                    await self.send_to_recipient(payload, recipient)
                    
                    logging.info(json.dumps({
                        "event": "sent_original_message",
                        "trace_id": trace_id,
                        "recipient_id": recipient
                    }))
                    
            except Exception as e:
                logging.error(json.dumps({
                    "event": "message_processing_error",
                    "trace_id": trace_id,
                    "recipient_id": recipient,
                    "error": str(e)
                }))

async def main():
    consumer = UserConsumer()
    await consumer.run()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main()) 