import uuid
from contextvars import ContextVar
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import json

# Context variable to store trace_id
trace_id_ctx: ContextVar[str] = ContextVar("trace_id", default="")

class TraceIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Get trace_id from header or generate new one
        trace_id = request.headers.get("X-Trace-ID", str(uuid.uuid4()))
        
        # Set trace_id in request state and context
        request.state.trace_id = trace_id
        trace_id_ctx.set(trace_id)
        
        # Get the response
        response = await call_next(request)
        
        # Add trace_id to response headers
        response.headers["X-Trace-ID"] = trace_id
        
        # If it's a JSONResponse, add trace_id to the body
        if isinstance(response, JSONResponse):
            try:
                body = json.loads(response.body.decode())
                if isinstance(body, dict):
                    body["trace_id"] = trace_id
                    response.body = json.dumps(body).encode()
            except (json.JSONDecodeError, UnicodeDecodeError):
                pass
        
        return response

def get_trace_id() -> str:
    """Get the current trace ID from context."""
    return trace_id_ctx.get() 