import asyncio
import httpx
import json
from datetime import datetime
import uuid
from typing import Optional, Dict, Any
import logging
import random

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

BASE_URL = "http://localhost:8000/api/v1"

async def make_request(
    client: httpx.AsyncClient,
    method: str,
    endpoint: str,
    data: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
    params: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """Make HTTP request with logging"""
    url = f"{BASE_URL}{endpoint}"
    logger.info(f"Making {method} request to {endpoint}")
    
    try:
        if method == "GET":
            response = await client.get(url, headers=headers, params=params)
        elif method == "POST":
            response = await client.post(url, json=data, headers=headers)
        else:
            raise ValueError(f"Unsupported method: {method}")
        
        response.raise_for_status()
        result = response.json()
        logger.info(f"Request successful: {json.dumps(result, indent=2)}")
        return result
    except httpx.HTTPStatusError as e:
        error_detail = e.response.json().get("detail", str(e))
        logger.error(f"HTTP error occurred: {error_detail}")
        raise
    except httpx.RequestError as e:
        logger.error(f"Request error occurred: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise

async def signup_user(client: httpx.AsyncClient, phone: str, password: str) -> Dict[str, Any]:
    """Sign up a new user using the API"""
    logger.info(f"Signing up user with phone: {phone}")
    data = {
        "phone_number": phone,
        "password": password,
        "language": "en"
    }
    return await make_request(client, "POST", "/auth/signup", data=data)

async def signin_user(client: httpx.AsyncClient, phone: str, password: str) -> Dict[str, Any]:
    """Sign in a user using the API"""
    logger.info(f"Signing in user with phone: {phone}")
    data = {
        "identifier": phone,
        "password": password
    }
    return await make_request(client, "POST", "/auth/signin", data=data)

async def search_rooms(client: httpx.AsyncClient, token: str) -> Dict[str, Any]:
    """Search for rooms using the API"""
    logger.info("Searching for rooms")
    headers = {"Authorization": f"Bearer {token}"}
    params = {"query": ""}  # Empty query is now allowed
    return await make_request(client, "GET", "/rooms/search", headers=headers, params=params)

async def get_room_participants(client: httpx.AsyncClient, token: str, room_id: str) -> Dict[str, Any]:
    """Get participants in a room using the API"""
    logger.info(f"Getting participants for room: {room_id}")
    headers = {"Authorization": f"Bearer {token}"}
    return await make_request(client, "GET", f"/rooms/{room_id}/participants", headers=headers)

async def main():
    """Main test function"""
    logger.info("Starting default room test")
    
    # Generate unique phone number for test in international format (digits only)
    random_digits = random.randint(100000, 999999)  # Exactly 6 digits
    test_phone = f"+1{random_digits}"
    test_password = "testpassword123"
    
    # Strip the '+' from the user's phone number and append '+888'
    assistant_phone = f"+888{test_phone.lstrip('+')}"
    logger.info(f"Assistant phone number: {assistant_phone}")
    
    async with httpx.AsyncClient() as client:
        try:
            # 1. Sign up new user
            logger.info("Step 1: Creating new user")
            signup_response = await signup_user(client, test_phone, test_password)
            user_id = signup_response.get("id")
            logger.info(f"User created with ID: {user_id}")
            
            # 2. Sign in
            logger.info("Step 2: Signing in user")
            signin_response = await signin_user(client, test_phone, test_password)
            token = signin_response.get("access_token")
            logger.info("Successfully signed in")
            
            # 3. Search for rooms
            logger.info("Step 3: Searching for rooms")
            rooms_response = await search_rooms(client, token)
            rooms = rooms_response.get("rooms", [])
            
            # Find default room
            default_room = next((room for room in rooms if room.get("is_default")), None)
            if not default_room:
                logger.error("Default room not found")
                return
            
            room_id = default_room.get("id")
            logger.info(f"Found default room with ID: {room_id}")
            
            # 4. Get room participants
            logger.info("Step 4: Getting room participants")
            participants_response = await get_room_participants(client, token, room_id)
            participants = participants_response.get("participants", [])
            
            # Log participant details with more information
            logger.info("Room participants:")
            for participant in participants:
                participant_id = participant.get("id")
                user_id = participant.get("user_id")
                role = participant.get("role")
                status = participant.get("status")
                joined_at = participant.get("joined_at")
                logger.info(
                    f"- Participant ID: {participant_id}\n"
                    f"  User ID: {user_id}\n"
                    f"  Role: {role}\n"
                    f"  Status: {status}\n"
                    f"  Joined At: {joined_at}"
                )
            
            logger.info("Test completed successfully")
            
        except httpx.HTTPStatusError as e:
            error_detail = e.response.json().get("detail", str(e))
            logger.error(f"API error occurred: {error_detail}")
            raise
        except httpx.RequestError as e:
            logger.error(f"Request error occurred: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Test failed: {str(e)}")
            raise

if __name__ == "__main__":
    asyncio.run(main()) 