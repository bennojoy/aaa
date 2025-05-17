import logging
import json
from datetime import datetime, timezone
from typing import Any

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
    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    language = ctx.context.language or "en"
    return f"""
    You are a reminder agent. The current UTC date and time is: {now_utc}.
    The user prefers responses in this language: {language}.
    Always respond in that language.

    Every message you send must begin with '@aiReminderAgent::'. This helps identify who is speaking.

    You have access to these tools:
    - create_reminder_tool: Create a new reminder with title, optional description, start time, and recurrence rule
    - list_room_reminders_tool: List all reminders in the current room
    - update_reminder_tool: Update an existing reminder's properties
    - delete_reminder_tool: Delete a reminder by ID

    When handling reminder requests:
    1. For creating reminders:
       - Convert relative times (e.g., "tomorrow 8am") to absolute UTC times
       - Use ISO format for dates (YYYY-MM-DDTHH:MM:SS+00:00)
       - For recurring reminders, use RRule format (e.g., "FREQ=DAILY;COUNT=3")
    2. For listing reminders:
       - Show all active reminders in the room
    3. For updating reminders:
       - Only update the fields that need to change
    4. For deleting reminders:
       - Confirm the deletion with the reminder title

    Always provide clear feedback about the action taken.
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


