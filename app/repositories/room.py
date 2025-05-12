from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from app.models.room import Room
from app.schemas.room import RoomCreate, RoomUpdate
from app.core.logging import logger
from app.middlewares.trace_id import get_trace_id
import uuid

class RoomRepositoryError(Exception):
    """Base exception for room repository errors"""
    pass

class RoomAlreadyExistsError(RoomRepositoryError):
    """Raised when attempting to create a room with a name that already exists for the user"""
    pass

class RoomNotFoundError(RoomRepositoryError):
    """Raised when a room is not found"""
    pass

class DatabaseError(RoomRepositoryError):
    """Raised when there's a database error"""
    pass

async def create_room(db: AsyncSession, room_in: RoomCreate, user_id: uuid.UUID) -> Room:
    """Create a new room"""
    trace_id = get_trace_id()
    logger.info(
        "Creating room in repository",
        extra={
            "event": "room_creation_repo",
            "user_id": str(user_id),
            "room_name": room_in.name,
            "trace_id": trace_id
        }
    )
    try:
        room = Room(
            name=room_in.name,
            description=room_in.description,
            created_by=user_id,
            type=room_in.type
        )
        db.add(room)
        await db.commit()
        await db.refresh(room)
        logger.info(
            "Room created successfully",
            extra={
                "event": "room_created_repo",
                "room_id": str(room.id),
                "user_id": str(user_id),
                "trace_id": trace_id
            }
        )
        return room
    except IntegrityError as e:
        await db.rollback()
        logger.error(
            "Room creation failed: name already exists",
            extra={
                "event": "room_creation_failed_repo",
                "reason": "name_exists",
                "user_id": str(user_id),
                "room_name": room_in.name,
                "trace_id": trace_id
            }
        )
        raise RoomAlreadyExistsError("Room with this name already exists")
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error(
            "Database error while creating room",
            extra={
                "event": "room_creation_failed_repo",
                "reason": "database_error",
                "user_id": str(user_id),
                "room_name": room_in.name,
                "error": str(e),
                "trace_id": trace_id
            }
        )
        raise DatabaseError("Failed to create room due to database error")

async def get_room_by_id(db: AsyncSession, room_id: uuid.UUID) -> Room:
    """Get room by ID"""
    trace_id = get_trace_id()
    logger.info(
        "Fetching room by ID",
        extra={
            "event": "room_fetch_by_id",
            "room_id": str(room_id),
            "trace_id": trace_id
        }
    )
    try:
        result = await db.execute(select(Room).filter(Room.id == room_id))
        room = result.scalar_one_or_none()
        if not room:
            logger.warning(
                "Room not found",
                extra={
                    "event": "room_not_found",
                    "room_id": str(room_id),
                    "trace_id": trace_id
                }
            )
            raise RoomNotFoundError("Room not found")
        return room
    except SQLAlchemyError as e:
        logger.error(
            "Database error while fetching room",
            extra={
                "event": "room_fetch_failed",
                "reason": "database_error",
                "room_id": str(room_id),
                "error": str(e),
                "trace_id": trace_id
            }
        )
        raise DatabaseError("Failed to fetch room due to database error")

async def get_user_rooms(db: AsyncSession, user_id: uuid.UUID, skip: int = 0, limit: int = 100) -> tuple[list[Room], int]:
    """Get all rooms for a user"""
    trace_id = get_trace_id()
    logger.info(
        "Fetching user rooms",
        extra={
            "event": "user_rooms_fetch",
            "user_id": str(user_id),
            "trace_id": trace_id
        }
    )
    try:
        # Get total count
        count_result = await db.execute(
            select(func.count()).select_from(Room).filter(Room.created_by == user_id)
        )
        total = count_result.scalar_one()

        # Get rooms
        result = await db.execute(
            select(Room)
            .filter(Room.created_by == user_id)
            .offset(skip)
            .limit(limit)
        )
        rooms = result.scalars().all()
        return rooms, total
    except SQLAlchemyError as e:
        logger.error(
            "Database error while fetching user rooms",
            extra={
                "event": "user_rooms_fetch_failed",
                "reason": "database_error",
                "user_id": str(user_id),
                "error": str(e),
                "trace_id": trace_id
            }
        )
        raise DatabaseError("Failed to fetch user rooms due to database error")

async def search_rooms(db: AsyncSession, user_id: uuid.UUID, query: str, skip: int = 0, limit: int = 100) -> tuple[list[Room], int]:
    """Search rooms by name"""
    trace_id = get_trace_id()
    logger.info(
        "Searching rooms",
        extra={
            "event": "room_search",
            "user_id": str(user_id),
            "query": query,
            "trace_id": trace_id
        }
    )
    try:
        # Get total count
        count_result = await db.execute(
            select(func.count())
            .select_from(Room)
            .filter(
                Room.created_by == user_id,
                Room.name.ilike(f"%{query}%")
            )
        )
        total = count_result.scalar_one()

        # Get rooms
        result = await db.execute(
            select(Room)
            .filter(
                Room.created_by == user_id,
                Room.name.ilike(f"%{query}%")
            )
            .offset(skip)
            .limit(limit)
        )
        rooms = result.scalars().all()
        return rooms, total
    except SQLAlchemyError as e:
        logger.error(
            "Database error while searching rooms",
            extra={
                "event": "room_search_failed",
                "reason": "database_error",
                "user_id": str(user_id),
                "query": query,
                "error": str(e),
                "trace_id": trace_id
            }
        )
        raise DatabaseError("Failed to search rooms due to database error")

async def update_room(db: AsyncSession, room_id: uuid.UUID, room_in: RoomUpdate) -> Room:
    """Update room details"""
    trace_id = get_trace_id()
    logger.info(
        "Updating room",
        extra={
            "event": "room_update",
            "room_id": str(room_id),
            "trace_id": trace_id
        }
    )
    try:
        # Get current room
        room = await get_room_by_id(db, room_id)
        
        # Update fields
        update_data = room_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(room, field, value)
        
        await db.commit()
        await db.refresh(room)
        
        logger.info(
            "Room updated successfully",
            extra={
                "event": "room_updated",
                "room_id": str(room_id),
                "trace_id": trace_id
            }
        )
        return room
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error(
            "Database error while updating room",
            extra={
                "event": "room_update_failed",
                "reason": "database_error",
                "room_id": str(room_id),
                "error": str(e),
                "trace_id": trace_id
            }
        )
        raise DatabaseError("Failed to update room due to database error")

async def delete_room(db: AsyncSession, room_id: uuid.UUID) -> None:
    """Delete a room"""
    trace_id = get_trace_id()
    logger.info(
        "Deleting room",
        extra={
            "event": "room_delete",
            "room_id": str(room_id),
            "trace_id": trace_id
        }
    )
    try:
        # Check if room exists
        room = await get_room_by_id(db, room_id)
        
        # Don't allow deletion of default room
        if room.is_default:
            logger.warning(
                "Cannot delete default room",
                extra={
                    "event": "room_delete_failed",
                    "reason": "is_default",
                    "room_id": str(room_id),
                    "trace_id": trace_id
                }
            )
            raise ValueError("Cannot delete default room")
        
        await db.delete(room)
        await db.commit()
        
        logger.info(
            "Room deleted successfully",
            extra={
                "event": "room_deleted",
                "room_id": str(room_id),
                "trace_id": trace_id
            }
        )
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error(
            "Database error while deleting room",
            extra={
                "event": "room_delete_failed",
                "reason": "database_error",
                "room_id": str(room_id),
                "error": str(e),
                "trace_id": trace_id
            }
        )
        raise DatabaseError("Failed to delete room due to database error") 