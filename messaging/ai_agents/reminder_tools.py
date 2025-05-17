from .api_client import APIClient
from agents import function_tool, RunContextWrapper
from messaging.ai_agents.agent_context import UserContext
import logging
from typing import Optional
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)
api_client = APIClient()

@function_tool
async def create_reminder_tool(
    session: RunContextWrapper[UserContext],
    title: str,
    description: Optional[str] = None,
    start_time: Optional[str] = None,  # ISO format datetime string
    rrule: Optional[str] = None  # RRule string for recurrence
) -> str:
    """Create a new reminder in the current room."""
    if not session.context.sender_id or not session.context.room:
        return "Error: Missing user IDs in context"
    
    try:
        # If no start_time provided, default to 1 hour from now
        if not start_time:
            start_time = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
            
        response = await api_client.make_request(
            "POST",
            "/v1/reminders/",
            data={
                "room_id": session.context.room,
                "created_by_user_id": session.context.sender_id,
                "title": title,
                "description": description,
                "start_time": start_time,
                "rrule": rrule
            },
            headers={"Authorization": f"Bearer {session.context.token}"}
        )
        return f"Successfully created reminder: {title}"
    except Exception as e:
        logger.error(f"Error creating reminder: {str(e)}")
        return f"Error creating reminder: {str(e)}"

@function_tool
async def list_room_reminders_tool(
    session: RunContextWrapper[UserContext]
) -> str:
    """List all reminders in the current room."""
    if not session.context.sender_id or not session.context.room:
        return "Error: Missing user IDs in context"
    
    try:
        response = await api_client.make_request(
            "GET",
            f"/v1/reminders/room/{session.context.room}/",
            headers={"Authorization": f"Bearer {session.context.token}"}
        )
        reminders = response
        if not reminders:
            return "No reminders found in this room"
        
        result = "Room reminders:\n"
        for reminder in reminders:
            result += f"- {reminder['title']}: {reminder['next_trigger_time']}\n"
        return result
    except Exception as e:
        logger.error(f"Error listing reminders: {str(e)}")
        return f"Error listing reminders: {str(e)}"

@function_tool
async def update_reminder_tool(
    session: RunContextWrapper[UserContext],
    reminder_id: str,
    title: Optional[str] = None,
    description: Optional[str] = None,
    start_time: Optional[str] = None,
    rrule: Optional[str] = None
) -> str:
    """Update an existing reminder."""
    if not session.context.sender_id or not session.context.room:
        return "Error: Missing user IDs in context"
    
    try:
        update_data = {}
        if title is not None:
            update_data["title"] = title
        if description is not None:
            update_data["description"] = description
        if start_time is not None:
            update_data["start_time"] = start_time
        if rrule is not None:
            update_data["rrule"] = rrule
            
        response = await api_client.make_request(
            "PUT",
            f"/v1/reminders/{reminder_id}/",
            data=update_data,
            headers={"Authorization": f"Bearer {session.context.token}"}
        )
        return f"Successfully updated reminder: {response['title']}"
    except Exception as e:
        logger.error(f"Error updating reminder: {str(e)}")
        return f"Error updating reminder: {str(e)}"

@function_tool
async def delete_reminder_tool(
    session: RunContextWrapper[UserContext],
    reminder_id: str
) -> str:
    """Delete a reminder."""
    if not session.context.sender_id or not session.context.room:
        return "Error: Missing user IDs in context"
    
    try:
        response = await api_client.make_request(
            "DELETE",
            f"/v1/reminders/{reminder_id}/",
            headers={"Authorization": f"Bearer {session.context.token}"}
        )
        return f"Successfully deleted reminder: {response['title']}"
    except Exception as e:
        logger.error(f"Error deleting reminder: {str(e)}")
        return f"Error deleting reminder: {str(e)}" 