from pydantic import BaseModel

# ---------- User Context ----------
class UserContext(BaseModel):
    name: str | None = None
    language: str = "en"
    sender_id: str | None = None
    receiver_id: str | None = None
    room: str | None = None
    token: str | None = None