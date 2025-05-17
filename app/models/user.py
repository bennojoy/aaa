from sqlalchemy import Column, String, Boolean, Enum, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from app.db.base import Base
from app.core.logging import logger
from datetime import datetime

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

    # Relationships
    rooms = relationship("Room", back_populates="creator", foreign_keys="Room.created_by")
    participations = relationship("Participant", back_populates="user", cascade="all, delete-orphan")
    created_reminders = relationship("Reminder", back_populates="created_by", foreign_keys="Reminder.created_by_user_id", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(id={self.id}, phone={self.phone_number}, alias={self.alias})>" 