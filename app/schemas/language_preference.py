from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

class LanguagePreferenceUpdate(BaseModel):
    outgoing_language: str = Field(..., min_length=2, max_length=10)
    incoming_language: str = Field(..., min_length=2, max_length=10)

class LanguagePreferenceResponse(BaseModel):
    user_id: str
    room_id: str
    outgoing_language: str
    incoming_language: str
    updated_at: datetime

class LanguagePreferenceResetResponse(BaseModel):
    message: str 