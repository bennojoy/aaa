from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
import uuid
from app.models.room import RoomType

class RoomBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    type: RoomType = Field(default=RoomType.USER)

class RoomCreate(RoomBase):
    pass

class RoomUpdate(RoomBase):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    assistant_name: Optional[str] = Field(None, min_length=1, max_length=100)
    type: Optional[RoomType] = None

class RoomResponse(RoomBase):
    id: uuid.UUID
    created_by: uuid.UUID
    is_default: bool
    assistant_name: str
    created_at: datetime
    updated_at: Optional[datetime]
    trace_id: Optional[str] = None

    class Config:
        from_attributes = True

class RoomList(BaseModel):
    rooms: list[RoomResponse]
    total: int
    trace_id: Optional[str] 