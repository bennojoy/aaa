import asyncio
import logging
from .consumers.translation_consumer import TranslationConsumer
from .consumers.user_consumer import UserConsumer
from .consumers.assistant_consumer import AssistantConsumer

async def run_consumers():
    # Initialize consumers
    translation_consumer = TranslationConsumer()
    user_consumer = UserConsumer()
    assistant_consumer = AssistantConsumer()

    # Run all consumers concurrently
    await asyncio.gather(
        translation_consumer.run(),
        user_consumer.run(),
        assistant_consumer.run()
    )

if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run consumers
    asyncio.run(run_consumers()) 