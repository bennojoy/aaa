import asyncio
import logging
import httpx

# === Logging Setup ===
logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')

# === User Setup ===
USER1_PHONE = "+15509990001"
USER1_PASSWORD = "pwuser1new2024"
USER2_ID = "33d6e677-7698-4f7d-9853-fe1656798def"  # User 2's ID

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

async def remove_user_from_room(token: str, room_id: str, user_id: str):
    url = f"http://localhost:8000/api/v1/rooms/{room_id}/participants/{user_id}"
    headers = {"Authorization": f"Bearer {token}"}
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.delete(url, headers=headers)
            if response.status_code == 200:
                logging.info(f"Successfully removed user {user_id} from room {room_id}")
                return True
            else:
                logging.error(f"Failed to remove user: {response.text}")
                return False
        except Exception as e:
            logging.error(f"Error removing user: {e}")
            return False

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
                logging.error(f"Failed to add user: {response.text}")
                return False
        except Exception as e:
            logging.error(f"Error adding user: {e}")
            return False

async def main():
    # Sign in as User 1 (room owner)
    token, user_id = await sign_in()
    if not token or not user_id:
        logging.error("Failed to obtain token. Exiting.")
        return

    # Room ID from create_users_and_room.py
    room_id = "13dce537-e0c1-4b07-a17d-4f24982f0263"
    
    # Remove User 2 from the room
    if not await remove_user_from_room(token, room_id, USER2_ID):
        logging.error("Failed to remove User 2. Exiting.")
        return

    # Add User 2 back to the room
    if not await add_user_to_room(token, room_id, USER2_ID):
        logging.error("Failed to add User 2 back. Exiting.")
        return

    logging.info("Successfully cleaned up and re-added User 2")

if __name__ == "__main__":
    asyncio.run(main()) 