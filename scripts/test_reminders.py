import asyncio
import httpx
import json
import sys
import os
from typing import Dict
import random
from datetime import datetime, timedelta, timezone

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
    response = await client.request(
        method, 
        url, 
        json=data, 
        headers=headers,
        follow_redirects=True  # Follow redirects automatically
    )
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
                "name": "Test Reminder Room",
                "description": "Room for testing reminders"
            }
            room = await make_request(client, "POST", f"{API_V1_STR}/rooms", data=room_data, headers=headers)
            room_id = room["id"]
            print(f"Room created: {room['name']}")

            # 4. Create a reminder
            print("\nCreating a reminder...")
            # Set reminder time to 1 hour from now
            reminder_time = datetime.now(timezone.utc) + timedelta(hours=1)
            reminder_data = {
                "room_id": room_id,
                "created_by_user_id": user["id"],  # Add the user ID
                "title": "Test Reminder",
                "description": "This is a test reminder",
                "start_time": reminder_time.isoformat(),
                "rrule": "FREQ=DAILY;COUNT=3"  # Daily reminder for 3 days
            }
            
            reminder = await make_request(
                client,
                "POST",
                f"{API_V1_STR}/reminders",  # This is now correct since the router has the /reminders prefix
                data=reminder_data,
                headers=headers
            )
            print("\nReminder created successfully!")
            print(f"Reminder ID: {reminder['id']}")
            print(f"Title: {reminder['title']}")
            print(f"Next trigger: {reminder['next_trigger_time']}")

            # 5. Get room reminders
            print("\nFetching room reminders...")
            room_reminders = await make_request(
                client,
                "GET",
                f"{API_V1_STR}/reminders/room/{room_id}",
                headers=headers
            )
            print(f"\nFound {len(room_reminders)} reminders in room:")
            for r in room_reminders:
                print(f"- {r['title']} (ID: {r['id']})")

            # 6. Get user created reminders
            print("\nFetching user created reminders...")
            user_reminders = await make_request(
                client,
                "GET",
                f"{API_V1_STR}/reminders/user/created",
                headers=headers
            )
            print(f"\nFound {len(user_reminders)} reminders created by user:")
            for r in user_reminders:
                print(f"- {r['title']} (ID: {r['id']})")

            # 7. Update the reminder
            print("\nUpdating reminder...")
            update_data = {
                "title": "Updated Test Reminder",
                "description": "This is an updated test reminder"
            }
            updated_reminder = await make_request(
                client,
                "PUT",
                f"{API_V1_STR}/reminders/{reminder['id']}",
                data=update_data,
                headers=headers
            )
            print("\nReminder updated successfully!")
            print(f"New title: {updated_reminder['title']}")
            print(f"New description: {updated_reminder['description']}")

            # 8. Delete the reminder
            print("\nDeleting reminder...")
            deleted_reminder = await make_request(
                client,
                "DELETE",
                f"{API_V1_STR}/reminders/{reminder['id']}",
                headers=headers
            )
            print("\nReminder deleted successfully!")
            print(f"Deleted reminder ID: {deleted_reminder['id']}")

        except httpx.HTTPStatusError as e:
            print(f"HTTP error occurred: {e.response.text}")
            raise
        except Exception as e:
            print(f"Error: {str(e)}")
            raise

if __name__ == "__main__":
    asyncio.run(main()) 