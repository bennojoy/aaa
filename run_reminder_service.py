import asyncio
import logging
from reminder_service.scanner import main

if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run reminder service
    asyncio.run(main()) 