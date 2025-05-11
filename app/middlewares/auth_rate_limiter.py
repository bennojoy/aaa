from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from datetime import datetime
import time
import logging
from app.middlewares.trace_id import get_trace_id
from app.core.config import settings

logger = logging.getLogger(__name__)

class AuthRateLimiter(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self.request_store = {}  # IP -> list of timestamps
        self.blacklist = {}  # IP -> unblock timestamp
        self.requests_per_minute = settings.RATE_LIMIT_PER_MINUTE
        self.requests_per_ten_minutes = settings.RATE_LIMIT_PER_HOUR // 6
        self.blacklist_duration = 3600  # 1 hour in seconds

    async def dispatch(self, request: Request, call_next):
        # Only apply to auth endpoints
        if not request.url.path.startswith("/api/v1/auth"):
            return await call_next(request)

        # Get client IP, handling test client
        client_ip = request.client.host if request.client else "testclient"
        current_time = time.time()

        # Initialize request store for new IPs
        if client_ip not in self.request_store:
            self.request_store[client_ip] = []

        # Check if IP is blacklisted
        if client_ip in self.blacklist:
            if current_time < self.blacklist[client_ip]:
                logger.warning(
                    f"Blacklisted IP attempted access: client_ip={client_ip}, unblock_time={datetime.fromtimestamp(self.blacklist[client_ip])}"
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "message": "IP address has been temporarily blocked due to suspicious activity",
                        "trace_id": get_trace_id()
                    }
                )
            else:
                # Remove from blacklist if block duration has passed
                del self.blacklist[client_ip]

        # Clean old entries
        self._clean_old_entries(client_ip, current_time)

        # Add current request timestamp
        self.request_store[client_ip].append(current_time)

        # Check rate limits
        if not self._check_rate_limits(client_ip, current_time):
            # Add to blacklist
            self.blacklist[client_ip] = current_time + self.blacklist_duration
            logger.warning(
                f"IP blacklisted due to rate limit violation: client_ip={client_ip}, unblock_time={datetime.fromtimestamp(self.blacklist[client_ip])}"
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "message": "Too many authentication attempts. IP has been temporarily blocked.",
                    "trace_id": get_trace_id()
                }
            )

        return await call_next(request)

    def _clean_old_entries(self, client_ip: str, current_time: float):
        """Remove entries older than 10 minutes"""
        if client_ip not in self.request_store:
            return

        # Keep only entries from the last 10 minutes
        cutoff_time = current_time - 600  # 10 minutes in seconds
        self.request_store[client_ip] = [
            ts for ts in self.request_store[client_ip] if ts > cutoff_time
        ]

    def _check_rate_limits(self, client_ip: str, current_time: float) -> bool:
        """Check if the IP has exceeded rate limits"""
        if client_ip not in self.request_store:
            return True

        # Check per-minute limit
        minute_ago = current_time - 60
        recent_requests = [ts for ts in self.request_store[client_ip] if ts > minute_ago]
        if len(recent_requests) > self.requests_per_minute:
            return False

        # Check per-10-minute limit
        ten_minutes_ago = current_time - 600
        ten_minute_requests = [ts for ts in self.request_store[client_ip] if ts > ten_minutes_ago]
        if len(ten_minute_requests) > self.requests_per_ten_minutes:
            return False

        return True 