import logging
import httpx
from ..config import SYSTEM_PHONE, SYSTEM_PASSWORD, SYSTEM_JWT_SECRET, SYSTEM_USER_UUID
import jwt
from datetime import datetime, timedelta

async def signup_system_user():
    """Try to sign up the system user. Ignore error if user already exists."""
    url = "http://localhost:8000/api/v1/auth/signup"
    data = {
        "phone_number": SYSTEM_PHONE,
        "password": SYSTEM_PASSWORD,
        "alias": "system_user",
        "user_type": "human",
        "language": "en"
    }
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, json=data)
            if response.status_code == 200:
                logging.info("System user signed up successfully.")
            elif response.status_code == 400 and ("already exists" in response.text or "exists" in response.text):
                logging.info("System user already exists, continuing.")
            else:
                logging.warning(f"System user signup response: {response.text}")
        except Exception as e:
            logging.error(f"System user signup error: {e}")

async def get_system_token() -> str:
    """Get a system JWT token with 1 year expiry"""
    # Set expiry to 1 year from now
    expiry = datetime.utcnow() + timedelta(days=365)
    
    # Create JWT payload
    payload = {
        "exp": expiry,
        "iss": "bee",
        "sub": SYSTEM_USER_UUID,
        "client_attrs": {
            "role": "admin",
            "sub": SYSTEM_USER_UUID,
            "sn": "system"
        },
        "acl": [
            {
                "permission": "allow",
                "action": "subscribe",
                "topic": f"user/{SYSTEM_USER_UUID}/message"
            },
            {
                "permission": "allow",
                "action": "publish",
                "topic": "messages/to_room"
            },
            {
                "permission": "deny",
                "action": "all",
                "topic": "#"
            }
        ]
    }
    
    # Generate JWT token
    token = jwt.encode(payload, SYSTEM_JWT_SECRET, algorithm="HS256")
    return token 