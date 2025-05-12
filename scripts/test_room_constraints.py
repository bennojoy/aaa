import asyncio
import httpx
import random
import uuid
from typing import List, Dict
import json

API_URL = "http://localhost:8000/api/v1"

def generate_random_phone() -> str:
    """Generate a random 6-digit phone number"""
    return f"+1{random.randint(100000, 999999)}"

async def signup_user(phone: str, password: str) -> Dict:
    """Sign up a new user"""
    async with httpx.AsyncClient() as client:
        payload = {
            "phone_number": phone,
            "password": password
        }
        resp = await client.post(f"{API_URL}/auth/signup", json=payload)
        print(f"[SIGNUP] User {phone}:", resp.status_code, resp.json())
        return resp.json()

async def login_user(phone: str, password: str) -> str:
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

async def create_room(token: str, name: str = "Test Room") -> Dict:
    """Create a new room"""
    async with httpx.AsyncClient() as client:
        payload = {
            "name": name,
            "description": "Room created by test script",
            "type": "user"  # Default to user type for test rooms
        }
        headers = {"Authorization": f"Bearer {token}"}
        resp = await client.post(f"{API_URL}/rooms", json=payload, headers=headers)
        print("[CREATE ROOM]:", resp.status_code, resp.json())
        return resp.json()

async def add_participant(token: str, room_id: str, user_id: str) -> Dict:
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
        return resp.json()

async def get_room_participants(token: str, room_id: str) -> Dict:
    """Get all participants in a room"""
    async with httpx.AsyncClient() as client:
        headers = {"Authorization": f"Bearer {token}"}
        resp = await client.get(f"{API_URL}/rooms/{room_id}/participants", headers=headers)
        print("[GET ROOM PARTICIPANTS]:", resp.status_code, resp.json())
        return resp.json()

async def test_room_participant_limit():
    """Test the maximum number of participants per room"""
    print("\n=== Testing Room Participant Limit ===")
    
    # Create owner user
    owner_phone = generate_random_phone()
    password = "testpassword123"
    owner_data = await signup_user(owner_phone, password)
    owner_token = await login_user(owner_phone, password)
    
    # Create a room
    room_data = await create_room(owner_token)
    room_id = room_data["id"]
    
    # Create and add participants until we hit the limit
    participants: List[Dict] = []
    try:
        while True:
            # Create new user
            user_phone = generate_random_phone()
            user_data = await signup_user(user_phone, password)
            participants.append(user_data)
            
            # Add user to room
            try:
                await add_participant(owner_token, room_id, user_data["id"])
                print(f"Added participant {len(participants)}")
            except Exception as e:
                if "Room has reached maximum limit" in str(e):
                    print(f"Successfully hit room participant limit at {len(participants)}")
                    break
                else:
                    raise
    except Exception as e:
        print(f"Error during room participant limit test: {str(e)}")
        raise
    
    # Verify final count
    room_participants = await get_room_participants(owner_token, room_id)
    print(f"Final participant count: {len(room_participants['participants'])}")

async def test_user_room_limit():
    """Test the maximum number of rooms per user"""
    print("\n=== Testing User Room Limit ===")
    
    # Create a user who will join multiple rooms
    user_phone = generate_random_phone()
    password = "testpassword123"
    user_data = await signup_user(user_phone, password)
    user_token = await login_user(user_phone, password)
    
    # Create multiple room owners
    rooms: List[Dict] = []
    try:
        while True:
            # Create new room owner
            owner_phone = generate_random_phone()
            owner_data = await signup_user(owner_phone, password)
            owner_token = await login_user(owner_phone, password)
            
            # Create room
            room_data = await create_room(owner_token)
            rooms.append(room_data)
            
            # Add user to room
            try:
                await add_participant(owner_token, room_data["id"], user_data["id"])
                print(f"Added user to room {len(rooms)}")
            except Exception as e:
                if "User has reached maximum limit" in str(e):
                    print(f"Successfully hit user room limit at {len(rooms)}")
                    break
                else:
                    raise
    except Exception as e:
        print(f"Error during user room limit test: {str(e)}")
        raise
    
    print(f"Final room count for user: {len(rooms)}")

async def main():
    """Run all constraint tests"""
    try:
        # Test room participant limit
        await test_room_participant_limit()
        
        # Test user room limit
        await test_user_room_limit()
        
        print("\nAll constraint tests completed successfully!")
        
    except Exception as e:
        print(f"Test failed: {str(e)}")
        raise

if __name__ == "__main__":
    asyncio.run(main()) 