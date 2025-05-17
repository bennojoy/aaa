from datetime import datetime
from uuid import UUID, uuid4
from sqlalchemy import Column, String, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import relationship

from app.db.base import Base

class Reminder(Base):
    __tablename__ = "reminders"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    room_id = Column(PGUUID(as_uuid=True), ForeignKey("rooms.id"), nullable=False)
    created_by_user_id = Column(PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=False)
    description = Column(String)
    start_time = Column(DateTime(timezone=True), nullable=False)
    rrule = Column(String)  # RRule string for recurrence
    status = Column(String, nullable=False, default="ACTIVE")  # ACTIVE, COMPLETED, CANCELLED
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_triggered_at = Column(DateTime(timezone=True))
    next_trigger_time = Column(DateTime(timezone=True), nullable=False)

    # Relationships
    room = relationship("Room", back_populates="reminders")
    created_by = relationship("User", foreign_keys=[created_by_user_id], back_populates="created_reminders")

    # Indexes
    __table_args__ = (
        # Index for querying room's reminders
        Index("ix_reminders_room_id", "room_id"),
        # Index for querying reminders by creator
        Index("ix_reminders_created_by", "created_by_user_id"),
        # Index for querying active reminders
        Index("ix_reminders_status", "status"),
        # Index for querying reminders by next trigger time
        Index("ix_reminders_next_trigger_time", "next_trigger_time"),
        # Composite index for efficient reminder processing
        Index("ix_reminders_status_next_trigger", "status", "next_trigger_time"),
    ) 