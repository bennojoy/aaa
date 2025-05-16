import asyncio
import logging
from agents import Runner, trace
from messaging.ai_agents.assistant_agent import assistant_agent
from messaging.ai_agents.agent_context import UserContext

logger = logging.getLogger("assistant_agent_runner")

async def run_assistant_agent(
    user_message: str,
    user_context: UserContext,
    trace_id: str,
    max_retries: int = 3,
    backoff_base: float = 1.0,
    circuit_breaker_threshold: int = 5,
) -> str:
    failures = 0
    # Format trace_id to match OpenAI's requirements
    formatted_trace_id = f"trace_{trace_id.replace('trace-', '')}"
    
    for attempt in range(max_retries):
        try:
            logger.info({
                "event": "runner_start",
                "attempt": attempt + 1,
                "trace_id": trace_id,
                "formatted_trace_id": formatted_trace_id,
                "workflow_name": user_context.sender_id,
                "group_id": user_context.room,
                "user_message": user_message
            })

            with trace(
                workflow_name=user_context.sender_id,
                group_id=user_context.room,
                trace_id=formatted_trace_id
            ):
                result = await Runner.run(
                    assistant_agent,
                    user_message,
                    context=user_context
                )

            logger.info({
                "event": "runner_success",
                "trace_id": trace_id,
                "formatted_trace_id": formatted_trace_id,
                "output": result.final_output
            })
            return result.final_output

        except Exception as e:
            failures += 1
            logger.error({
                "event": "runner_failure",
                "trace_id": trace_id,
                "attempt": attempt + 1,
                "error": str(e)
            })
            if failures >= circuit_breaker_threshold:
                logger.critical({
                    "event": "circuit_breaker_open",
                    "trace_id": trace_id,
                    "failures": failures
                })
                raise Exception("Circuit breaker open: too many failures") from e
            await asyncio.sleep(backoff_base * (2 ** attempt))

    logger.error({
        "event": "runner_exhausted",
        "trace_id": trace_id,
        "failures": failures
    })
    raise Exception("Assistant agent failed after retries") 