from .api_client import APIClient
from agents import function_tool, RunContextWrapper
from messaging.ai_agents.agent_context import UserContext
import logging
from typing import Optional

logger = logging.getLogger(__name__)
api_client = APIClient()

@function_tool
async def set_outgoing_translation_tool(
    session: RunContextWrapper[UserContext],
    target_language: str
) -> str:
    """Set translation preference for outgoing messages."""
    if not session.context.sender_id or not session.context.room:
        return "Error: Missing user IDs in context"
    
    try:
        response = await api_client.make_request(
            "PUT",
            f"/users/{session.context.sender_id}/rooms/{session.context.room}/language-preferences",
            data={
                "outgoing_language": target_language,
                "incoming_language": None  # Keep existing value
            },
            headers={"Authorization": f"Bearer {session.context.token}"}
        )
        return f"Successfully set outgoing messages to {target_language}"
    except Exception as e:
        logger.error(f"Error setting outgoing language: {str(e)}")
        return f"Error setting language preference: {str(e)}"

@function_tool
async def set_incoming_translation_tool(
    session: RunContextWrapper[UserContext],
    target_language: str
) -> str:
    """Set translation preference for incoming messages."""
    if not session.context.sender_id or not session.context.room:
        return "Error: Missing user IDs in context"
    
    try:
        response = await api_client.make_request(
            "PUT",
            f"/users/{session.context.sender_id}/rooms/{session.context.room}/language-preferences",
            data={
                "outgoing_language": None,  # Keep existing value
                "incoming_language": target_language
            },
            headers={"Authorization": f"Bearer {session.context.token}"}
        )
        return f"Successfully set incoming messages to {target_language}"
    except Exception as e:
        logger.error(f"Error setting incoming language: {str(e)}")
        return f"Error setting language preference: {str(e)}"

@function_tool
async def clear_translation_tool(
    session: RunContextWrapper[UserContext],
    direction: Optional[str] = None
) -> str:
    """Clear translation preference."""
    if not session.context.sender_id or not session.context.room:
        return "Error: Missing user IDs in context"
    
    try:
        if direction == "outgoing":
            response = await api_client.make_request(
                "PUT",
                f"/users/{session.context.sender_id}/rooms/{session.context.room}/language-preferences",
                data={
                    "outgoing_language": None,  # Reset to None
                    "incoming_language": None  # Keep existing value
                },
                headers={"Authorization": f"Bearer {session.context.token}"}
            )
            return "Successfully cleared outgoing translation preferences"
        elif direction == "incoming":
            response = await api_client.make_request(
                "PUT",
                f"/users/{session.context.sender_id}/rooms/{session.context.room}/language-preferences",
                data={
                    "outgoing_language": None,  # Keep existing value
                    "incoming_language": None  # Reset to None
                },
                headers={"Authorization": f"Bearer {session.context.token}"}
            )
            return "Successfully cleared incoming translation preferences"
        else:
            # Clear both preferences using DELETE endpoint
            response = await api_client.make_request(
                "DELETE",
                f"/users/{session.context.sender_id}/rooms/{session.context.room}/language-preferences",
                headers={"Authorization": f"Bearer {session.context.token}"}
            )
            return "Successfully cleared all translation preferences"
    except Exception as e:
        logger.error(f"Error clearing language preferences: {str(e)}")
        return f"Error clearing language preferences: {str(e)}"