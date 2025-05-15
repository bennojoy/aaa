import asyncio
import logging
import httpx

# === Logging Setup ===
logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')

# === User Setup ===
USER1_PHONE = "+15509990001"
USER1_PASSWORD = "pwuser1new2024"
USER2_ID = "552995d0-759f-4cf8-a6e9-43eb7859d5d3"  # User 2's ID
ROOM_ID = "0b09026d-c96b-4234-8fe4-f484ebf51759"  # Room ID from setup

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

    # Try to add User 2 again (should fail with 409 Conflict)
    if not await add_user_to_room(token, ROOM_ID, USER2_ID):
        logging.info("As expected, failed to add duplicate participant")
    else:
        logging.error("Unexpected: Successfully added duplicate participant!")

if __name__ == "__main__":
    asyncio.run(main()) 