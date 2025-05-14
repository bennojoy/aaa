from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.schemas.participant import (
    ParticipantCreate,
    ParticipantUpdate,
    ParticipantResponse,
    ParticipantList,
    UserSearchResponse,
    UserSearchList,
    MessagePermissionResponse
)
from app.services.participant import (
    add_participant_service,
    get_room_participants_service,
    search_room_participants_service,
    search_users_service,
    update_participant_service,
    remove_participant_service,
    transfer_ownership_service,
    ParticipantServiceError,
    ParticipantAlreadyExistsServiceError,
    ParticipantNotFoundServiceError,
    DatabaseServiceError,
    PermissionServiceError,
    RoomLimitExceededError,
    UserRoomLimitExceededError,
    check_message_permission_service
)
from app.middlewares.trace_id import get_trace_id
from app.core.logging import logger
import uuid

router = APIRouter(prefix="/rooms", tags=["participants"])

@router.post("/rooms/{room_id}/participants", response_model=ParticipantResponse)
async def add_participant(
    room_id: uuid.UUID,
    participant_in: ParticipantCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Add a new participant to a room"""
    try:
        return await add_participant_service(db, room_id, participant_in, current_user.id)
    except ParticipantAlreadyExistsServiceError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except PermissionServiceError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except RoomLimitExceededError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except UserRoomLimitExceededError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except DatabaseServiceError as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/rooms/{room_id}/participants", response_model=ParticipantList)
async def get_room_participants(
    room_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all participants in a room"""
    try:
        return await get_room_participants_service(db, room_id)
    except DatabaseServiceError as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/rooms/{room_id}/participants/search", response_model=ParticipantList)
async def search_room_participants(
    room_id: uuid.UUID,
    query: str = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Search participants in a room. If no query is provided, returns all participants."""
    try:
        return await search_room_participants_service(db, room_id, query or "")
    except DatabaseServiceError as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/users/search", response_model=UserSearchList)
async def search_users(
    query: str = Query(..., min_length=1),
    exclude_room_id: uuid.UUID = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Search users globally"""
    try:
        return await search_users_service(db, query, exclude_room_id)
    except DatabaseServiceError as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/rooms/{room_id}/participants/{user_id}", response_model=ParticipantResponse)
async def update_participant(
    room_id: uuid.UUID,
    user_id: uuid.UUID,
    participant_in: ParticipantUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update participant details"""
    try:
        return await update_participant_service(db, room_id, user_id, participant_in, current_user.id)
    except ParticipantNotFoundServiceError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionServiceError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except DatabaseServiceError as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/rooms/{room_id}/participants/{user_id}")
async def remove_participant(
    room_id: uuid.UUID,
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Remove a participant from a room"""
    try:
        await remove_participant_service(db, room_id, user_id, current_user.id)
        return {"message": "Participant removed successfully"}
    except ParticipantNotFoundServiceError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionServiceError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except DatabaseServiceError as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/rooms/{room_id}/transfer-ownership/{new_owner_id}", response_model=ParticipantResponse)
async def transfer_ownership(
    room_id: uuid.UUID,
    new_owner_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Transfer room ownership to another participant"""
    try:
        return await transfer_ownership_service(db, room_id, new_owner_id, current_user.id)
    except ParticipantNotFoundServiceError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionServiceError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except DatabaseServiceError as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{room_id}/message-permission/{user_id}", response_model=MessagePermissionResponse)
async def check_message_permission(
    room_id: uuid.UUID,
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Check if a user can send messages in a room and get all non-assistant participants.
    This endpoint is intended for system services to check message permissions.
    
    Args:
        room_id (UUID): ID of the room to check
        user_id (UUID): ID of the user to check permissions for
        db (AsyncSession): Database session
        current_user (dict): Current authenticated user (system service)
        
    Returns:
        MessagePermissionResponse: Permission status and list of participants
    """
    trace_id = get_trace_id()
    logger.info(
        "API: Checking message permission",
        extra={
            "event": "api_message_permission_check",
            "user_id": str(user_id),
            "room_id": str(room_id),
            "trace_id": trace_id
        }
    )
    
    try:
        result = await check_message_permission_service(
            db,
            user_id,
            room_id
        )
        return result
    except Exception as e:
        logger.error(
            "API: Error checking message permission",
            extra={
                "event": "api_message_permission_check_failed",
                "reason": "unexpected_error",
                "user_id": str(user_id),
                "room_id": str(room_id),
                "error": str(e),
                "trace_id": trace_id
            }
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to check message permission"
        ) 