import asyncio
import json
import logging
import httpx
import uuid

# === Logging Setup ===
logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')

# === User Setup ===
USER1_PHONE = "+15509990001"  # New phone number for User 1
USER1_PASSWORD = "pwuser1new2024"  # New password for User 1
USER2_PHONE = "+15509990002"  # New phone number for User 2
USER2_PASSWORD = "pwuser2new2024"  # New password for User 2

async def sign_up(phone, password):
    url = "http://localhost:8000/api/v1/auth/signup"
    data = {
        "phone_number": phone,
        "password": password
    }
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, json=data)
            logging.info(f"Sign-up response status: {response.status_code}")
            logging.info(f"Sign-up response text: {response.text}")
            if response.status_code == 200:
                logging.info(f"User {phone} signed up successfully.")
            else:
                logging.warning(f"Sign-up failed for {phone}: {response.text}")
        except Exception as e:
            logging.error(f"Error during sign-up for {phone}: {e}")

async def sign_in(phone, password):
    url = "http://localhost:8000/api/v1/auth/signin"
    data = {
        "identifier": phone,
        "password": password
    }
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, json=data)
            logging.info(f"Sign-in response status: {response.status_code}")
            logging.info(f"Sign-in response text: {response.text}")
            if response.status_code == 200:
                response_data = response.json()
                token = response_data["access_token"]
                user_id = response_data["user_id"]
                logging.info(f"User {phone} signed in successfully.")
                return token, user_id
            else:
                logging.error(f"Sign-in failed for {phone}: {response.text}")
                return None, None
        except Exception as e:
            logging.error(f"Error during sign-in for {phone}: {e}")
            return None, None

async def create_room(token):
    url = "http://localhost:8000/api/v1/rooms"
    data = {
        "name": "messaging_room_test",  # Fixed room name
        "type": "user"
    }
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, json=data, headers={"Authorization": f"Bearer {token}"})
            if response.status_code == 200:
                room_id = response.json()["id"]
                logging.info(f"Room created successfully with ID: {room_id}")
                return room_id
            else:
                logging.error(f"Failed to create room: {response.text}")
                return None
        except Exception as e:
            logging.error(f"Error creating room: {e}")
            return None

async def add_user_to_room(room_id, user_id, token):
    url = f"http://localhost:8000/api/v1/rooms/{room_id}/participants"
    data = {
        "user_id": user_id
    }
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, json=data, headers={"Authorization": f"Bearer {token}"})
            if response.status_code == 200:
                logging.info(f"User {user_id} added to room {room_id} successfully.")
            else:
                logging.error(f"Failed to add user {user_id} to room {room_id}: {response.text}")
        except Exception as e:
            logging.error(f"Error adding user {user_id} to room {room_id}: {e}")

async def main():
    # Sign up and sign in for User 1
    await sign_up(USER1_PHONE, USER1_PASSWORD)
    token1, user1_id = await sign_in(USER1_PHONE, USER1_PASSWORD)
    if not token1 or not user1_id:
        logging.error("Failed to obtain token for User 1. Exiting.")
        return

    # Sign up and sign in for User 2
    await sign_up(USER2_PHONE, USER2_PASSWORD)
    token2, user2_id = await sign_in(USER2_PHONE, USER2_PASSWORD)
    if not token2 or not user2_id:
        logging.error("Failed to obtain token for User 2. Exiting.")
        return

    # Create a room
    room_id = await create_room(token1)
    if not room_id:
        logging.error("Failed to create room. Exiting.")
        return

    # Add User 1 to the room
    await add_user_to_room(room_id, user1_id, token1)

    # Add User 2 to the room using User 1's token
    await add_user_to_room(room_id, user2_id, token1)

if __name__ == "__main__":
    asyncio.run(main()) 