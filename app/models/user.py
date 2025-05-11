from sqlalchemy import Column, String, Boolean, Enum, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
import uuid
from app.db.base import Base
from app.core.logging import logger

class LoginStatus(str, Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    AWAY = "away"

class UserType(str, Enum):
    HUMAN = "human"
    BOT = "bot"
    SYSTEM = "system"

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    phone_number = Column(String, unique=True, index=True, nullable=False)
    alias = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    is_online = Column(Boolean, default=False)  # Track real-time presence
    login_status = Column(String, default=LoginStatus.OFFLINE)
    user_type = Column(String, default=UserType.HUMAN)  # Default to human
    language = Column(String, default="en")  # Default language
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now()) 