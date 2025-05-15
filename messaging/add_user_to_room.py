import asyncio
import logging
import httpx

# === Logging Setup ===
logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')

# === User Setup ===
USER1_PHONE = "+15509990001"  # User 1's phone (room owner)
USER1_PASSWORD = "pwuser1new2024"  # User 1's password
USER2_PHONE = "+15509990002"  # User 2's phone
USER2_PASSWORD = "pwuser2new2024"  # User 2's password

async def sign_in(phone: str, password: str):
    url = "http://localhost:8000/api/v1/auth/signin"
    data = {
        "identifier": phone,
        "password": password
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

async def search_room(token, room_name):
    url = "http://localhost:8000/api/v1/rooms/search"
    params = {"name": room_name}
    headers = {"Authorization": f"Bearer {token}"}
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, params=params, headers=headers)
            logging.info(f"Room search response status: {response.status_code}")
            logging.info(f"Room search response text: {response.text}")
            if response.status_code == 200:
                rooms = response.json()["rooms"]
                # Select the first room whose name starts with 'Test Room' and type is 'user'
                for room in rooms:
                    if room["name"].startswith("Test Room") and room["type"] == "user":
                        logging.info(f"Found room: {room['name']} with ID: {room['id']}")
                        return room['id']
                logging.error("No user-created 'Test Room' found.")
                return None
            else:
                logging.error(f"Room search failed: {response.text}")
                return None
        except Exception as e:
            logging.error(f"Error searching for room: {e}")
            return None

async def add_user_to_room(room_id: str, user_id: str, token: str):
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
                logging.info(f"User {user_id} added to room {room_id} successfully")
                return True
            else:
                logging.error(f"Failed to add user {user_id} to room {room_id}: {response.text}")
                return False
        except Exception as e:
            logging.error(f"Error adding user {user_id} to room {room_id}: {e}")
            return False

async def main():
    # Sign in as User 1 (room owner)
    user1_token, user1_id = await sign_in(USER1_PHONE, USER1_PASSWORD)
    if not user1_token or not user1_id:
        logging.error("Failed to sign in as User 1. Exiting.")
        return

    # Sign in as User 2
    user2_token, user2_id = await sign_in(USER2_PHONE, USER2_PASSWORD)
    if not user2_token or not user2_id:
        logging.error("Failed to sign in as User 2. Exiting.")
        return

    # Find the room
    room_id = await search_room(user1_token, "Test Room")
    if not room_id:
        logging.error("Failed to find room. Exiting.")
        return

    # Add User 2 to the room
    success = await add_user_to_room(room_id, user2_id, user1_token)
    if success:
        logging.info("User 2 has been added to the room. You can now run both MQTT clients to chat.")
    else:
        logging.error("Failed to add User 2 to the room.")

if __name__ == "__main__":
    asyncio.run(main()) 