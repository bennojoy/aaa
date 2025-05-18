from pydantic import BaseModel
from datetime import datetime
from typing import Optional, Dict, Any
from uuid import UUID

class Reminder(BaseModel):
    id: UUID
    room_id: UUID
    created_by_user_id: UUID
    title: str
    description: Optional[str] = None
    start_time: datetime
    next_trigger_time: datetime
    rrule: Optional[str] = None
    status: str
    created_at: datetime
    updated_at: datetime
    last_triggered_at: Optional[datetime] = None

class ReminderMessage(BaseModel):
    room_id: UUID
    sender_id: UUID  # Will be the created_by_user_id
    content: str     # Will be the reminder title/description
    trace_id: str
    timestamp: datetime
    payload: Dict[str, Any]  # Will contain reminder details

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v)
        }
