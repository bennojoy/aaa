from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta, UTC
from typing import Optional
from app.core.config import settings
import uuid
import time

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = {
        "exp": int(time.time() + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)).total_seconds()),
        "iss": "bee",
        "sub": str(data["sub"]),
        "client_attrs": {
            "role": "admin",
            "sub": str(data["sub"]),  # user ID
            "sn": "system"  # system identifier
        },
        "acl": [
            {
                "permission": "allow",
                "action": "subscribe",
                "topic": f"user/{data['sub']}/message"
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
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        # Convert string UUID back to UUID object if present
        if "client_attrs" in payload and "sub" in payload["client_attrs"]:
            payload["client_attrs"]["sub"] = uuid.UUID(payload["client_attrs"]["sub"])
        return payload
    except JWTError:
        return None 