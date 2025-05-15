import logging
import httpx
from typing import Dict

async def check_message_permission(
    client: httpx.AsyncClient,
    room_id: str,
    user_id: str,
    trace_id: str,
    token: str
) -> Dict:
    """Check if user can send messages in room and get participants"""
    url = f"http://localhost:8000/api/v1/rooms/{room_id}/message-permission/{user_id}"
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Trace-ID": trace_id
    }
    
    logging.info(f"Checking message permission - URL: {url}, Headers: {headers}")
    response = await client.get(url, headers=headers)
    logging.info(f"Permission check response - Status: {response.status_code}, Body: {response.text}")
    
    if response.status_code != 200:
        raise Exception(f"Permission check failed: {response.text}")
        
    return response.json() 