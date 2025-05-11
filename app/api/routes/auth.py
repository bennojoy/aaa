from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.user import UserCreate, UserLogin, UserResponse, TokenResponse, AliasCheck, AliasUpdate, GeneratedAliasResponse
from app.services.user import (
    create_user_service,
    authenticate_user_service,
    check_alias_availability_service,
    update_user_alias_service,
    UserServiceError,
    UserAlreadyExistsServiceError,
    DatabaseServiceError,
    AliasAlreadyExistsServiceError
)
from app.repositories.user import generate_unique_alias
from app.db.session import get_db
from app.middlewares.trace_id import get_trace_id
from app.core.security import create_access_token, decode_access_token
from app.core.logging import logger
from fastapi.security import OAuth2PasswordBearer
import uuid

router = APIRouter(prefix="/auth", tags=["auth"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")

@router.post("/signup", response_model=UserResponse)
async def signup(user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    """
    Register a new user.
    
    Args:
        user_in (UserCreate): User registration data.
        db (AsyncSession): Database session.
    
    Returns:
        UserResponse: Created user data with trace_id.
    
    Raises:
        HTTPException: If user already exists.
    """
    trace_id = get_trace_id()
    logger.info(
        "Attempting to register user",
        extra={
            "event": "signup_attempt",
            "phone": user_in.phone_number,
            "trace_id": trace_id
        }
    )
    try:
        user = await create_user_service(db, user_in)
        logger.info(
            "User registered successfully",
            extra={
                "event": "signup_success",
                "user_id": str(user.id),
                "phone": user_in.phone_number,
                "trace_id": trace_id
            }
        )
        response = UserResponse.model_validate(user, from_attributes=True)
        response.trace_id = trace_id
        return response.model_dump()
    except UserAlreadyExistsServiceError as e:
        logger.error(
            "User registration failed: user exists",
            extra={
                "event": "signup_failed",
                "reason": "user_exists",
                "phone": user_in.phone_number,
                "error": str(e),
                "trace_id": trace_id
            }
        )
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(
            "Error registering user",
            extra={
                "event": "signup_failed",
                "reason": "unexpected_error",
                "phone": user_in.phone_number,
                "error": str(e),
                "trace_id": trace_id,
                "error_type": type(e).__name__,
                "error_module": e.__class__.__module__
            },
            exc_info=True
        )
        raise HTTPException(status_code=400, detail="User registration failed.")

@router.post("/signin", response_model=TokenResponse)
async def signin(user_in: UserLogin, db: AsyncSession = Depends(get_db)):
    """
    Authenticate a user and return an access token.
    
    Args:
        user_in (UserLogin): User login credentials.
        db (AsyncSession): Database session.
    
    Returns:
        TokenResponse: Access token, token type, and trace_id.
    
    Raises:
        HTTPException: If credentials are invalid.
    """
    trace_id = get_trace_id()
    logger.info(
        "API: Signin request received",
        extra={
            "event": "api_signin_request",
            "identifier": user_in.identifier,
            "layer": "api",
            "trace_id": trace_id
        }
    )
    try:
        user = await authenticate_user_service(db, user_in.identifier, user_in.password)
        if not user:
            logger.warning(
                "API: Invalid credentials",
                extra={
                    "event": "api_signin_failed",
                    "reason": "invalid_credentials",
                    "identifier": user_in.identifier,
                    "layer": "api",
                    "trace_id": trace_id
                }
            )
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
        logger.info(
            "API: User signed in successfully",
            extra={
                "event": "api_signin_success",
                "user_id": str(user.id),
                "identifier": user_in.identifier,
                "layer": "api",
                "trace_id": trace_id
            }
        )
        access_token = create_access_token(data={"sub": str(user.id)})
        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            trace_id=trace_id
        )
    except Exception as e:
        logger.error(
            "API: Unexpected error during signin",
            extra={
                "event": "api_signin_failed",
                "reason": "unexpected_error",
                "identifier": user_in.identifier,
                "error": str(e),
                "error_type": type(e).__name__,
                "error_module": e.__class__.__module__,
                "layer": "api",
                "trace_id": trace_id
            },
            exc_info=True
        )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

@router.post("/check-alias", response_model=dict)
async def check_alias(alias_check: AliasCheck, db: AsyncSession = Depends(get_db)):
    """
    Check if an alias is available.
    
    Args:
        alias_check (AliasCheck): Alias to check.
        db (AsyncSession): Database session.
    
    Returns:
        dict: Availability status and trace_id.
    
    Raises:
        HTTPException: If database error occurs.
    """
    trace_id = get_trace_id()
    logger.info(
        f"Checking alias availability: {alias_check.alias}",
        extra={
            "event": "alias_check",
            "alias": alias_check.alias,
            "trace_id": trace_id
        }
    )
    try:
        is_available = await check_alias_availability_service(db, alias_check.alias)
        return {
            "alias": alias_check.alias,
            "available": is_available,
            "trace_id": trace_id
        }
    except Exception as e:
        logger.error(
            f"Error checking alias: {str(e)}",
            extra={
                "event": "alias_check_failed",
                "reason": "unexpected_error",
                "alias": alias_check.alias,
                "trace_id": trace_id
            }
        )
        raise HTTPException(status_code=500, detail="An unexpected error occurred")

@router.put("/update-alias/{user_id}", response_model=UserResponse)
async def update_alias(
    user_id: uuid.UUID,
    alias_update: AliasUpdate,
    db: AsyncSession = Depends(get_db)
):
    """
    Update a user's alias.
    
    Args:
        user_id (UUID): User ID.
        alias_update (AliasUpdate): New alias.
        db (AsyncSession): Database session.
    
    Returns:
        UserResponse: Updated user data with trace_id.
    
    Raises:
        HTTPException: If alias is taken or user not found.
    """
    trace_id = get_trace_id()
    logger.info(
        f"Updating alias for user {user_id}",
        extra={
            "event": "alias_update",
            "user_id": str(user_id),
            "new_alias": alias_update.new_alias,
            "trace_id": trace_id
        }
    )
    try:
        user = await update_user_alias_service(db, user_id, alias_update.new_alias)
        return UserResponse(**user.__dict__, trace_id=trace_id)
    except AliasAlreadyExistsServiceError as e:
        logger.error(
            f"Alias already exists: {str(e)}",
            extra={
                "event": "alias_update_failed",
                "reason": "alias_exists",
                "user_id": str(user_id),
                "trace_id": trace_id
            }
        )
        raise HTTPException(status_code=400, detail="Alias already taken")
    except Exception as e:
        logger.error(
            f"Error updating alias: {str(e)}",
            extra={
                "event": "alias_update_failed",
                "reason": "unexpected_error",
                "user_id": str(user_id),
                "trace_id": trace_id
            }
        )
        raise HTTPException(status_code=500, detail="An unexpected error occurred")

@router.get("/generate-alias", response_model=GeneratedAliasResponse)
async def generate_alias(db: AsyncSession = Depends(get_db)):
    """
    Generate a unique alias.
    
    Args:
        db (AsyncSession): Database session.
    
    Returns:
        GeneratedAliasResponse: Generated unique alias and trace_id.
    
    Raises:
        HTTPException: If database error occurs.
    """
    trace_id = get_trace_id()
    logger.info(
        "Generating unique alias",
        extra={
            "event": "alias_generation",
            "trace_id": trace_id
        }
    )
    try:
        alias = await generate_unique_alias(db)
        logger.info(
            f"Generated alias: {alias}",
            extra={
                "event": "alias_generated",
                "alias": alias,
                "trace_id": trace_id
            }
        )
        return GeneratedAliasResponse(alias=alias, trace_id=trace_id)
    except Exception as e:
        logger.error(
            f"Error generating alias: {str(e)}",
            extra={
                "event": "alias_generation_failed",
                "reason": "unexpected_error",
                "trace_id": trace_id
            }
        )
        raise HTTPException(status_code=500, detail="Failed to generate alias")

@router.get("/protected")
async def protected_route(token: str = Depends(oauth2_scheme)):
    """
    Protected route that requires authentication.
    
    Args:
        token (str): JWT token from Authorization header.
    
    Returns:
        dict: Success message and trace_id.
    
    Raises:
        HTTPException: If token is invalid.
    """
    trace_id = get_trace_id()
    payload = decode_access_token(token)
    if not payload:
        logger.warning(
            "Invalid token provided",
            extra={
                "event": "auth_failed",
                "reason": "invalid_token",
                "trace_id": trace_id
            }
        )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    logger.info(
        f"Protected route accessed",
        extra={
            "event": "protected_route_accessed",
            "user_id": str(payload.get('sub')),
            "trace_id": trace_id
        }
    )
    return {"message": "You are authenticated", "trace_id": trace_id} 