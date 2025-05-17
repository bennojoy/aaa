from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, UniqueConstraint, Enum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid
from app.db.session import Base
from datetime import datetime
import enum

class RoomType(str, enum.Enum):
    ASSISTANT = "assistant"
    USER = "user"

class Room(Base):
    __tablename__ = "rooms"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    description = Column(String)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    is_default = Column(Boolean, default=False)
    assistant_name = Column(String, default="Assistant")
    type = Column(Enum(RoomType), nullable=False, default=RoomType.USER)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Ensure room names are unique per user
    __table_args__ = (
        UniqueConstraint('created_by', 'name', name='uix_room_name_per_user'),
    )

    # Relationships
    creator = relationship("User", foreign_keys=[created_by])
    participants = relationship("Participant", back_populates="room", cascade="all, delete-orphan")
    reminders = relationship("Reminder", back_populates="room", cascade="all, delete-orphan")
    # messages = relationship("Message", back_populates="room", cascade="all, delete-orphan", lazy="dynamic") 

    def __repr__(self):
        return f"<Room(id={self.id}, name={self.name}, created_by={self.created_by}, type={self.type})>" 