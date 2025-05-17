from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field

class ReminderBase(BaseModel):
    title: str
    description: Optional[str] = None
    start_time: datetime
    rrule: Optional[str] = None

class ReminderCreate(ReminderBase):
    room_id: UUID
    created_by_user_id: UUID

class ReminderUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    start_time: Optional[datetime] = None
    rrule: Optional[str] = None
    status: Optional[str] = None

class ReminderInDBBase(ReminderBase):
    id: UUID
    room_id: UUID
    created_by_user_id: UUID
    status: str
    created_at: datetime
    updated_at: datetime
    last_triggered_at: Optional[datetime] = None
    next_trigger_time: datetime

    class Config:
        from_attributes = True

class Reminder(ReminderInDBBase):
    pass

class ReminderInDB(ReminderInDBBase):
    pass 