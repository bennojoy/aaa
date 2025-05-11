import requests
import json
from auth_debug import get_auth_token, API_URL

def create_room(token: str, name: str, description: str = None) -> dict:
    """Create a new room"""
    headers = {"Authorization": f"Bearer {token}"}
    data = {"name": name, "description": description}
    
    print(f"\nCreating room: {name}")
    response = requests.post(f"{API_URL}/rooms", headers=headers, json=data)
    print(f"Status Code: {response.status_code}")
    try:
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.json()
    except json.JSONDecodeError:
        print(f"Raw Response: {response.text}")
        return None

def search_rooms(token: str, query: str) -> dict:
    """Search rooms by name"""
    headers = {"Authorization": f"Bearer {token}"}
    
    print(f"\nSearching rooms with query: {query}")
    response = requests.get(f"{API_URL}/rooms/search?query={query}", headers=headers)
    print(f"Status Code: {response.status_code}")
    try:
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.json()
    except json.JSONDecodeError:
        print(f"Raw Response: {response.text}")
        return None

def list_rooms(token: str) -> dict:
    """List all rooms"""
    headers = {"Authorization": f"Bearer {token}"}
    
    print("\nListing all rooms")
    response = requests.get(f"{API_URL}/rooms", headers=headers)
    print(f"Status Code: {response.status_code}")
    try:
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.json()
    except json.JSONDecodeError:
        print(f"Raw Response: {response.text}")
        return None

def get_room_details(token: str, room_id: str) -> dict:
    """Get room details"""
    headers = {"Authorization": f"Bearer {token}"}
    
    print(f"\nGetting details for room: {room_id}")
    response = requests.get(f"{API_URL}/rooms/{room_id}", headers=headers)
    print(f"Status Code: {response.status_code}")
    try:
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.json()
    except json.JSONDecodeError:
        print(f"Raw Response: {response.text}")
        return None

def main():
    # Get auth token
    token = get_auth_token()
    if not token:
        print("Failed to get auth token")
        return

    print(f"\nGot token: {token[:20]}...")

    # Create a test room
    room = create_room(token, "Test Room", "This is a test room")
    room_id = None
    
    # If room creation failed but we got a response, try to get the room ID from search
    if not room or not room.get("id"):
        print("\nRoom creation failed or room already exists, searching for existing room...")
        search_result = search_rooms(token, "Test")
        if search_result and search_result.get("rooms") and len(search_result["rooms"]) > 0:
            room_id = search_result["rooms"][0]["id"]
            print(f"Found existing room with ID: {room_id}")
    else:
        room_id = room["id"]
    
    if room_id:
        # List all rooms
        list_rooms(token)
        
        # Get room details
        get_room_details(token, room_id)
    else:
        print("Failed to find or create a room to work with")

if __name__ == "__main__":
    main() 