from app.core.config import settings
from uuid import UUID
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.participant import Participant

async def check_message_permission_service(
    user_id: UUID,
    room_id: UUID,
    session: AsyncSession
) -> bool:
    # System user always has permission
    if str(user_id) == settings.SYSTEM_USER_UUID:
        return True
        
    # Check if user is an active participant in the room
    stmt = select(Participant).where(
        and_(
            Participant.user_id == user_id,
            Participant.room_id == room_id,
            Participant.status == "ACTIVE"
        )
    )
    result = await session.execute(stmt)
    participant = result.scalar_one_or_none()
    
    return participant is not None 