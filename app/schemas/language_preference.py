from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

class LanguagePreferenceUpdate(BaseModel):
    outgoing_language: Optional[str] = None
    incoming_language: Optional[str] = None

class LanguagePreferenceResponse(BaseModel):
    user_id: str
    room_id: str
    outgoing_language: Optional[str] = None
    incoming_language: Optional[str] = None
    updated_at: datetime

class LanguagePreferenceResetResponse(BaseModel):
    message: str 