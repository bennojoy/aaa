import asyncio
import httpx
import uuid
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from datetime import datetime
import json

console = Console()

def print_request(method: str, url: str, headers: dict, data: dict = None):
    """Print request details in a formatted panel"""
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Key")
    table.add_column("Value")
    
    table.add_row("Method", method)
    table.add_row("URL", url)
    
    for key, value in headers.items():
        if key.lower() == "authorization":
            value = "Bearer <token>"
        table.add_row(key, str(value))
    
    if data:
        table.add_row("Data", json.dumps(data, indent=2))
    
    console.print(Panel(table, title="Request", border_style="blue"))

def print_response(status_code: int, headers: dict, data: dict):
    """Print response details in a formatted panel"""
    table = Table(show_header=True, header_style="bold green")
    table.add_column("Key")
    table.add_column("Value")
    
    table.add_row("Status Code", str(status_code))
    
    for key, value in headers.items():
        table.add_row(key, str(value))
    
    table.add_row("Data", json.dumps(data, indent=2))
    
    console.print(Panel(table, title="Response", border_style="green"))

async def create_system_user(client: httpx.AsyncClient) -> dict:
    """Create a system user for testing"""
    url = "http://localhost:8000/api/v1/auth/signup"
    data = {
        "phone_number": f"+1{str(uuid.uuid4().int)[:10]}",
        "password": "system123"
    }
    
    print_request("POST", url, client.headers, data)
    response = await client.post(url, json=data)
    print_response(response.status_code, dict(response.headers), response.json())
    
    return response.json()

async def get_system_token(client: httpx.AsyncClient, phone_number: str) -> str:
    """Get JWT token for system user"""
    url = "http://localhost:8000/api/v1/auth/signin"
    data = {
        "identifier": phone_number,
        "password": "system123"
    }
    
    print_request("POST", url, client.headers, data)
    response = await client.post(url, json=data)
    print_response(response.status_code, dict(response.headers), response.json())
    
    return response.json()["access_token"]

async def create_test_room(client: httpx.AsyncClient) -> dict:
    """Create a test room"""
    url = "http://localhost:8000/api/v1/rooms"
    data = {
        "name": "Test Room",
        "description": "Room for testing message permissions",
        "type": "user"
    }
    
    print_request("POST", url, client.headers, data)
    response = await client.post(url, json=data)
    print_response(response.status_code, dict(response.headers), response.json())
    
    return response.json()

async def create_test_user(client: httpx.AsyncClient) -> dict:
    """Create a test user to check permissions for"""
    url = "http://localhost:8000/api/v1/auth/signup"
    data = {
        "phone_number": f"+1{str(uuid.uuid4().int)[:10]}",
        "password": "test123"
    }
    
    print_request("POST", url, client.headers, data)
    response = await client.post(url, json=data)
    print_response(response.status_code, dict(response.headers), response.json())
    
    return response.json()

async def add_user_to_room(client: httpx.AsyncClient, room_id: str, user_id: str):
    """Add test user to room"""
    url = f"http://localhost:8000/api/v1/rooms/rooms/{room_id}/participants"
    data = {
        "user_id": user_id
    }
    
    print_request("POST", url, client.headers, data)
    response = await client.post(url, json=data)
    print_response(response.status_code, dict(response.headers), response.json())

async def check_message_permission(
    client: httpx.AsyncClient,
    room_id: str,
    user_id: str,
    trace_id: str
):
    """Check message permission for user in room"""
    url = f"http://localhost:8000/api/v1/rooms/{room_id}/message-permission/{user_id}"
    headers = {
        **client.headers,
        "X-Trace-ID": trace_id
    }
    
    print_request("GET", url, headers)
    response = await client.get(url, headers=headers)
    print_response(response.status_code, dict(response.headers), response.json())

async def main():
    trace_id = str(uuid.uuid4())
    console.print(f"\n[bold blue]Starting test with trace_id: {trace_id}[/bold blue]\n")
    
    async with httpx.AsyncClient() as client:
        # Create system user
        console.print("\n[bold yellow]1. Creating system user[/bold yellow]")
        system_user = await create_system_user(client)
        
        # Get system token
        console.print("\n[bold yellow]2. Getting system token[/bold yellow]")
        token = await get_system_token(client, system_user["phone_number"])
        client.headers["Authorization"] = f"Bearer {token}"
        
        # Create test room
        console.print("\n[bold yellow]3. Creating test room[/bold yellow]")
        room = await create_test_room(client)
        
        # Create test user
        console.print("\n[bold yellow]4. Creating test user[/bold yellow]")
        test_user = await create_test_user(client)
        
        # Add test user to room
        console.print("\n[bold yellow]5. Adding test user to room[/bold yellow]")
        await add_user_to_room(client, room["id"], test_user["id"])
        
        # Check message permission
        console.print("\n[bold yellow]6. Checking message permission[/bold yellow]")
        await check_message_permission(client, room["id"], test_user["id"], trace_id)

if __name__ == "__main__":
    asyncio.run(main()) 