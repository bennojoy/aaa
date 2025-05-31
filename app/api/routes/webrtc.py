from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from app.core.security import decode_access_token
from app.middlewares.trace_id import get_trace_id
from app.core.logging import logger
import httpx
import os
from typing import Optional
import uuid

router = APIRouter(prefix="/webrtc", tags=["webrtc"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")

async def get_current_user_id(token: str = Depends(oauth2_scheme)) -> uuid.UUID:
    """Get current user ID from token"""
    payload = decode_access_token(token)
    if not payload or "client_attrs" not in payload or "sub" not in payload["client_attrs"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )
    return payload["client_attrs"]["sub"]

@router.post("/ephemeral-token")
async def get_ephemeral_token(user_id: uuid.UUID = Depends(get_current_user_id)):
    """
    Get an ephemeral token from OpenAI for WebRTC connection.
    
    Args:
        user_id (uuid.UUID): Current user's ID from token.
    
    Returns:
        dict: Ephemeral token and trace_id.
    
    Raises:
        HTTPException: If token generation fails.
    """
    trace_id = get_trace_id()
    logger.info(
        "Requesting ephemeral token from OpenAI",
        extra={
            "event": "ephemeral_token_request",
            "user_id": str(user_id),
            "trace_id": trace_id
        }
    )

    try:
        # Get OpenAI API key from environment
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not openai_api_key:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="OpenAI API key not configured"
            )

        # Request ephemeral token from OpenAI
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.openai.com/v1/realtime/sessions",
                headers={
                    "Authorization": f"Bearer {openai_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "gpt-4o-realtime-preview-2024-12-17",
                },
                timeout=30.0
            )

            if response.status_code != 200:
                logger.error(
                    "Failed to get ephemeral token from OpenAI",
                    extra={
                        "event": "ephemeral_token_failed",
                        "user_id": str(user_id),
                        "status_code": response.status_code,
                        "response": response.text,
                        "trace_id": trace_id
                    }
                )
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to get ephemeral token from OpenAI"
                )

            data = response.json()
            logger.info(
                "Successfully obtained ephemeral token",
                extra={
                    "event": "ephemeral_token_success",
                    "user_id": str(user_id),
                    "trace_id": trace_id
                }
            )

            return {
                "ephemeral_token": data.get("client_secret", {}).get("value"),
                "trace_id": trace_id
            }

    except Exception as e:
        logger.error(
            "Error getting ephemeral token",
            extra={
                "event": "ephemeral_token_error",
                "user_id": str(user_id),
                "error": str(e),
                "error_type": type(e).__name__,
                "trace_id": trace_id
            },
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get ephemeral token"
        ) 