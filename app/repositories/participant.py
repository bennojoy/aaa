from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from app.models.participant import Participant, ParticipantRole
from app.models.user import User
from app.schemas.participant import ParticipantCreate, ParticipantUpdate
from app.core.logging import logger
from app.middlewares.trace_id import get_trace_id
import uuid

class ParticipantRepositoryError(Exception):
    """Base exception for participant repository errors"""
    pass

class ParticipantAlreadyExistsError(ParticipantRepositoryError):
    """Raised when attempting to add a user who is already a participant"""
    pass

class ParticipantNotFoundError(ParticipantRepositoryError):
    """Raised when a participant is not found"""
    pass

class DatabaseError(ParticipantRepositoryError):
    """Raised when there's a database error"""
    pass

async def add_participant(db: AsyncSession, room_id: uuid.UUID, participant_in: ParticipantCreate) -> Participant:
    """Add a new participant to a room"""
    trace_id = get_trace_id()
    logger.info(
        "Adding participant to room",
        extra={
            "event": "participant_add",
            "room_id": str(room_id),
            "user_id": str(participant_in.user_id),
            "trace_id": trace_id
        }
    )
    try:
        participant = Participant(
            room_id=room_id,
            user_id=participant_in.user_id,
            role=participant_in.role,
            status=participant_in.status
        )
        db.add(participant)
        await db.commit()
        await db.refresh(participant)
        return participant
    except IntegrityError as e:
        await db.rollback()
        logger.error(
            "Failed to add participant: already exists",
            extra={
                "event": "participant_add_failed",
                "reason": "already_exists",
                "room_id": str(room_id),
                "user_id": str(participant_in.user_id),
                "trace_id": trace_id
            }
        )
        raise ParticipantAlreadyExistsError("User is already a participant in this room")
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error(
            "Database error while adding participant",
            extra={
                "event": "participant_add_failed",
                "reason": "database_error",
                "room_id": str(room_id),
                "user_id": str(participant_in.user_id),
                "error": str(e),
                "trace_id": trace_id
            }
        )
        raise DatabaseError("Failed to add participant due to database error")

async def get_participant(db: AsyncSession, room_id: uuid.UUID, user_id: uuid.UUID) -> Participant:
    """Get a participant by room_id and user_id"""
    trace_id = get_trace_id()
    logger.info(
        "Getting participant",
        extra={
            "event": "participant_get",
            "room_id": str(room_id),
            "user_id": str(user_id),
            "trace_id": trace_id
        }
    )
    try:
        result = await db.execute(
            select(Participant).filter(
                and_(
                    Participant.room_id == room_id,
                    Participant.user_id == user_id
                )
            )
        )
        participant = result.scalar_one_or_none()
        if not participant:
            raise ParticipantNotFoundError("Participant not found")
        return participant
    except SQLAlchemyError as e:
        logger.error(
            "Database error while getting participant",
            extra={
                "event": "participant_get_failed",
                "reason": "database_error",
                "room_id": str(room_id),
                "user_id": str(user_id),
                "error": str(e),
                "trace_id": trace_id
            }
        )
        raise DatabaseError("Failed to get participant due to database error")

async def get_room_participants(db: AsyncSession, room_id: uuid.UUID) -> list[Participant]:
    """Get all participants in a room"""
    trace_id = get_trace_id()
    logger.info(
        "Getting room participants",
        extra={
            "event": "room_participants_get",
            "room_id": str(room_id),
            "trace_id": trace_id
        }
    )
    try:
        result = await db.execute(
            select(Participant).filter(Participant.room_id == room_id)
        )
        return result.scalars().all()
    except SQLAlchemyError as e:
        logger.error(
            "Database error while getting room participants",
            extra={
                "event": "room_participants_get_failed",
                "reason": "database_error",
                "room_id": str(room_id),
                "error": str(e),
                "trace_id": trace_id
            }
        )
        raise DatabaseError("Failed to get room participants due to database error")

async def search_room_participants(
    db: AsyncSession,
    room_id: uuid.UUID,
    query: str
) -> list[Participant]:
    """Search participants in a room by user alias or phone number. If query is empty, returns all participants."""
    trace_id = get_trace_id()
    logger.info(
        "Searching room participants",
        extra={
            "event": "room_participants_search",
            "room_id": str(room_id),
            "query": query,
            "trace_id": trace_id
        }
    )
    try:
        # Base query with room filter
        base_query = select(Participant).filter(Participant.room_id == room_id)
        
        # If query is provided, add user search conditions
        if query:
            result = await db.execute(
                base_query
                .join(User, func.replace(User.id, '-', '') == func.replace(Participant.user_id, '-', ''))
                .filter(
                    or_(
                        User.alias.ilike(f"%{query}%"),
                        User.phone_number.ilike(f"%{query}%")
                    )
                )
            )
        else:
            # If no query, return all participants
            result = await db.execute(base_query)
            
        return result.scalars().all()
    except SQLAlchemyError as e:
        logger.error(
            "Database error while searching room participants",
            extra={
                "event": "room_participants_search_failed",
                "reason": "database_error",
                "room_id": str(room_id),
                "query": query,
                "error": str(e),
                "trace_id": trace_id
            }
        )
        raise DatabaseError("Failed to search room participants due to database error")

async def search_users(
    db: AsyncSession,
    query: str,
    exclude_room_id: uuid.UUID = None
) -> list[User]:
    """Search users globally by alias or phone number"""
    trace_id = get_trace_id()
    logger.info(
        "Searching users",
        extra={
            "event": "users_search",
            "query": query,
            "exclude_room_id": str(exclude_room_id) if exclude_room_id else None,
            "trace_id": trace_id
        }
    )
    try:
        # Base query
        query_filter = or_(
            User.alias.ilike(f"%{query}%"),
            User.phone_number.ilike(f"%{query}%")
        )

        # If excluding users from a room
        if exclude_room_id:
            subquery = select(Participant.user_id).filter(Participant.room_id == exclude_room_id)
            query_filter = and_(query_filter, User.id.notin_(subquery))

        result = await db.execute(
            select(User).filter(query_filter)
        )
        return result.scalars().all()
    except SQLAlchemyError as e:
        logger.error(
            "Database error while searching users",
            extra={
                "event": "users_search_failed",
                "reason": "database_error",
                "query": query,
                "error": str(e),
                "trace_id": trace_id
            }
        )
        raise DatabaseError("Failed to search users due to database error")

async def update_participant(
    db: AsyncSession,
    room_id: uuid.UUID,
    user_id: uuid.UUID,
    participant_in: ParticipantUpdate
) -> Participant:
    """Update participant details"""
    trace_id = get_trace_id()
    logger.info(
        "Updating participant",
        extra={
            "event": "participant_update",
            "room_id": str(room_id),
            "user_id": str(user_id),
            "trace_id": trace_id
        }
    )
    try:
        participant = await get_participant(db, room_id, user_id)
        
        # Don't allow changing owner's role
        if participant.role == ParticipantRole.OWNER:
            raise ValueError("Cannot modify owner's role")

        update_data = participant_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(participant, field, value)
        
        await db.commit()
        await db.refresh(participant)
        return participant
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error(
            "Database error while updating participant",
            extra={
                "event": "participant_update_failed",
                "reason": "database_error",
                "room_id": str(room_id),
                "user_id": str(user_id),
                "error": str(e),
                "trace_id": trace_id
            }
        )
        raise DatabaseError("Failed to update participant due to database error")

async def remove_participant(db: AsyncSession, room_id: uuid.UUID, user_id: uuid.UUID) -> None:
    """Remove a participant from a room"""
    trace_id = get_trace_id()
    logger.info(
        "Removing participant",
        extra={
            "event": "participant_remove",
            "room_id": str(room_id),
            "user_id": str(user_id),
            "trace_id": trace_id
        }
    )
    try:
        participant = await get_participant(db, room_id, user_id)
        
        # Don't allow removing owner
        if participant.role == ParticipantRole.OWNER:
            raise ValueError("Cannot remove room owner")

        await db.delete(participant)
        await db.commit()
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error(
            "Database error while removing participant",
            extra={
                "event": "participant_remove_failed",
                "reason": "database_error",
                "room_id": str(room_id),
                "user_id": str(user_id),
                "error": str(e),
                "trace_id": trace_id
            }
        )
        raise DatabaseError("Failed to remove participant due to database error")

async def transfer_ownership(
    db: AsyncSession,
    room_id: uuid.UUID,
    current_owner_id: uuid.UUID,
    new_owner_id: uuid.UUID
) -> Participant:
    """Transfer room ownership to another participant"""
    trace_id = get_trace_id()
    logger.info(
        "Transferring room ownership",
        extra={
            "event": "ownership_transfer",
            "room_id": str(room_id),
            "current_owner_id": str(current_owner_id),
            "new_owner_id": str(new_owner_id),
            "trace_id": trace_id
        }
    )
    try:
        # Get current owner
        current_owner = await get_participant(db, room_id, current_owner_id)
        if current_owner.role != ParticipantRole.OWNER:
            raise ValueError("Current user is not the room owner")

        # Get new owner
        new_owner = await get_participant(db, room_id, new_owner_id)
        
        # Update roles
        current_owner.role = ParticipantRole.MEMBER
        new_owner.role = ParticipantRole.OWNER
        
        await db.commit()
        await db.refresh(new_owner)
        return new_owner
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error(
            "Database error while transferring ownership",
            extra={
                "event": "ownership_transfer_failed",
                "reason": "database_error",
                "room_id": str(room_id),
                "current_owner_id": str(current_owner_id),
                "new_owner_id": str(new_owner_id),
                "error": str(e),
                "trace_id": trace_id
            }
        )
        raise DatabaseError("Failed to transfer ownership due to database error") 