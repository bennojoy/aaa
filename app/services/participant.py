from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from app.repositories.participant import (
    add_participant,
    get_participant,
    get_room_participants,
    search_room_participants,
    search_users,
    update_participant,
    remove_participant,
    transfer_ownership,
    ParticipantRepositoryError,
    ParticipantAlreadyExistsError,
    ParticipantNotFoundError,
    DatabaseError
)
from app.repositories.room import get_room_by_id
from app.schemas.participant import (
    ParticipantCreate,
    ParticipantUpdate,
    ParticipantResponse,
    ParticipantList,
    UserSearchResponse,
    UserSearchList,
    MessagePermissionResponse
)
from app.core.logging import logger
from app.middlewares.trace_id import get_trace_id
from app.core.config import settings
from app.models.participant import Participant
from app.models.room import Room, RoomType
from app.models.user import User, UserType
import uuid

class ParticipantServiceError(Exception):
    """Base exception for participant service errors"""
    pass

class ParticipantAlreadyExistsServiceError(ParticipantServiceError):
    """Raised when attempting to add a user who is already a participant"""
    pass

class ParticipantNotFoundServiceError(ParticipantServiceError):
    """Raised when a participant is not found"""
    pass

class RoomLimitExceededError(ParticipantServiceError):
    """Raised when a room has reached its maximum number of participants"""
    pass

class UserRoomLimitExceededError(ParticipantServiceError):
    """Raised when a user has reached their maximum number of rooms"""
    pass

class DatabaseServiceError(ParticipantServiceError):
    """Raised when there's a database error"""
    pass

class PermissionServiceError(ParticipantServiceError):
    """Raised when user doesn't have required permissions"""
    pass

async def add_participant_service(
    db: AsyncSession,
    room_id: uuid.UUID,
    participant_in: ParticipantCreate,
    current_user_id: uuid.UUID
) -> ParticipantResponse:
    """Add a new participant to a room"""
    trace_id = get_trace_id()
    logger.info(
        "Adding participant in service",
        extra={
            "event": "participant_add_service",
            "room_id": str(room_id),
            "user_id": str(participant_in.user_id),
            "current_user_id": str(current_user_id),
            "trace_id": trace_id
        }
    )
    try:
        # Check if current user is room owner
        room = await get_room_by_id(db, room_id)
        if room.created_by != current_user_id:
            raise PermissionServiceError("Only room owner can add participants")

        # Check room participant limit
        current_participants = await get_room_participants(db, room_id)
        if len(current_participants) >= settings.MAX_USERS_PER_ROOM:
            raise RoomLimitExceededError(f"Room has reached maximum limit of {settings.MAX_USERS_PER_ROOM} participants")

        # Check user's room limit
        user_rooms = await search_room_participants(db, None, str(participant_in.user_id))
        if len(user_rooms) >= settings.MAX_ROOMS_PER_USER:
            raise UserRoomLimitExceededError(f"User has reached maximum limit of {settings.MAX_ROOMS_PER_USER} rooms")

        participant = await add_participant(db, room_id, participant_in)
        response = ParticipantResponse.model_validate(participant, from_attributes=True)
        response.trace_id = trace_id
        return response
    except ParticipantAlreadyExistsError as e:
        logger.error(
            "Failed to add participant: already exists",
            extra={
                "event": "participant_add_failed_service",
                "reason": "already_exists",
                "room_id": str(room_id),
                "user_id": str(participant_in.user_id),
                "trace_id": trace_id
            }
        )
        raise ParticipantAlreadyExistsServiceError(str(e))
    except RoomLimitExceededError as e:
        logger.error(
            "Failed to add participant: room limit exceeded",
            extra={
                "event": "participant_add_failed_service",
                "reason": "room_limit_exceeded",
                "room_id": str(room_id),
                "user_id": str(participant_in.user_id),
                "trace_id": trace_id
            }
        )
        raise
    except UserRoomLimitExceededError as e:
        logger.error(
            "Failed to add participant: user room limit exceeded",
            extra={
                "event": "participant_add_failed_service",
                "reason": "user_room_limit_exceeded",
                "room_id": str(room_id),
                "user_id": str(participant_in.user_id),
                "trace_id": trace_id
            }
        )
        raise
    except DatabaseError as e:
        logger.error(
            "Database error in participant add",
            extra={
                "event": "participant_add_failed_service",
                "reason": "database_error",
                "room_id": str(room_id),
                "user_id": str(participant_in.user_id),
                "error": str(e),
                "trace_id": trace_id
            }
        )
        raise DatabaseServiceError(str(e))

async def get_room_participants_service(
    db: AsyncSession,
    room_id: uuid.UUID
) -> ParticipantList:
    """Get all participants in a room"""
    trace_id = get_trace_id()
    logger.info(
        "Getting room participants in service",
        extra={
            "event": "room_participants_get_service",
            "room_id": str(room_id),
            "trace_id": trace_id
        }
    )
    try:
        participants = await get_room_participants(db, room_id)
        response = ParticipantList(
            participants=[
                ParticipantResponse.model_validate(p, from_attributes=True)
                for p in participants
            ],
            trace_id=trace_id
        )
        return response
    except DatabaseError as e:
        logger.error(
            "Database error in room participants get",
            extra={
                "event": "room_participants_get_failed_service",
                "reason": "database_error",
                "room_id": str(room_id),
                "error": str(e),
                "trace_id": trace_id
            }
        )
        raise DatabaseServiceError(str(e))

async def search_room_participants_service(
    db: AsyncSession,
    room_id: uuid.UUID,
    query: str
) -> ParticipantList:
    """Search participants in a room"""
    trace_id = get_trace_id()
    logger.info(
        "Searching room participants in service",
        extra={
            "event": "room_participants_search_service",
            "room_id": str(room_id),
            "query": query,
            "trace_id": trace_id
        }
    )
    try:
        participants = await search_room_participants(db, room_id, query)
        response = ParticipantList(
            participants=[
                ParticipantResponse.model_validate(p, from_attributes=True)
                for p in participants
            ],
            trace_id=trace_id
        )
        return response
    except DatabaseError as e:
        logger.error(
            "Database error in room participants search",
            extra={
                "event": "room_participants_search_failed_service",
                "reason": "database_error",
                "room_id": str(room_id),
                "query": query,
                "error": str(e),
                "trace_id": trace_id
            }
        )
        raise DatabaseServiceError(str(e))

async def search_users_service(
    db: AsyncSession,
    query: str,
    exclude_room_id: uuid.UUID = None
) -> UserSearchList:
    """Search users globally"""
    trace_id = get_trace_id()
    logger.info(
        "Searching users in service",
        extra={
            "event": "users_search_service",
            "query": query,
            "exclude_room_id": str(exclude_room_id) if exclude_room_id else None,
            "trace_id": trace_id
        }
    )
    try:
        users = await search_users(db, query, exclude_room_id)
        response = UserSearchList(
            users=[
                UserSearchResponse.model_validate(u, from_attributes=True)
                for u in users
            ],
            trace_id=trace_id
        )
        return response
    except DatabaseError as e:
        logger.error(
            "Database error in users search",
            extra={
                "event": "users_search_failed_service",
                "reason": "database_error",
                "query": query,
                "error": str(e),
                "trace_id": trace_id
            }
        )
        raise DatabaseServiceError(str(e))

async def update_participant_service(
    db: AsyncSession,
    room_id: uuid.UUID,
    user_id: uuid.UUID,
    participant_in: ParticipantUpdate,
    current_user_id: uuid.UUID
) -> ParticipantResponse:
    """Update participant details"""
    trace_id = get_trace_id()
    logger.info(
        "Updating participant in service",
        extra={
            "event": "participant_update_service",
            "room_id": str(room_id),
            "user_id": str(user_id),
            "current_user_id": str(current_user_id),
            "trace_id": trace_id
        }
    )
    try:
        # Check if current user is room owner
        room = await get_room_by_id(db, room_id)
        if room.created_by != current_user_id:
            raise PermissionServiceError("Only room owner can update participants")

        participant = await update_participant(db, room_id, user_id, participant_in)
        response = ParticipantResponse.model_validate(participant, from_attributes=True)
        response.trace_id = trace_id
        return response
    except ParticipantNotFoundError as e:
        logger.error(
            "Participant not found for update",
            extra={
                "event": "participant_update_failed_service",
                "reason": "not_found",
                "room_id": str(room_id),
                "user_id": str(user_id),
                "trace_id": trace_id
            }
        )
        raise ParticipantNotFoundServiceError(str(e))
    except DatabaseError as e:
        logger.error(
            "Database error in participant update",
            extra={
                "event": "participant_update_failed_service",
                "reason": "database_error",
                "room_id": str(room_id),
                "user_id": str(user_id),
                "error": str(e),
                "trace_id": trace_id
            }
        )
        raise DatabaseServiceError(str(e))

async def remove_participant_service(
    db: AsyncSession,
    room_id: uuid.UUID,
    user_id: uuid.UUID,
    current_user_id: uuid.UUID
) -> None:
    """Remove a participant from a room"""
    trace_id = get_trace_id()
    logger.info(
        "Removing participant in service",
        extra={
            "event": "participant_remove_service",
            "room_id": str(room_id),
            "user_id": str(user_id),
            "current_user_id": str(current_user_id),
            "trace_id": trace_id
        }
    )
    try:
        # Check if current user is room owner
        room = await get_room_by_id(db, room_id)
        if room.created_by != current_user_id:
            raise PermissionServiceError("Only room owner can remove participants")

        await remove_participant(db, room_id, user_id)
    except ParticipantNotFoundError as e:
        logger.error(
            "Participant not found for removal",
            extra={
                "event": "participant_remove_failed_service",
                "reason": "not_found",
                "room_id": str(room_id),
                "user_id": str(user_id),
                "trace_id": trace_id
            }
        )
        raise ParticipantNotFoundServiceError(str(e))
    except DatabaseError as e:
        logger.error(
            "Database error in participant removal",
            extra={
                "event": "participant_remove_failed_service",
                "reason": "database_error",
                "room_id": str(room_id),
                "user_id": str(user_id),
                "error": str(e),
                "trace_id": trace_id
            }
        )
        raise DatabaseServiceError(str(e))

async def transfer_ownership_service(
    db: AsyncSession,
    room_id: uuid.UUID,
    new_owner_id: uuid.UUID,
    current_user_id: uuid.UUID
) -> ParticipantResponse:
    """Transfer room ownership to another participant"""
    trace_id = get_trace_id()
    logger.info(
        "Transferring ownership in service",
        extra={
            "event": "ownership_transfer_service",
            "room_id": str(room_id),
            "new_owner_id": str(new_owner_id),
            "current_user_id": str(current_user_id),
            "trace_id": trace_id
        }
    )
    try:
        # Check if current user is room owner
        room = await get_room_by_id(db, room_id)
        if room.created_by != current_user_id:
            raise PermissionServiceError("Only room owner can transfer ownership")

        new_owner = await transfer_ownership(db, room_id, current_user_id, new_owner_id)
        response = ParticipantResponse.model_validate(new_owner, from_attributes=True)
        response.trace_id = trace_id
        return response
    except ParticipantNotFoundError as e:
        logger.error(
            "Participant not found for ownership transfer",
            extra={
                "event": "ownership_transfer_failed_service",
                "reason": "not_found",
                "room_id": str(room_id),
                "new_owner_id": str(new_owner_id),
                "trace_id": trace_id
            }
        )
        raise ParticipantNotFoundServiceError(str(e))
    except DatabaseError as e:
        logger.error(
            "Database error in ownership transfer",
            extra={
                "event": "ownership_transfer_failed_service",
                "reason": "database_error",
                "room_id": str(room_id),
                "new_owner_id": str(new_owner_id),
                "error": str(e),
                "trace_id": trace_id
            }
        )
        raise DatabaseServiceError(str(e))

async def check_message_permission_service(
    db: AsyncSession,
    user_id: uuid.UUID,
    room_id: uuid.UUID
) -> MessagePermissionResponse:
    """
    Check if a user can send messages in a room and get all non-assistant participants.
    
    Args:
        db (AsyncSession): Database session
        user_id (UUID): ID of the user to check
        room_id (UUID): ID of the room to check
        
    Returns:
        MessagePermissionResponse: Permission status and list of participants
    """
    trace_id = get_trace_id()
    logger.info(
        "Checking message permission",
        extra={
            "event": "message_permission_check",
            "user_id": str(user_id),
            "room_id": str(room_id),
            "trace_id": trace_id
        }
    )
    
    try:
        # Check if user is a participant in the room
        participant_query = select(Participant).where(
            and_(
                Participant.user_id == user_id,
                Participant.room_id == room_id,
                Participant.status == "active"
            )
        )
        result = await db.execute(participant_query)
        participant = result.scalar_one_or_none()
        
        can_send_message = participant is not None
        
        # Get all non-assistant participants
        participants_query = select(Participant).join(User).where(
            and_(
                Participant.room_id == room_id,
                Participant.status == "active",
                User.user_type != UserType.BOT
            )
        ).distinct()
        result = await db.execute(participants_query)
        participants = result.scalars().all()
        
        logger.info(
            "Message permission check completed",
            extra={
                "event": "message_permission_check_complete",
                "user_id": str(user_id),
                "room_id": str(room_id),
                "can_send_message": can_send_message,
                "participant_count": len(participants),
                "trace_id": trace_id
            }
        )
        
        return MessagePermissionResponse(
            can_send_message=can_send_message,
            participants=participants,
            trace_id=trace_id
        )
        
    except Exception as e:
        logger.error(
            "Error checking message permission",
            extra={
                "event": "message_permission_check_failed",
                "reason": "unexpected_error",
                "user_id": str(user_id),
                "room_id": str(room_id),
                "error": str(e),
                "trace_id": trace_id
            }
        )
        raise 