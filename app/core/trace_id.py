import uuid
from contextvars import ContextVar
from typing import Optional

# Context variable to store the trace ID
trace_id_context: ContextVar[Optional[str]] = ContextVar("trace_id", default=None)

def get_trace_id() -> str:
    """
    Get the current trace ID or generate a new one if none exists
    """
    trace_id = trace_id_context.get()
    if trace_id is None:
        trace_id = str(uuid.uuid4())
        trace_id_context.set(trace_id)
    return trace_id

def set_trace_id(trace_id: str) -> None:
    """
    Set the trace ID in the current context
    """
    trace_id_context.set(trace_id) 