import asyncio
import logging
import jwt
import time
from aiomqtt import Client

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# JWT Configuration
JWT_SECRET = "your-secret-key-here"
JWT_ALGORITHM = "HS256"

def generate_jwt():
    payload = {
        "exp": int(time.time()) + 90 * 24 * 60 * 60,  # 3 months
        "iss": "bee",
        "client_attrs": {
            "role": "admin",
            "sub": "mqtt-fanout",
            "sn": "mqtt-bridge"
        }
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

async def test_mqtt_connection():
    token = generate_jwt()
    try:
        async with Client(
            hostname="localhost",
            port=8083,
            username=token,
            password=None,
            identifier="test-client",
            transport="websockets",
            websocket_path="/mqtt"
        ) as client:
            logger.info("Successfully connected to MQTT broker")
            
            # Subscribe to a test topic
            await client.subscribe("test/topic")
            logger.info("Subscribed to test/topic")
            
            # Publish a test message
            await client.publish("test/topic", "Hello, MQTT!")
            logger.info("Published test message")
            
            # Wait for a moment to ensure message delivery
            await asyncio.sleep(1)
            
    except Exception as e:
        logger.error(f"Failed to connect: {e}")

if __name__ == "__main__":
    asyncio.run(test_mqtt_connection()) 