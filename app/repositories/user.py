from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from app.models.user import User, LoginStatus, UserType
from app.schemas.user import UserCreate
from app.core.security import hash_password, verify_password
from app.core.logging import logger, bind_context
from app.middlewares.trace_id import get_trace_id
import random
import string
import uuid

class UserRepositoryError(Exception):
    """Base exception for user repository errors"""
    pass

class UserAlreadyExistsError(UserRepositoryError):
    """Raised when attempting to create a user that already exists"""
    pass

class DatabaseError(UserRepositoryError):
    """Raised when there's a database error"""
    pass

class AliasAlreadyExistsError(UserRepositoryError):
    """Raised when attempting to use an alias that already exists"""
    pass

async def generate_unique_alias(db: AsyncSession, base_alias: str = None) -> str:
    """Generate a unique alias by appending random numbers if needed"""
    if not base_alias:
        # Generate a random alias if none provided
        base_alias = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
    
    alias = base_alias
    while True:
        if not await get_user_by_alias(db, alias):
            return alias
        # Append 3 random digits to make it unique
        alias = f"{base_alias}{random.randint(100, 999)}"

async def create_user_repo(db: AsyncSession, user_in: UserCreate) -> User:
    """Create a new user"""
    trace_id = get_trace_id()
    logger.info(
        "Creating user in repository",
        extra={
            "event": "user_creation_repo",
            "trace_id": trace_id
        }
    )
    try:
        # Generate or validate alias
        if user_in.alias:
            if await get_user_by_alias(db, user_in.alias):
                # Generate unique alias based on provided one
                unique_alias = await generate_unique_alias(db, user_in.alias)
                logger.info(
                    f"Generated unique alias: {unique_alias}",
                    extra={
                        "event": "alias_generated",
                        "alias": unique_alias,
                        "trace_id": trace_id
                    }
                )
            else:
                unique_alias = user_in.alias
        else:
            # Generate completely new alias
            unique_alias = await generate_unique_alias(db)
            logger.info(
                f"Generated new alias: {unique_alias}",
                extra={
                    "event": "alias_generated",
                    "alias": unique_alias,
                    "trace_id": trace_id
                }
            )

        # Create user with hashed password
        user = User(
            phone_number=user_in.phone_number,
            alias=unique_alias,
            hashed_password=hash_password(user_in.password),
            is_active=True,
            login_status=LoginStatus.OFFLINE,
            user_type=user_in.user_type,
            language=user_in.language
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        logger.info(
            f"User created in repository: {user.id}",
            extra={
                "event": "user_created_repo",
                "user_id": user.id,
                "trace_id": trace_id
            }
        )
        return user
    except IntegrityError as e:
        await db.rollback()
        logger.error(
            f"User creation failed in repository: {str(e)}",
            extra={
                "event": "user_creation_failed_repo",
                "reason": "integrity_error",
                "trace_id": trace_id
            },
            exc_info=True
        )
        raise UserAlreadyExistsError("User already exists")
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error(
            f"Database error while creating user: {str(e)}",
            extra={
                "event": "user_creation_failed_repo",
                "reason": "database_error",
                "trace_id": trace_id
            },
            exc_info=True
        )
        raise DatabaseError("Failed to create user due to database error")

async def get_user_by_id(db: AsyncSession, user_id: uuid.UUID) -> User:
    """
    Get user by ID.
    
    Args:
        db (AsyncSession): Database session.
        user_id (UUID): User ID.
    
    Returns:
        User: User object if found, None otherwise.
    """
    trace_id = get_trace_id()
    logger.info(
        f"Fetching user by ID: {user_id}",
        extra={
            "event": "user_fetch_by_id",
            "user_id": str(user_id),
            "trace_id": trace_id
        }
    )
    try:
        result = await db.execute(select(User).filter(User.id == user_id))
        return result.scalar_one_or_none()
    except SQLAlchemyError as e:
        logger.error(
            f"Database error while fetching user: {str(e)}",
            extra={
                "event": "user_fetch_failed",
                "reason": "database_error",
                "user_id": str(user_id),
                "trace_id": trace_id
            }
        )
        raise DatabaseError("Failed to fetch user due to database error")

async def get_user_by_alias(db: AsyncSession, alias: str) -> User:
    """Get user by alias"""
    trace_id = get_trace_id()
    logger.info(
        f"Fetching user by alias: {alias}",
        extra={
            "event": "user_fetch_by_alias",
            "alias": alias,
            "trace_id": trace_id
        }
    )
    try:
        result = await db.execute(select(User).filter(User.alias == alias))
        return result.scalar_one_or_none()
    except SQLAlchemyError as e:
        logger.error(
            f"Database error while fetching user: {str(e)}",
            extra={
                "event": "user_fetch_failed",
                "reason": "database_error",
                "alias": alias,
                "trace_id": trace_id
            }
        )
        raise DatabaseError("Failed to fetch user due to database error")

async def check_alias_availability(db: AsyncSession, alias: str) -> bool:
    """Check if an alias is available"""
    trace_id = get_trace_id()
    logger.info(
        f"Checking alias availability: {alias}",
        extra={
            "event": "alias_check_repo",
            "alias": alias,
            "trace_id": trace_id
        }
    )
    try:
        return await get_user_by_alias(db, alias) is None
    except SQLAlchemyError as e:
        logger.error(
            f"Database error while checking alias: {str(e)}",
            extra={
                "event": "alias_check_failed_repo",
                "reason": "database_error",
                "alias": alias,
                "trace_id": trace_id
            }
        )
        raise DatabaseError("Failed to check alias availability")

async def update_user_alias(db: AsyncSession, user_id: uuid.UUID, new_alias: str) -> User:
    """
    Update user's alias.
    
    Args:
        db (AsyncSession): Database session.
        user_id (UUID): User ID.
        new_alias (str): New alias.
    
    Returns:
        User: Updated user.
    
    Raises:
        ValueError: If alias is already taken.
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
        raise ValueError("Alias already exists")
    
    # Update alias
    stmt = update(User).where(User.id == user_id).values(alias=new_alias)
    try:
        await db.execute(stmt)
        await db.commit()
        user = await get_user_by_id(db, user_id)
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
    except Exception as e:
        await db.rollback()
        logger.error(
            "Error updating alias",
            extra={
                "event": "alias_update_failed",
                "reason": "database_error",
                "user_id": str(user_id),
                "new_alias": new_alias,
                "error": str(e),
                "trace_id": trace_id
            }
        )
        raise

async def get_user_by_phone(db: AsyncSession, phone: str) -> User:
    """
    Get user by phone number.
    
    Args:
        db (AsyncSession): Database session.
        phone (str): User phone number.
    
    Returns:
        User: User object if found, None otherwise.
    """
    trace_id = get_trace_id()
    logger.info(
        "Getting user by phone",
        extra={
            "event": "get_user_by_phone",
            "phone": phone,
            "trace_id": trace_id
        }
    )
    try:
        stmt = select(User).where(User.phone_number == phone)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        if user:
            logger.info(
                "User found",
                extra={
                    "event": "user_found",
                    "user_id": str(user.id),
                    "phone": phone,
                    "trace_id": trace_id
                }
            )
        else:
            logger.warning(
                "User not found",
                extra={
                    "event": "user_not_found",
                    "phone": phone,
                    "trace_id": trace_id
                }
            )
        return user
    except SQLAlchemyError as e:
        logger.error(
            "Database error while fetching user",
            extra={
                "event": "user_fetch_failed",
                "reason": "database_error",
                "phone": phone,
                "error": str(e),
                "trace_id": trace_id
            }
        )
        raise DatabaseError("Failed to fetch user due to database error")

async def authenticate_user_repo(db: AsyncSession, identifier: str, password: str) -> User:
    """
    Authenticate a user by phone number or alias.
    """
    trace_id = get_trace_id()
    logger.info(
        "REPO: Starting user authentication",
        extra={
            "event": "repo_auth_start",
            "identifier": identifier,
            "layer": "repository",
            "trace_id": trace_id
        }
    )
    try:
        # Try to find user by phone number first
        user = await get_user_by_phone(db, identifier)
        
        # If not found by phone, try by alias
        if not user:
            logger.info(
                "REPO: User not found by phone, trying alias",
                extra={
                    "event": "repo_auth_phone_not_found",
                    "identifier": identifier,
                    "layer": "repository",
                    "trace_id": trace_id
                }
            )
            user = await get_user_by_alias(db, identifier)
        
        if not user:
            logger.warning(
                "REPO: User not found",
                extra={
                    "event": "repo_auth_failed",
                    "reason": "user_not_found",
                    "identifier": identifier,
                    "layer": "repository",
                    "trace_id": trace_id
                }
            )
            return None
            
        if not verify_password(password, user.hashed_password):
            logger.warning(
                "REPO: Invalid password",
                extra={
                    "event": "repo_auth_failed",
                    "reason": "invalid_password",
                    "identifier": identifier,
                    "layer": "repository",
                    "trace_id": trace_id
                }
            )
            return None
            
        logger.info(
            "REPO: User authenticated successfully",
            extra={
                "event": "repo_auth_success",
                "user_id": user.id,
                "identifier": identifier,
                "layer": "repository",
                "trace_id": trace_id
            }
        )
        return user
        
    except Exception as e:
        logger.error(
            "REPO: Database error during authentication",
            extra={
                "event": "repo_auth_failed",
                "reason": "database_error",
                "identifier": identifier,
                "error": str(e),
                "layer": "repository",
                "trace_id": trace_id
            }
        )
        raise DatabaseError(f"Database error: {str(e)}")

async def create_user_repository(db: AsyncSession, user_data: dict) -> User:
    """
    Create a new user in the database.
    
    Args:
        db (AsyncSession): Database session.
        user_data (dict): User data including hashed password.
    
    Returns:
        User: Created user.
    
    Raises:
        UserAlreadyExistsError: If user already exists.
        DatabaseError: If database error occurs.
    """
    trace_id = get_trace_id()
    logger.info(
        "Creating user in repository",
        extra={
            "event": "repository_user_creation_start",
            "phone": user_data.get("phone_number"),
            "trace_id": trace_id
        }
    )
    try:
        # Check if user exists
        existing_user = await get_user_by_phone(db, user_data["phone_number"])
        if existing_user:
            logger.warning(
                "User creation failed: phone number exists",
                extra={
                    "event": "repository_user_creation_failed",
                    "reason": "phone_exists",
                    "phone": user_data["phone_number"],
                    "trace_id": trace_id
                }
            )
            raise UserAlreadyExistsError("User with this phone number already exists")
        
        # Create new user
        user = User(**user_data)
        db.add(user)
        await db.commit()
        await db.refresh(user)
        
        logger.info(
            "User created in repository",
            extra={
                "event": "repository_user_creation_success",
                "user_id": user.id,
                "phone": user_data["phone_number"],
                "trace_id": trace_id
            }
        )
        return user
        
    except UserAlreadyExistsError:
        raise
    except Exception as e:
        logger.error(
            "Database error during user creation",
            extra={
                "event": "repository_user_creation_failed",
                "reason": "database_error",
                "phone": user_data.get("phone_number"),
                "error": str(e),
                "trace_id": trace_id
            }
        )
        raise DatabaseError(f"Database error: {str(e)}")

async def generate_unique_alias(db: AsyncSession) -> str:
    """
    Generate a unique alias.
    
    Args:
        db (AsyncSession): Database session.
    
    Returns:
        str: Generated unique alias.
    """
    trace_id = get_trace_id()
    logger.info(
        "Generating unique alias",
        extra={
            "event": "alias_generation_start",
            "trace_id": trace_id
        }
    )
    
    while True:
        # Generate random alias
        alias = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
        
        # Check if alias is available
        if await check_alias_availability(db, alias):
            logger.info(
                "Unique alias generated",
                extra={
                    "event": "alias_generation_success",
                    "alias": alias,
                    "trace_id": trace_id
                }
            )
            return alias 