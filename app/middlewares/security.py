from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
import time
import structlog
from app.core.config import settings

logger = structlog.get_logger()

class SecurityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: callable) -> Response:
        # Check request size
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > settings.MAX_REQUEST_SIZE:
            logger.warning(
                "Request too large",
                client_ip=request.client.host,
                content_length=content_length,
                max_size=settings.MAX_REQUEST_SIZE
            )
            raise HTTPException(status_code=413, detail="Request too large")

        # Check allowed hosts
        if settings.ALLOWED_HOSTS != ["*"]:
            host = request.headers.get("host", "").split(":")[0]
            if host not in settings.ALLOWED_HOSTS:
                logger.warning(
                    "Invalid host",
                    client_ip=request.client.host,
                    host=host
                )
                raise HTTPException(status_code=400, detail="Invalid host")

        # Add security headers
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time

        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        response.headers["X-Process-Time"] = str(process_time)

        # Check request timeout
        if process_time > settings.REQUEST_TIMEOUT:
            logger.warning(
                "Request timeout",
                client_ip=request.client.host,
                path=request.url.path,
                process_time=process_time
            )
            raise HTTPException(status_code=504, detail="Request timeout")

        return response 