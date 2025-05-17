import logging
import json
from datetime import datetime, timezone, timedelta
from typing import Any, Optional, Dict

from agents import Agent, Runner, function_tool, handoff, RunContextWrapper, WebSearchTool, HandoffInputData
from pydantic import BaseModel
from agents.extensions import handoff_filters

from messaging.ai_agents.agent_context import UserContext
from messaging.ai_agents.translation_tools import (
    set_outgoing_translation_tool,
    set_incoming_translation_tool,
    clear_translation_tool
)
from messaging.ai_agents.reminder_tools import (
    create_reminder_tool,
    list_room_reminders_tool,
    update_reminder_tool,
    delete_reminder_tool
)
from messaging.ai_agents.api_client import APIClient

# ---------- JSON Logger Setup ----------
class JSONFormatter(logging.Formatter):
    def format(self, record):
        if isinstance(record.msg, dict):
            return json.dumps(record.msg)
        return json.dumps({"event": record.msg})

logger = logging.getLogger("agent_logger")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(JSONFormatter())
logger.addHandler(handler)

# ---------- Instructions ----------
def dynamic_reminder_instructions(ctx: RunContextWrapper[UserContext], agent: Agent[UserContext]) -> str:
    now_utc = datetime.now(timezone.utc)
    now_local = now_utc + timedelta(minutes=ctx.context.timezone_offset) if ctx.context.timezone_offset else now_utc
    
    return f"""
    You are a helpful assistant that can manage reminders. You MUST use the provided tools for ALL operations.

    Current Time Context:
    - UTC Time: {now_utc.strftime("%Y-%m-%d %H:%M UTC")}
    - Local Time: {now_local.strftime("%Y-%m-%d %H:%M")} (Jakarta time)

    Available Tools:
    1. create_reminder_tool: Use this tool to create ANY new reminder
       - ALWAYS send times in UTC format
       - NEVER send local times to the tool
       - Example: If user says "tomorrow 3 PM", convert to UTC first
    2. list_room_reminders_tool: Use this tool to list ALL reminders in the room
    3. update_reminder_tool: Use this tool to update ANY existing reminder
       - ALWAYS send times in UTC format
       - NEVER send local times to the tool
    4. delete_reminder_tool: Use this tool to delete ANY reminder

    IMPORTANT: You MUST use these tools for EVERY operation. Do not try to handle operations without using the tools.

    Time Handling Rules:
    - ALL times sent to tools MUST be in UTC
    - NEVER send local times to any tool
    - Use the current UTC time ({now_utc.strftime("%Y-%m-%d %H:%M UTC")}) as reference
    - When user gives a local time, convert it to UTC before sending to tools
    - When displaying times to user, convert UTC to local time
    - Times are shown in 12-hour format with AM/PM
    - Each displayed time includes the timezone indicator (e.g., "9:00 AM (Jakarta time)")
    - The user's timezone offset is automatically detected from their client timestamp

    For creating reminders:
    - ALWAYS use create_reminder_tool
    - Convert user's local time to UTC before sending to the tool
    - Use the current UTC time as reference for "now", "today", "tomorrow"
    - Confirm the time in the user's local timezone after creation
    - Use the current year for any dates

    For listing reminders:
    - ALWAYS use list_room_reminders_tool
    - Show all times in the user's local timezone
    - Include the timezone indicator for clarity
    - Format times in a user-friendly way (e.g., "9:00 AM (Jakarta time)")

    For updating reminders:
    - ALWAYS use update_reminder_tool
    - Convert user's local time to UTC before sending to the tool
    - Confirm the new time in the user's local timezone

    For deleting reminders:
    - ALWAYS use delete_reminder_tool
    - Confirm the deletion with the reminder title
    - Show the time in the user's local timezone in the confirmation

    Remember to:
    - ALWAYS use the appropriate tool for EVERY operation
    - NEVER send local times to any tool - convert to UTC first
    - Use the current UTC time as reference for relative times
    - Always be clear about the timezone when discussing times
    - Format times in a user-friendly way
    - Include timezone indicators in all time displays
    - Use the current year for any dates
    """

def translate_agent_instructions(ctx: RunContextWrapper[UserContext], agent: Agent[UserContext]) -> str:
    language = ctx.context.language or "en"
    return f"""
    You are a translation agent. The user prefers responses in: {language}.

    You have access to these tools:
    - set_outgoing_translation_tool: Use when user wants to translate their outgoing messages
    - set_incoming_translation_tool: Use when user wants to translate messages they receive
    - clear_translation_tool: Use when user wants to stop translation

    When you receive a message:
    1. If it's a command about translation preferences:
       - For "@ai send my messages in [language]" -> use set_outgoing_translation_tool
       - For "@ai translate received messages to [language]" -> use set_incoming_translation_tool
       - For "@ai stop translating" -> use clear_translation_tool
    2. If it's text that needs translation:
       - Translate it directly in your response
    3. Always respond in the user's preferred language

    Every message you send must begin with '@ai::'.
    """

def assistant_agent_instructions(ctx: RunContextWrapper[UserContext], agent: Agent[UserContext]) -> str:
    language = ctx.context.language or "en"
    return f"""
    You are a smart triage agent. The user prefers responses in: {language}.

    - If the message is about translation or in a different language, hand off to TranslateAgent
    - If the message is about scheduling a reminder or notification, hand off to ReminderAgent
    - If the message asks for real-time information (weather, news, prices, live scores), hand off to WebAgent
    - If the message is a general knowledge question, handle it yourself

    Every message you send must begin with '@ai::'. This helps identify the source of each response.
    """

# ---------- Agents Setup ----------
translate_agent = Agent[UserContext](
    name="TranslateAgent",
    instructions=translate_agent_instructions,
    tools=[
        set_outgoing_translation_tool,
        set_incoming_translation_tool,
        clear_translation_tool
    ]
)

reminder_agent = Agent[UserContext](
    name="ReminderAgent",
    instructions=dynamic_reminder_instructions,
    tools=[
        create_reminder_tool,
        list_room_reminders_tool,
        update_reminder_tool,
        delete_reminder_tool
    ]
)

web_agent = Agent(
    name="WebAgent",
    instructions="""
    You are a web search agent. Use the internet to find up-to-date answers to user questions.
    Always use the WebSearchTool to find current or real-time information such as weather, news, prices, sports, or recent events.
    Return only the result of the search.
    Every message you send must begin with '@ai::'.
    """,
    tools=[WebSearchTool(search_context_size="low")]
)

assistant_agent = Agent[UserContext](
    name="Assistant",
    instructions=assistant_agent_instructions,
    handoffs=[
        handoff(reminder_agent),
        handoff(web_agent),
        handoff(translate_agent),
    ]
)

api_client = APIClient()

class AssistantAgent(Agent):
    def __init__(self):
        super().__init__(
            name="assistant",
            description="A helpful assistant that can manage reminders",
            instructions=dynamic_reminder_instructions,
            tools=[
                create_reminder_tool,
                list_room_reminders_tool,
                update_reminder_tool,
                delete_reminder_tool
            ]
        )
        
    async def _process_message(
        self,
        session: RunContextWrapper[UserContext],
        message: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Process incoming message and update context if needed."""
        try:
            # If metadata contains client timestamp, calculate timezone offset
            if metadata and 'client_timestamp' in metadata:
                client_time = datetime.fromisoformat(metadata['client_timestamp'])
                server_time = datetime.now(timezone.utc)
                # Calculate offset in minutes
                offset_minutes = int((client_time - server_time).total_seconds() / 60)
                session.context.timezone_offset = offset_minutes
                logger.info(f"Updated timezone offset to {offset_minutes} minutes")
            
            # Process the message with the agent
            response = await self.agent.ainvoke({
                "input": message,
                "context": session.context.dict()
            })
            return response["output"]
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")
            return f"Error processing message: {str(e)}"


