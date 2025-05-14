import asyncio
import json
import time
import jwt
from asyncio_mqtt import Client, MqttError

# === JWT Setup ===
JWT_SECRET = "your-secret-key-here"
JWT_ALGORITHM = "HS256"
USER_ID = "333-333-333"  # The user ID of this client

def generate_jwt():
    payload = {
        "exp": int(time.time()) + 3600,  # Token valid for 1 hour
        "iss": "bee",
        "client_attrs": {
            "role": "admin",
            "sub": USER_ID,
            "sn": "10c61f1a1f47"
        },
        "acl": [
            {
                "permission": "allow",
                "action": "subscribe",
                "topic": f"user/{USER_ID}/message"
            },
            {
                "permission": "allow",
                "action": "publish",
                "topic": "messages/to_room"
            },
            {
                "permission": "deny",
                "action": "all",
                "topic": "#"
            }
        ]
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

# === MQTT Setup ===
BROKER_HOST = "localhost"
BROKER_PORT = 8083
WEBSOCKET_PATH = "/mqtt"
TOPIC_SUB = f"user/{USER_ID}/message"
TOPIC_PUB = "messages/to_room"
CLIENT_ID = USER_ID  # Must be stable for durable session

message_payload = {
    "room_id": "room-abc123",
    "room_type": "user",
    "content": "hi hi Hello World from 111 again!!!",
    "trace_id": "trace-xyz789"
}

async def mqtt_main():
    token = generate_jwt()

    async with Client(
        hostname=BROKER_HOST,
        port=BROKER_PORT,
        username=token,
        password=token,
        client_id=CLIENT_ID,
        clean_session=False,  # <-- Durable session
        transport="websockets"
    ) as client:
        client._client.ws_set_options(path=WEBSOCKET_PATH)

        # Subscribe to topic
        sub_result = await client.subscribe(TOPIC_SUB, qos=1)
        print(f"🧪 Subscription result: {sub_result}")
        if sub_result[0] == 128:
            print("❌ Subscription denied by EMQX ACL")
            return
        else:
            print(f"✅ Subscribed to: {TOPIC_SUB}")

        # Publish a test message
        await client.publish(TOPIC_PUB, json.dumps(message_payload), qos=1)
        print(f"✅ Published to: {TOPIC_PUB}")

        # Listen for messages
        async with client.unfiltered_messages() as messages:
            async for msg in messages:
                print(f"\n📥 Received on {msg.topic}: {msg.payload.decode()}")

if __name__ == "__main__":
    try:
        asyncio.run(mqtt_main())
    except MqttError as e:
        print(f"MQTT error: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")

