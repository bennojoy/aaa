from app.core.config import settings
from uuid import UUID
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.participant import Participant, ParticipantStatus
from app.models.user import User, UserType

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
            Participant.status == ParticipantStatus.ACTIVE
        )
    )
    result = await session.execute(stmt)
    participant = result.scalar_one_or_none()
    
    return participant is not None 

async def get_active_participants_service(
    room_id: UUID,
    session: AsyncSession
) -> list:
    participants_query = select(Participant).join(User).where(
        and_(
            Participant.room_id == room_id,
            Participant.status == ParticipantStatus.ACTIVE,
            User.user_type != UserType.BOT
        )
    ).distinct()
    result = await session.execute(participants_query)
    return result.scalars().all() 