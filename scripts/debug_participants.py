import asyncio
import httpx
import random
import uuid

API_URL = "http://localhost:8000/api/v1"

def generate_random_phone():
    """Generate a random 6-digit phone number"""
    return f"+1{random.randint(100000, 999999)}"

async def signup_user(phone: str, password: str):
    """Sign up a new user"""
    async with httpx.AsyncClient() as client:
        payload = {
            "phone_number": phone,
            "password": password
        }
        resp = await client.post(f"{API_URL}/auth/signup", json=payload)
        print(f"[SIGNUP] User {phone}:", resp.status_code, resp.json())
        return resp.json()

async def login_user(phone: str, password: str):
    """Login a user and return their token"""
    async with httpx.AsyncClient() as client:
        payload = {
            "identifier": phone,
            "password": password
        }
        resp = await client.post(f"{API_URL}/auth/signin", json=payload)
        resp.raise_for_status()
        token = resp.json()["access_token"]
        print(f"[LOGIN] User {phone}:", resp.status_code)
        return token

async def create_room(token: str, name: str = "Test Room"):
    """Create a new room"""
    async with httpx.AsyncClient() as client:
        payload = {
            "name": name,
            "description": "Room created by debug script",
            "type": "user"  # Default to user type for debug rooms
        }
        headers = {"Authorization": f"Bearer {token}"}
        resp = await client.post(f"{API_URL}/rooms", json=payload, headers=headers)
        print("[CREATE ROOM]:", resp.status_code, resp.json())
        return resp.json()

async def search_rooms(token: str, query: str = ""):
    """Search for rooms"""
    async with httpx.AsyncClient() as client:
        headers = {"Authorization": f"Bearer {token}"}
        params = {"query": query}
        resp = await client.get(f"{API_URL}/rooms/search", params=params, headers=headers)
        print("[SEARCH ROOMS]:", resp.status_code, resp.json())
        return resp.json()

async def search_users(token: str, query: str):
    """Search for users globally"""
    async with httpx.AsyncClient() as client:
        headers = {"Authorization": f"Bearer {token}"}
        params = {"query": query}
        resp = await client.get(f"{API_URL}/rooms/users/search", params=params, headers=headers)
        print("[SEARCH USERS]:", resp.status_code, resp.json())
        return resp.json()

async def add_participant(token: str, room_id: str, user_id: str):
    """Add a participant to a room"""
    async with httpx.AsyncClient() as client:
        payload = {
            "user_id": user_id,
            "role": "member",
            "status": "active"
        }
        headers = {"Authorization": f"Bearer {token}"}
        resp = await client.post(f"{API_URL}/rooms/{room_id}/participants", json=payload, headers=headers)
        print("[ADD PARTICIPANT]:", resp.status_code, resp.json())
        return resp

async def search_room_participants(token: str, room_id: str, query: str = ""):
    """Search for participants in a room"""
    async with httpx.AsyncClient() as client:
        headers = {"Authorization": f"Bearer {token}"}
        params = {"query": query}
        resp = await client.get(f"{API_URL}/rooms/{room_id}/participants/search", params=params, headers=headers)
        print("[SEARCH ROOM PARTICIPANTS]:", resp.status_code, resp.json())
        return resp.json()

async def remove_participant(token: str, room_id: str, user_id: str):
    """Remove a participant from a room"""
    async with httpx.AsyncClient() as client:
        headers = {"Authorization": f"Bearer {token}"}
        resp = await client.delete(f"{API_URL}/rooms/{room_id}/participants/{user_id}", headers=headers)
        print("[REMOVE PARTICIPANT]:", resp.status_code, resp.text)
        return resp

async def delete_room(token: str, room_id: str):
    """Delete a room"""
    async with httpx.AsyncClient() as client:
        headers = {"Authorization": f"Bearer {token}"}
        resp = await client.delete(f"{API_URL}/rooms/{room_id}", headers=headers)
        print("[DELETE ROOM]:", resp.status_code, resp.text)
        return resp

async def main():
    try:
        # Generate random phone numbers and passwords for two users
        user1_phone = generate_random_phone()
        user2_phone = generate_random_phone()
        password = "testpassword123"  # Same password for both users for simplicity

        print(f"Generated phone numbers:")
        print(f"User 1: {user1_phone}")
        print(f"User 2: {user2_phone}")

        # Sign up both users
        user1_data = await signup_user(user1_phone, password)
        user2_data = await signup_user(user2_phone, password)

        # Login with first user
        user1_token = await login_user(user1_phone, password)

        # Create a room with user1
        room_data = await create_room(user1_token)
        room_id = room_data["id"]

        # Search for the created room
        rooms = await search_rooms(user1_token, room_data["name"])
        print(f"Found {len(rooms['rooms'])} rooms matching the search")

        # Search for the second user globally
        users = await search_users(user1_token, user2_phone)
        if not users or not users.get('users'):
            raise Exception("Could not find second user in global search")
        found_user = users['users'][0]  # Get first user from response
        print(f"Found user in global search: {found_user}")

        # Add the found user to the room
        await add_participant(user1_token, room_id, found_user["id"])

        # After adding participant, test both empty and specific queries
        print("\nTesting participant search with empty query:")
        participants = await search_room_participants(user1_token, room_id, "")
        print(f"[SEARCH ROOM PARTICIPANTS (empty query)]: {participants}")
        print(f"Found {len(participants['participants'])} participants with empty query")

        print("\nTesting participant search with specific query:")
        participants = await search_room_participants(user1_token, room_id, user2_phone)
        print(f"[SEARCH ROOM PARTICIPANTS (specific query)]: {participants}")
        print(f"Found {len(participants['participants'])} participants matching query '{user2_phone}'")

        # Remove the user from the room
        await remove_participant(user1_token, room_id, found_user["id"])

        # Delete the room
        await delete_room(user1_token, room_id)

        print("\nTest completed successfully!")
        print(f"Room ID: {room_id}")
        print(f"User 1 ID: {user1_data['id']}")
        print(f"User 2 ID: {user2_data['id']}")

    except Exception as e:
        print(f"An error occurred: {str(e)}")
        raise

if __name__ == "__main__":
    asyncio.run(main()) 