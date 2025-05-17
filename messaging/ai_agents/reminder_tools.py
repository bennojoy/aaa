from .api_client import APIClient
from agents import function_tool, RunContextWrapper
from messaging.ai_agents.agent_context import UserContext
import logging
from typing import Optional
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)
api_client = APIClient()

def format_local_time(utc_time: str, offset_minutes: int) -> str:
    """Convert UTC time to local time with timezone indicator."""
    try:
        # Parse UTC time
        dt = datetime.fromisoformat(utc_time.replace('Z', '+00:00'))
        
        # Convert to local time
        local_dt = dt + timedelta(minutes=offset_minutes)
        
        # Format time
        time_str = local_dt.strftime("%I:%M %p")  # e.g., "09:00 AM"
        
        # Get timezone name based on offset
        if offset_minutes == 420:  # UTC+7
            tz_name = "Jakarta time"
        elif offset_minutes == 0:
            tz_name = "UTC"
        else:
            # Format offset as +/-HH:MM
            hours = abs(offset_minutes) // 60
            minutes = abs(offset_minutes) % 60
            sign = "+" if offset_minutes >= 0 else "-"
            tz_name = f"UTC{sign}{hours:02d}:{minutes:02d}"
        
        return f"{time_str} ({tz_name})"
    except Exception as e:
        logger.error(f"Error formatting time: {str(e)}")
        return utc_time  # Return original time if conversion fails

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
        else:
            # If start_time is provided, ensure it's in UTC
            # First parse the local time
            local_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            
            # If the year is not set (or is old), use current year
            current_year = datetime.now(timezone.utc).year
            if local_dt.year < current_year:
                local_dt = local_dt.replace(year=current_year)
            
            # Convert to UTC by adding the offset (since local time is ahead of UTC)
            if session.context.timezone_offset is not None:
                utc_dt = local_dt + timedelta(minutes=session.context.timezone_offset)
                start_time = utc_dt.isoformat()
            
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
        
        # Format the response with local time if timezone offset is available
        if session.context.timezone_offset is not None:
            local_time = format_local_time(response['start_time'], session.context.timezone_offset)
            return f"Successfully created reminder: {title} at {local_time}"
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
            # Format time in local timezone if offset is available
            if session.context.timezone_offset is not None:
                time_str = format_local_time(reminder['next_trigger_time'], session.context.timezone_offset)
            else:
                time_str = reminder['next_trigger_time']
            result += f"- {reminder['title']}: {time_str}\n"
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
            # Convert local time to UTC before updating
            local_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            if session.context.timezone_offset is not None:
                utc_dt = local_dt - timedelta(minutes=session.context.timezone_offset)
                update_data["start_time"] = utc_dt.isoformat()
            else:
                update_data["start_time"] = start_time
        if rrule is not None:
            update_data["rrule"] = rrule
            
        response = await api_client.make_request(
            "PUT",
            f"/v1/reminders/{reminder_id}/",
            data=update_data,
            headers={"Authorization": f"Bearer {session.context.token}"}
        )
        
        # Format the response with local time if timezone offset is available
        if session.context.timezone_offset is not None and 'start_time' in response:
            local_time = format_local_time(response['start_time'], session.context.timezone_offset)
            return f"Successfully updated reminder: {response['title']} at {local_time}"
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