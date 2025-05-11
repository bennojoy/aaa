from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum
from app.db.session import Base

class ParticipantType(enum.Enum):
    USER = "user"
    AI_ASSISTANT = "ai_assistant"

class Participant(Base):
    __tablename__ = "participants"

    id = Column(Integer, primary_key=True, index=True)
    room_id = Column(Integer, ForeignKey("rooms.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # Nullable for AI assistants
    participant_type = Column(Enum(ParticipantType), nullable=False)
    alias = Column(String, nullable=False)  # For AI assistants, this is their name
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    room = relationship("Room", back_populates="participants")
    user = relationship("User")
    # messages = relationship("Message", back_populates="sender", cascade="all, delete-orphan") 