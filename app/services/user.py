from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User, LoginStatus, UserType
from app.schemas.user import UserCreate, UserLogin
from app.repositories.user import (
    create_user_repo,
    get_user_by_phone,
    get_user_by_alias,
    check_alias_availability,
    update_user_alias,
    UserRepositoryError,
    UserAlreadyExistsError,
    DatabaseError,
    AliasAlreadyExistsError
)
from app.repositories.room import create_room
from app.repositories.participant import add_participant
from app.schemas.room import RoomCreate
from app.schemas.participant import ParticipantCreate
from app.middlewares.trace_id import get_trace_id
from app.core.security import hash_password, verify_password
from app.core.logging import logger
from app.models.room import RoomType
import uuid

class UserServiceError(Exception):
    """Base exception for user service errors"""
    pass

class UserAlreadyExistsServiceError(UserServiceError):
    """Raised when attempting to create a user that already exists"""
    pass

class DatabaseServiceError(UserServiceError):
    """Raised when there's a database error"""
    pass

class AliasAlreadyExistsServiceError(UserServiceError):
    """Raised when attempting to use an alias that already exists"""
    pass

async def create_assistant_and_default_room(db: AsyncSession, user_id: uuid.UUID) -> None:
    """Create an assistant user and default room for a new user"""
    trace_id = get_trace_id()
    logger.info(
        "Creating assistant and default room",
        extra={
            "event": "assistant_creation_start",
            "user_id": str(user_id),
            "trace_id": trace_id
        }
    )
    try:
        # Get user's phone number
        user = await db.get(User, user_id)
        if not user:
            raise DatabaseError("User not found")
            
        # Create assistant user with phone number based on user's phone
        assistant_phone = f"+888{user.phone_number.lstrip('+')}"  # Use user's phone number with +888 prefix
        assistant_alias = f"Assistant_{user_id}"
        assistant_data = UserCreate(
            phone_number=assistant_phone,
            alias=assistant_alias,
            password="bot_password",  # Simple password for bot
            user_type=UserType.BOT,
            language="en"
        )
        assistant = await create_user_repo(db, assistant_data)
        
        # Create default room
        room_data = RoomCreate(
            name="Assistant",
            description="Your personal assistant room",
            type=RoomType.ASSISTANT
        )
        room = await create_room(db, room_data, user_id)
        room.is_default = True
        await db.commit()
        
        # Add assistant to room
        participant_data = ParticipantCreate(
            user_id=assistant.id,
            role="member",
            status="active"
        )
        await add_participant(db, room.id, participant_data)
        
        logger.info(
            "Assistant and default room created successfully",
            extra={
                "event": "assistant_creation_success",
                "user_id": str(user_id),
                "assistant_id": str(assistant.id),
                "room_id": str(room.id),
                "trace_id": trace_id
            }
        )
    except Exception as e:
        logger.error(
            "Error creating assistant and default room",
            extra={
                "event": "assistant_creation_failed",
                "reason": "unexpected_error",
                "user_id": str(user_id),
                "error": str(e),
                "trace_id": trace_id
            }
        )
        raise DatabaseError("Failed to create assistant and default room")

async def create_user_service(db: AsyncSession, user_in: UserCreate) -> User:
    """Create a new user"""
    trace_id = get_trace_id()
    logger.info(
        "Creating user in service",
        extra={
            "event": "user_creation_service",
            "phone": user_in.phone_number,
            "trace_id": trace_id
        }
    )
    try:
        # Check if user already exists
        existing_user = await get_user_by_phone(db, user_in.phone_number)
        if existing_user:
            logger.info(
                "User already exists",
                extra={
                    "event": "user_exists",
                    "phone": user_in.phone_number,
                    "trace_id": trace_id
                }
            )
            return existing_user

        # Create new user
        user = await create_user_repo(db, user_in)
        
        # Create assistant and default room
        await create_assistant_and_default_room(db, user.id)
        
        logger.info(
            "User created successfully",
            extra={
                "event": "user_created_service",
                "user_id": str(user.id),
                "phone": user_in.phone_number,
                "trace_id": trace_id
            }
        )
        return user
    except Exception as e:
        logger.error(
            "Error creating user",
            extra={
                "event": "user_creation_failed_service",
                "reason": "unexpected_error",
                "phone": user_in.phone_number,
                "error": str(e),
                "trace_id": trace_id
            }
        )
        raise DatabaseError("Failed to create user due to database error")

async def authenticate_user_service(db: AsyncSession, identifier: str, password: str) -> User:
    """
    Authenticate a user.
    
    Args:
        db (AsyncSession): Database session.
        identifier (str): User identifier (phone or alias).
        password (str): User password.
    
    Returns:
        User: Authenticated user if successful, None otherwise.
    """
    trace_id = get_trace_id()
    logger.info(
        "Authenticating user",
        extra={
            "event": "authentication_start",
            "identifier": identifier,
            "trace_id": trace_id
        }
    )
    
    try:
        # Try to find user by phone or alias
        user = await get_user_by_phone(db, identifier)
        if not user:
            user = await get_user_by_alias(db, identifier)
        
        if not user:
            logger.warning(
                "User not found",
                extra={
                    "event": "authentication_failed",
                    "reason": "user_not_found",
                    "identifier": identifier,
                    "trace_id": trace_id
                }
            )
            return None
        
        # Verify password
        if not verify_password(password, user.hashed_password):
            logger.warning(
                "Invalid password",
                extra={
                    "event": "authentication_failed",
                    "reason": "invalid_password",
                    "user_id": str(user.id),
                    "trace_id": trace_id
                }
            )
            return None
        
        logger.info(
            "User authenticated successfully",
            extra={
                "event": "authentication_success",
                "user_id": str(user.id),
                "trace_id": trace_id
            }
        )
        return user
    except Exception as e:
        logger.error(
            "Error authenticating user",
            extra={
                "event": "authentication_failed",
                "reason": "unexpected_error",
                "error": str(e),
                "identifier": identifier,
                "trace_id": trace_id
            }
        )
        return None

async def check_alias_availability_service(db: AsyncSession, alias: str) -> bool:
    """
    Check if an alias is available.
    
    Args:
        db (AsyncSession): Database session.
        alias (str): Alias to check.
    
    Returns:
        bool: True if alias is available, False otherwise.
    """
    trace_id = get_trace_id()
    logger.info(
        "Checking alias availability",
        extra={
            "event": "alias_check",
            "alias": alias,
            "trace_id": trace_id
        }
    )
    
    try:
        is_available = await check_alias_availability(db, alias)
        logger.info(
            "Alias availability checked",
            extra={
                "event": "alias_check_complete",
                "alias": alias,
                "available": is_available,
                "trace_id": trace_id
            }
        )
        return is_available
    except Exception as e:
        logger.error(
            "Error checking alias availability",
            extra={
                "event": "alias_check_failed",
                "reason": "unexpected_error",
                "error": str(e),
                "alias": alias,
                "trace_id": trace_id
            }
        )
        raise DatabaseServiceError("An unexpected error occurred")

async def update_user_alias_service(db: AsyncSession, user_id: uuid.UUID, new_alias: str) -> User:
    """
    Update user's alias.
    
    Args:
        db (AsyncSession): Database session.
        user_id (UUID): User ID.
        new_alias (str): New alias.
    
    Returns:
        User: Updated user.
    
    Raises:
        AliasAlreadyExistsServiceError: If alias is already taken.
        DatabaseServiceError: If database error occurs.
    """
    trace_id = get_trace_id()
    logger.info(
        "Updating user alias",
        extra={
            "event": "alias_update_start",
            "user_id": str(user_id),
            "new_alias": new_alias,
            "trace_id": trace_id
        }
    )
    
    try:
        # Check if alias is available
        if not await check_alias_availability(db, new_alias):
            logger.warning(
                "Alias already exists",
                extra={
                    "event": "alias_update_failed",
                    "reason": "alias_exists",
                    "user_id": str(user_id),
                    "new_alias": new_alias,
                    "trace_id": trace_id
                }
            )
            raise AliasAlreadyExistsServiceError("Alias already exists")
        
        # Update alias
        user = await update_user_alias(db, user_id, new_alias)
        logger.info(
            "Alias updated successfully",
            extra={
                "event": "alias_update_success",
                "user_id": str(user_id),
                "new_alias": new_alias,
                "trace_id": trace_id
            }
        )
        return user
    except UserRepositoryError as e:
        logger.error(
            "Error updating alias",
            extra={
                "event": "alias_update_failed",
                "reason": "repository_error",
                "error": str(e),
                "user_id": str(user_id),
                "new_alias": new_alias,
                "trace_id": trace_id
            }
        )
        raise DatabaseServiceError(str(e))
    except Exception as e:
        logger.error(
            "Unexpected error updating alias",
            extra={
                "event": "alias_update_failed",
                "reason": "unexpected_error",
                "error": str(e),
                "user_id": str(user_id),
                "new_alias": new_alias,
                "trace_id": trace_id
            }
        )
        raise DatabaseServiceError("An unexpected error occurred") 