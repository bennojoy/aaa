from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.room import (
    create_room,
    get_room_by_id,
    get_user_rooms,
    search_rooms,
    update_room,
    delete_room,
    RoomRepositoryError,
    RoomAlreadyExistsError,
    RoomNotFoundError,
    DatabaseError
)
from app.schemas.room import RoomCreate, RoomUpdate, RoomResponse, RoomList
from app.core.logging import logger
from app.middlewares.trace_id import get_trace_id
import uuid
from app.repositories.participant import add_participant
from app.schemas.participant import ParticipantCreate

class RoomServiceError(Exception):
    """Base exception for room service errors"""
    pass

class RoomAlreadyExistsServiceError(RoomServiceError):
    """Raised when attempting to create a room that already exists"""
    pass

class RoomNotFoundServiceError(RoomServiceError):
    """Raised when a room is not found"""
    pass

class DatabaseServiceError(RoomServiceError):
    """Raised when there's a database error"""
    pass

async def create_room_service(db: AsyncSession, room_in: RoomCreate, user_id: uuid.UUID) -> RoomResponse:
    """Create a new room"""
    trace_id = get_trace_id()
    logger.info(
        "Creating room in service",
        extra={
            "event": "room_creation_service",
            "user_id": str(user_id),
            "room_name": room_in.name,
            "trace_id": trace_id
        }
    )
    try:
        # Create the room
        room = await create_room(db, room_in, user_id)
        
        # Add creator as participant with owner role
        participant_data = ParticipantCreate(
            user_id=user_id,
            role="owner",
            status="active"
        )
        await add_participant(db, room.id, participant_data)
        
        response = RoomResponse.model_validate(room, from_attributes=True)
        response.trace_id = trace_id
        return response
    except RoomAlreadyExistsError as e:
        logger.error(
            "Room creation failed: name exists",
            extra={
                "event": "room_creation_failed_service",
                "reason": "name_exists",
                "user_id": str(user_id),
                "room_name": room_in.name,
                "trace_id": trace_id
            }
        )
        raise RoomAlreadyExistsServiceError(str(e))
    except DatabaseError as e:
        logger.error(
            "Database error in room creation",
            extra={
                "event": "room_creation_failed_service",
                "reason": "database_error",
                "user_id": str(user_id),
                "room_name": room_in.name,
                "error": str(e),
                "trace_id": trace_id
            }
        )
        raise DatabaseServiceError(str(e))

async def get_room_service(db: AsyncSession, room_id: uuid.UUID) -> RoomResponse:
    """Get room by ID"""
    trace_id = get_trace_id()
    logger.info(
        "Getting room in service",
        extra={
            "event": "room_get_service",
            "room_id": str(room_id),
            "trace_id": trace_id
        }
    )
    try:
        room = await get_room_by_id(db, room_id)
        response = RoomResponse.model_validate(room, from_attributes=True)
        response.trace_id = trace_id
        return response
    except RoomNotFoundError as e:
        logger.error(
            "Room not found",
            extra={
                "event": "room_get_failed_service",
                "reason": "not_found",
                "room_id": str(room_id),
                "trace_id": trace_id
            }
        )
        raise RoomNotFoundServiceError(str(e))
    except DatabaseError as e:
        logger.error(
            "Database error in room get",
            extra={
                "event": "room_get_failed_service",
                "reason": "database_error",
                "room_id": str(room_id),
                "error": str(e),
                "trace_id": trace_id
            }
        )
        raise DatabaseServiceError(str(e))

async def get_user_rooms_service(
    db: AsyncSession,
    user_id: uuid.UUID,
    skip: int = 0,
    limit: int = 100
) -> RoomList:
    """Get all rooms for a user"""
    trace_id = get_trace_id()
    logger.info(
        "Getting user rooms in service",
        extra={
            "event": "user_rooms_get_service",
            "user_id": str(user_id),
            "trace_id": trace_id
        }
    )
    try:
        rooms, total = await get_user_rooms(db, user_id, skip, limit)
        response = RoomList(
            rooms=[RoomResponse.model_validate(room, from_attributes=True) for room in rooms],
            total=total,
            trace_id=trace_id
        )
        return response
    except DatabaseError as e:
        logger.error(
            "Database error in user rooms get",
            extra={
                "event": "user_rooms_get_failed_service",
                "reason": "database_error",
                "user_id": str(user_id),
                "error": str(e),
                "trace_id": trace_id
            }
        )
        raise DatabaseServiceError(str(e))

async def search_rooms_service(
    db: AsyncSession,
    user_id: uuid.UUID,
    query: str,
    skip: int = 0,
    limit: int = 100
) -> RoomList:
    """Search rooms by name"""
    trace_id = get_trace_id()
    logger.info(
        "Searching rooms in service",
        extra={
            "event": "room_search_service",
            "user_id": str(user_id),
            "query": query,
            "trace_id": trace_id
        }
    )
    try:
        rooms, total = await search_rooms(db, user_id, query, skip, limit)
        response = RoomList(
            rooms=[RoomResponse.model_validate(room, from_attributes=True) for room in rooms],
            total=total,
            trace_id=trace_id
        )
        return response
    except DatabaseError as e:
        logger.error(
            "Database error in room search",
            extra={
                "event": "room_search_failed_service",
                "reason": "database_error",
                "user_id": str(user_id),
                "query": query,
                "error": str(e),
                "trace_id": trace_id
            }
        )
        raise DatabaseServiceError(str(e))

async def update_room_service(
    db: AsyncSession,
    room_id: uuid.UUID,
    room_in: RoomUpdate
) -> RoomResponse:
    """Update room details"""
    trace_id = get_trace_id()
    logger.info(
        "Updating room in service",
        extra={
            "event": "room_update_service",
            "room_id": str(room_id),
            "trace_id": trace_id
        }
    )
    try:
        room = await update_room(db, room_id, room_in)
        response = RoomResponse.model_validate(room, from_attributes=True)
        response.trace_id = trace_id
        return response
    except RoomNotFoundError as e:
        logger.error(
            "Room not found for update",
            extra={
                "event": "room_update_failed_service",
                "reason": "not_found",
                "room_id": str(room_id),
                "trace_id": trace_id
            }
        )
        raise RoomNotFoundServiceError(str(e))
    except DatabaseError as e:
        logger.error(
            "Database error in room update",
            extra={
                "event": "room_update_failed_service",
                "reason": "database_error",
                "room_id": str(room_id),
                "error": str(e),
                "trace_id": trace_id
            }
        )
        raise DatabaseServiceError(str(e))

async def delete_room_service(db: AsyncSession, room_id: uuid.UUID) -> None:
    """Delete a room"""
    trace_id = get_trace_id()
    logger.info(
        "Deleting room in service",
        extra={
            "event": "room_delete_service",
            "room_id": str(room_id),
            "trace_id": trace_id
        }
    )
    try:
        await delete_room(db, room_id)
    except RoomNotFoundError as e:
        logger.error(
            "Room not found for deletion",
            extra={
                "event": "room_delete_failed_service",
                "reason": "not_found",
                "room_id": str(room_id),
                "trace_id": trace_id
            }
        )
        raise RoomNotFoundServiceError(str(e))
    except ValueError as e:
        logger.error(
            "Cannot delete room",
            extra={
                "event": "room_delete_failed_service",
                "reason": "invalid_operation",
                "room_id": str(room_id),
                "error": str(e),
                "trace_id": trace_id
            }
        )
        raise RoomServiceError(str(e))
    except DatabaseError as e:
        logger.error(
            "Database error in room deletion",
            extra={
                "event": "room_delete_failed_service",
                "reason": "database_error",
                "room_id": str(room_id),
                "error": str(e),
                "trace_id": trace_id
            }
        )
        raise DatabaseServiceError(str(e)) 