import asyncio
import logging
from messaging.consumers.translation_consumer import TranslationConsumer
from messaging.consumers.user_consumer import UserConsumer
from messaging.consumers.assistant_consumer import AssistantConsumer

async def main():
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Initialize consumers
    translation_consumer = TranslationConsumer()
    user_consumer = UserConsumer()
    assistant_consumer = AssistantConsumer()
    
    # Start all consumers
    await asyncio.gather(
        translation_consumer.run(),
        user_consumer.run(),
        assistant_consumer.run()
    )

if __name__ == "__main__":
    asyncio.run(main()) 