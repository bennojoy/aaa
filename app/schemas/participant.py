from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
import uuid
from app.models.participant import ParticipantRole, ParticipantStatus

class ParticipantBase(BaseModel):
    role: ParticipantRole = Field(default=ParticipantRole.MEMBER)
    status: ParticipantStatus = Field(default=ParticipantStatus.ACTIVE)

class ParticipantCreate(ParticipantBase):
    user_id: uuid.UUID

class ParticipantUpdate(ParticipantBase):
    role: Optional[ParticipantRole] = None
    status: Optional[ParticipantStatus] = None

class ParticipantResponse(ParticipantBase):
    id: uuid.UUID
    room_id: uuid.UUID
    user_id: uuid.UUID
    joined_at: datetime
    last_activity: datetime
    created_at: datetime
    updated_at: Optional[datetime]
    trace_id: Optional[str] = None

    class Config:
        from_attributes = True

class ParticipantList(BaseModel):
    participants: list[ParticipantResponse]
    trace_id: Optional[str] = None

class UserSearchResponse(BaseModel):
    id: uuid.UUID
    alias: Optional[str]
    phone_number: str  # Will be masked in the response
    trace_id: Optional[str] = None

    class Config:
        from_attributes = True

class UserSearchList(BaseModel):
    users: list[UserSearchResponse]
    trace_id: Optional[str] = None

class MessagePermissionResponse(BaseModel):
    can_send_message: bool
    participants: List[ParticipantResponse]
    trace_id: Optional[str] = None 