import asyncio
import json
import time
import logging
import httpx
from asyncio_mqtt import Client, MqttError
from datetime import datetime

# === Logging Setup ===
logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')

# === User Setup ===
USER1_PHONE = "+15509990001"
USER1_PASSWORD = "pwuser1new2024"
USER2_PHONE = "+15509990002"
USER2_PASSWORD = "pwuser2new2024"
ROOM_ID = "0b09026d-c96b-4234-8fe4-f484ebf51759"  # Room ID from setup

# === MQTT Setup ===
BROKER_HOST = "localhost"
BROKER_PORT = 8083
WEBSOCKET_PATH = "/mqtt"
CLIENT_ID = None  # Will be set after login

async def sign_in():
    url = "http://localhost:8000/api/v1/auth/signin"
    data = {
        "identifier": USER1_PHONE,
        "password": USER1_PASSWORD
    }
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, json=data)
            if response.status_code == 200:
                response_data = response.json()
                token = response_data["access_token"]
                user_id = response_data["user_id"]
                logging.info(f"User signed in successfully. User ID: {user_id}")
                return token, user_id
            else:
                logging.error(f"Sign-in failed: {response.text}")
                return None, None
        except Exception as e:
            logging.error(f"Error during sign-in: {e}")
            return None, None

async def create_room(token: str, name: str = "Test Room"):
    url = "http://localhost:8000/api/v1/rooms"
    data = {
        "name": name,
        "description": "Room for testing chat",
        "type": "user"
    }
    headers = {"Authorization": f"Bearer {token}"}
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, json=data, headers=headers)
            if response.status_code == 200:
                room_data = response.json()
                logging.info(f"Created room: {room_data['name']} with ID: {room_data['id']}")
                return room_data['id']
            else:
                logging.error(f"Failed to create room: {response.text}")
                return None
        except Exception as e:
            logging.error(f"Error creating room: {e}")
            return None

async def add_user_to_room(token: str, room_id: str, user_id: str):
    url = f"http://localhost:8000/api/v1/rooms/{room_id}/participants"
    data = {
        "user_id": user_id,
        "role": "member",
        "status": "active"
    }
    headers = {"Authorization": f"Bearer {token}"}
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, json=data, headers=headers)
            if response.status_code == 200:
                logging.info(f"Successfully added user {user_id} to room {room_id}")
                return True
            else:
                logging.error(f"Failed to add user to room: {response.text}")
                return False
        except Exception as e:
            logging.error(f"Error adding user to room: {e}")
            return False

async def search_room(token, room_name):
    url = "http://localhost:8000/api/v1/rooms/search"
    params = {"query": room_name}
    headers = {"Authorization": f"Bearer {token}"}
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, params=params, headers=headers)
            logging.info(f"Room search response status: {response.status_code}")
            logging.info(f"Room search response text: {response.text}")
            if response.status_code == 200:
                rooms = response.json()["rooms"]
                # First try to find exact match
                for room in rooms:
                    if room["name"] == room_name and room["type"] == "user":
                        logging.info(f"Found exact match room: {room['name']} with ID: {room['id']}")
                        return room['id']
                # If no exact match, try partial match
                for room in rooms:
                    if room["name"].startswith(room_name) and room["type"] == "user":
                        logging.info(f"Found partial match room: {room['name']} with ID: {room['id']}")
                        return room['id']
                logging.error(f"No room found with name '{room_name}'")
                return None
            else:
                logging.error(f"Room search failed: {response.text}")
                return None
        except Exception as e:
            logging.error(f"Error searching for room: {e}")
            return None

async def prompt_for_message():
    while True:
        message = await asyncio.get_event_loop().run_in_executor(None, input, "Enter message (or 'exit' to quit): ")
        if message.lower() == 'exit':
            break
        return message

async def mqtt_main():
    # Sign in and get token and user ID
    token, user_id = await sign_in()
    if not token or not user_id:
        logging.error("Failed to obtain token. Exiting.")
        return

    # Set client ID to user ID
    CLIENT_ID = user_id

    # Search for the room first
    room_id = await search_room(token, "messaging_room_test")
    if not room_id:
        logging.info("Room not found, creating new room...")
        room_id = await create_room(token)
        if not room_id:
            logging.error("Failed to create room. Exiting.")
            return

 

    # Set up MQTT topics
    TOPIC_SUB_PERSONAL = f"user/{user_id}/message"
    TOPIC_PUB = "messages/to_room"

    async with Client(
        hostname=BROKER_HOST,
        port=BROKER_PORT,
        username=token,  # Use original token
        password=token,  # Use original token
        client_id=CLIENT_ID,
        clean_session=False,
        transport="websockets"
    ) as client:
        client._client.ws_set_options(path=WEBSOCKET_PATH)

        # Subscribe to personal topic only
        await client.subscribe(TOPIC_SUB_PERSONAL, qos=1)
        logging.info(f"Subscribed to personal topic: {TOPIC_SUB_PERSONAL}")

        # Listen for messages in a separate task
        async def listen_for_messages():
            async with client.unfiltered_messages() as messages:
                async for msg in messages:
                    try:
                        payload = json.loads(msg.payload.decode())
                        sender = payload.get('sender_id', 'unknown')
                        logging.info(f"[RECEIVED] Topic: {msg.topic} | From: {sender} | Room: {payload.get('room_id', 'n/a')} | Content: {payload.get('content', payload)}")
                    except json.JSONDecodeError:
                        logging.info(f"[RECEIVED] Topic: {msg.topic} | Raw: {msg.payload.decode()}")

        # Start listening for messages
        asyncio.create_task(listen_for_messages())

        # Prompt for messages and publish
        while True:
            message = await prompt_for_message()
            if not message:
                break

            message_payload = {
                "room_id": room_id,
                "room_type": "user",
                "content": message,
                "trace_id": f"trace-{int(time.time())}",
                "sender_id": user_id,
                "client_timestamp": datetime.now().isoformat()
            }
            
            await client.publish(TOPIC_PUB, json.dumps(message_payload), qos=1)
            logging.info(f"[SENT] To: {TOPIC_PUB} | Room: {room_id} | Content: {message}")

if __name__ == "__main__":
    try:
        asyncio.run(mqtt_main())
    except MqttError as e:
        logging.error(f"MQTT error: {e}")
    except Exception as e:
        logging.error(f"Unexpected error: {e}")

