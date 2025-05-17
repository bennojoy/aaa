from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from pybreaker import CircuitBreaker
import httpx
from typing import Optional, Any, Dict
import logging
from functools import wraps

logger = logging.getLogger(__name__)

class APIClient:
    def __init__(self):
        # Circuit breaker configuration
        self.breaker = CircuitBreaker(
            fail_max=5,  # Number of failures before opening circuit
            reset_timeout=60,  # Time in seconds to wait before retrying
            exclude=[httpx.HTTPStatusError]  # Don't count 4xx errors as failures
        )
        
        # Base URL for API
        self.base_url = "http://localhost:8000/api"
        
    @retry(
        stop=stop_after_attempt(3),  # Try 3 times
        wait=wait_exponential(multiplier=1, min=4, max=10),  # Exponential backoff
        retry=retry_if_exception_type((httpx.NetworkError, httpx.TimeoutException)),
        reraise=True
    )
    async def make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Make HTTP request with retry and circuit breaker"""
        # Use the circuit breaker's call method
        return await self.breaker(self._make_request)(
            method=method,
            endpoint=endpoint,
            data=data,
            headers=headers
        )

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Internal method to make the actual HTTP request"""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.request(
                    method,
                    f"{self.base_url}{endpoint}",
                    json=data,
                    headers=headers,
                    timeout=5.0  # 5 second timeout
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP error: {e.response.status_code} - {e.response.text}")
                raise
            except httpx.RequestError as e:
                logger.error(f"Request error: {str(e)}")
                raise 