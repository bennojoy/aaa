from agents import function_tool, RunContextWrapper
from messaging.ai_agents.agent_context import UserContext

import logging
import json

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)



@function_tool
async def set_outgoing_translation_tool(
    session: RunContextWrapper[UserContext],
    target_language: str
) -> str:
    """Set translation preference for outgoing messages."""
    if not session.context.user_id or not session.context.target_user_id:
        return "Error: Missing user IDs in context"
    
  
    return ""

@function_tool
async def set_incoming_translation_tool(
    session: RunContextWrapper[UserContext],
    target_language: str
) -> str:
    """Set translation preference for incoming messages."""
    if not session.context.user_id or not session.context.target_user_id:
        return "Error: Missing user IDs in context"
    
 
    return ""

@function_tool
async def clear_translation_tool(
    session: RunContextWrapper[UserContext],
    direction: str = None
) -> str:
    """Clear translation preference."""
    if not session.context.user_id or not session.context.target_user_id:
        return "Error: Missing user IDs in context"
    

    return ""