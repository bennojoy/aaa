from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
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
from app.middlewares.trace_id import get_trace_id
from app.core.security import hash_password, verify_password
from app.core.logging import logger
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

async def create_user_service(db: AsyncSession, user: UserCreate) -> User:
    """
    Create a new user.
    
    Args:
        db (AsyncSession): Database session.
        user (UserCreate): User data.
    
    Returns:
        User: Created user.
    
    Raises:
        UserServiceError: If user creation fails.
    """
    trace_id = get_trace_id()
    logger.info(
        "Creating new user",
        extra={
            "event": "user_creation_start",
            "phone": user.phone_number,
            "trace_id": trace_id
        }
    )
    try:
        # Check if user exists
        existing_user = await get_user_by_phone(db, user.phone_number)
        if existing_user:
            logger.warning(
                "User already exists",
                extra={
                    "event": "user_creation_failed",
                    "reason": "user_exists",
                    "phone": user.phone_number,
                    "trace_id": trace_id
                }
            )
            raise UserAlreadyExistsServiceError("User already exists")
        
        # Create user
        user = await create_user_repo(db, user)
        logger.info(
            "User created successfully",
            extra={
                "event": "user_creation_success",
                "user_id": str(user.id),
                "phone": user.phone_number,
                "trace_id": trace_id
            }
        )
        return user
    except UserRepositoryError as e:
        logger.error(
            "Error creating user",
            extra={
                "event": "user_creation_failed",
                "reason": "repository_error",
                "error": str(e),
                "phone": user.phone_number,
                "trace_id": trace_id
            }
        )
        raise DatabaseServiceError(str(e))
    except Exception as e:
        logger.error(
            "Unexpected error creating user",
            extra={
                "event": "user_creation_failed",
                "reason": "unexpected_error",
                "error": str(e),
                "phone": user.phone_number,
                "trace_id": trace_id
            }
        )
        raise DatabaseServiceError("An unexpected error occurred")

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