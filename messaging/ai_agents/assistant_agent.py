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

# ---------- Reminder Tool ----------
class ReminderInput(BaseModel):
    date: str
    time: str
    message: str

@function_tool(name_override="reminder")
def reminder_tool(ctx: RunContextWrapper[Any], input: ReminderInput) -> str:
    try:
        datetime.strptime(input.date, "%Y-%m-%d")
        datetime.strptime(input.time, "%H:%M")
    except ValueError:
        return "Invalid date or time format. Please use YYYY-MM-DD and HH:MM."

    logger.info({
        "event": "tool_called",
        "tool": "reminder",
        "input": input.model_dump()
    })
    return f"⏰ Reminder set for {input.date} at {input.time}: {input.message}"

# ---------- Instructions ----------
def dynamic_reminder_instructions(ctx: RunContextWrapper[UserContext], agent: Agent[UserContext]) -> str:
    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    language = ctx.context.language or "en"
    return f"""
    You are a reminder agent. The current UTC date and time is: {now_utc}.
    The user prefers responses in this language: {language}.
    Always respond in that language.

    Every message you send must begin with '@aiReminderAgent::'. This helps identify who is speaking.

    Use the `reminder` tool to schedule reminders. Convert times like "tomorrow 8am" to absolute UTC.
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
       - For "send messages in [language]" -> use set_outgoing_translation_tool
       - For "translate received messages to [language]" -> use set_incoming_translation_tool
       - For "stop translating" -> use clear_translation_tool
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

# ---------- Translation Tools ----------
# Using imported tools directly from translation_tools.py

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
    tools=[reminder_tool]
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


