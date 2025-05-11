from fastapi import Request, HTTPException, status
from datetime import datetime, timedelta
from collections import defaultdict
import time
from app.core.config import settings
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response, JSONResponse

logger = logging.getLogger(__name__)

# In-memory storage for rate limiting
# In production, use Redis or similar
rate_limit_store = defaultdict(list)

class RateLimiter(BaseHTTPMiddleware):
    def __init__(
        self,
        app,
        requests_per_minute: int = 60,
        requests_per_hour: int = 1000,
        requests_per_day: int = 10000
    ):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        self.requests_per_day = requests_per_day

    async def dispatch(self, request: Request, call_next) -> Response:
        # Prefer X-Forwarded-For for client IP (for proxies/testing), fallback to request.client.host
        x_forwarded_for = request.headers.get("x-forwarded-for")
        if x_forwarded_for:
            client_ip = x_forwarded_for.split(",")[0].strip()
        else:
            client_ip = request.client.host if request.client else "testclient"
        current_time = time.time()
        
        # Clean old entries
        self._clean_old_entries(client_ip, current_time)
        
        # Check rate limits
        if not self._check_rate_limits(client_ip, current_time):
            logger.warning(f"Rate limit exceeded for IP: {client_ip}")
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={"detail": "Too many requests. Please try again later."}
            )
        
        # Add current request
        rate_limit_store[client_ip].append(current_time)
        
        # Process the request
        return await call_next(request)

    def _clean_old_entries(self, client_ip: str, current_time: float):
        """Remove entries older than 24 hours"""
        day_ago = current_time - 86400  # 24 hours in seconds
        rate_limit_store[client_ip] = [
            t for t in rate_limit_store[client_ip] if t > day_ago
        ]

    def _check_rate_limits(self, client_ip: str, current_time: float) -> bool:
        """Check if the request is within rate limits"""
        requests = rate_limit_store[client_ip]
        
        # Check per-minute limit
        minute_ago = current_time - 60
        minute_requests = len([t for t in requests if t > minute_ago])
        if minute_requests >= self.requests_per_minute:
            return False
        
        # Check per-hour limit
        hour_ago = current_time - 3600
        hour_requests = len([t for t in requests if t > hour_ago])
        if hour_requests >= self.requests_per_hour:
            return False
        
        # Check per-day limit
        day_ago = current_time - 86400
        day_requests = len([t for t in requests if t > day_ago])
        if day_requests >= self.requests_per_day:
            return False
        
        return True

# Remove or comment out the following lines:
# rate_limiter = RateLimiter(
#     requests_per_minute=settings.RATE_LIMIT_PER_MINUTE,
#     requests_per_hour=settings.RATE_LIMIT_PER_HOUR,
#     requests_per_day=settings.RATE_LIMIT_PER_DAY
# ) 