from typing import Optional
from pydantic import BaseModel

# ---------- User Context ----------
class UserContext(BaseModel):
    name: str | None = None
    language: Optional[str] = "en"
    sender_id: Optional[str] = None
    receiver_id: str | None = None
    room: Optional[str] = None
    token: Optional[str] = None
    timezone_offset: Optional[int] = None  # Timezone offset in minutes from UTC