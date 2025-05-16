import asyncio
import httpx
import json
import sys
import os
from typing import Dict
import random

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configuration
BASE_URL = "http://localhost:8000"
API_V1_STR = "/api/v1"

async def make_request(
    client: httpx.AsyncClient,
    method: str,
    endpoint: str,
    data: Dict = None,
    headers: Dict = None
) -> Dict:
    """Helper function to make HTTP requests"""
    url = f"{BASE_URL}{endpoint}"
    response = await client.request(method, url, json=data, headers=headers)
    response.raise_for_status()
    return response.json()

async def main():
    # Generate unique phone number for test
    random_digits = random.randint(100000, 999999)
    test_phone = f"+1{random_digits}"
    test_password = "testpassword123"

    async with httpx.AsyncClient() as client:
        try:
            # 1. Create a new user
            print("Creating new user...")
            user_data = {
                "phone_number": test_phone,
                "password": test_password,
                "language": "en"
            }
            try:
                user = await make_request(client, "POST", f"{API_V1_STR}/auth/signup", data=user_data)
                print(f"User created with phone: {test_phone}")
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 400 and "already registered" in e.response.text:
                    print("User already exists, proceeding with login...")
                else:
                    raise

            # 2. Login to get access token
            print("\nLogging in...")
            login_data = {
                "identifier": test_phone,
                "password": test_password
            }
            auth_response = await make_request(client, "POST", f"{API_V1_STR}/auth/signin", data=login_data)
            access_token = auth_response["access_token"]
            print("Login successful!")

            # Set up headers with authentication
            headers = {"Authorization": f"Bearer {access_token}"}

            # 3. Create a new room
            print("\nCreating new room...")
            room_data = {
                "name": "Test Language Room",
                "description": "Room for testing language preferences"
            }
            room = await make_request(client, "POST", f"{API_V1_STR}/rooms", data=room_data, headers=headers)
            room_id = room["id"]
            print(f"Room created: {room['name']}")

            # 4. Set language preferences
            print("\nSetting language preferences...")
            language_preferences = {
                "outgoing_language": "es",  # Spanish for outgoing messages
                "incoming_language": "it"   # Italian for incoming messages
            }
            
            preferences = await make_request(
                client,
                "PUT",
                f"/api/users/{user['id']}/rooms/{room_id}/language-preferences",
                data=language_preferences,
                headers=headers
            )
            
            print("\nLanguage preferences set successfully!")
            print(f"Outgoing language: {preferences['outgoing_language']}")
            print(f"Incoming language: {preferences['incoming_language']}")

            # 5. Verify preferences
            print("\nVerifying preferences...")
            verify_preferences = await make_request(
                client,
                "GET",
                f"/api/users/{user['id']}/rooms/{room_id}/language-preferences",
                headers=headers
            )
            
            print("\nVerification successful!")
            print(f"Current preferences:")
            print(f"Outgoing language: {verify_preferences['outgoing_language']}")
            print(f"Incoming language: {verify_preferences['incoming_language']}")

        except httpx.HTTPStatusError as e:
            print(f"HTTP error occurred: {e.response.text}")
            raise
        except Exception as e:
            print(f"Error: {str(e)}")
            raise

if __name__ == "__main__":
    asyncio.run(main()) 