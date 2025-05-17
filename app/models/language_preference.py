from sqlalchemy import Column, String, DateTime, func
from app.db.session import Base

class RoomUserLanguagePreference(Base):
    __tablename__ = "room_user_preferences"

    user_id = Column(String(255), primary_key=True)
    room_id = Column(String(255), primary_key=True)
    outgoing_language = Column(String(10), nullable=True)
    incoming_language = Column(String(10), nullable=True)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now()) 