import json
import logging
import asyncio
from .base_consumer import BaseConsumer
from ..config import TOPICS, CONSUMER_GROUPS
from ..ai_agents.runner import run_assistant_agent
from ..ai_agents.agent_context import UserContext

class TranslationConsumer(BaseConsumer):
    def __init__(self):
        super().__init__(
            topic=TOPICS["TO_TRANSLATION"],
            group_id=CONSUMER_GROUPS["TRANSLATION"]
        )
        logging.info(f"TranslationConsumer initialized for topic: {self.topic}")

    async def process_message(self, msg):
        """Process a message from the translation topic"""
        payload = msg.value
        trace_id = payload.get("trace_id", "unknown")
        
        logging.info(json.dumps({
            "event": "received_translation_request",
            "trace_id": trace_id,
            "topic": msg.topic,
            "partition": msg.partition,
            "offset": msg.offset,
            "key": msg.key,
            "payload": payload
        }))

        try:
            # Create context for assistant agent
            context = UserContext(
                sender_id=payload["sender_id"],
                room=payload["room_id"],
                token=payload.get("token")
            )
            
            # Use assistant agent to translate
            content = payload["original_message"]["content"]
            target_language = payload["target_language"]
            prompt = f"Translate the following text to {target_language}. Only output the translation, no explanations:\n\n{content}"
            translated_text = await run_assistant_agent(
                user_message=prompt,
                user_context=context,
                trace_id=trace_id
            )
            
            # Send translated message
            translated_text = translated_text.strip("@ai::")
            translated_payload = payload["original_message"].copy()
            translated_payload["content"] = translated_text
            translated_payload["translated"] = True
            translated_payload["target_language"] = payload["target_language"]
            
            await self.send_to_recipient(
                translated_payload,
                payload["recipient_id"]
            )
            
            logging.info(json.dumps({
                "event": "translation_success",
                "trace_id": trace_id,
                "recipient_id": payload["recipient_id"],
                "target_language": payload["target_language"]
            }))
            
        except Exception as e:
            logging.error(json.dumps({
                "event": "translation_failed",
                "trace_id": trace_id,
                "error": str(e)
            }))
            # Fallback to original message
            await self.send_to_recipient(
                payload["original_message"],
                payload["recipient_id"]
            )

async def main():
    consumer = TranslationConsumer()
    await consumer.run()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main()) 