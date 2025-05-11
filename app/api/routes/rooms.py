from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.room import RoomCreate, RoomUpdate, RoomResponse, RoomList
from app.services.room import (
    create_room_service,
    get_room_service,
    get_user_rooms_service,
    search_rooms_service,
    update_room_service,
    delete_room_service,
    RoomServiceError,
    RoomAlreadyExistsServiceError,
    RoomNotFoundServiceError,
    DatabaseServiceError
)
from app.db.session import get_db
from app.middlewares.trace_id import get_trace_id
from app.core.security import decode_access_token
from fastapi.security import OAuth2PasswordBearer
import uuid

router = APIRouter(prefix="/rooms", tags=["rooms"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")

async def get_current_user_id(token: str = Depends(oauth2_scheme)) -> uuid.UUID:
    """Get current user ID from token"""
    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )
    return payload["sub"]

@router.post("", response_model=RoomResponse)
async def create_room(
    room_in: RoomCreate,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id)
):
    """Create a new room"""
    try:
        return await create_room_service(db, room_in, user_id)
    except RoomAlreadyExistsServiceError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except DatabaseServiceError as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("", response_model=RoomList)
async def list_rooms(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id)
):
    """List all rooms for the current user"""
    try:
        return await get_user_rooms_service(db, user_id, skip, limit)
    except DatabaseServiceError as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/search", response_model=RoomList)
async def search_rooms(
    query: str = Query(..., min_length=1),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id)
):
    """Search rooms by name"""
    try:
        return await search_rooms_service(db, user_id, query, skip, limit)
    except DatabaseServiceError as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{room_id}", response_model=RoomResponse)
async def get_room(
    room_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id)
):
    """Get room details"""
    try:
        return await get_room_service(db, room_id)
    except RoomNotFoundServiceError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except DatabaseServiceError as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{room_id}", response_model=RoomResponse)
async def update_room(
    room_id: uuid.UUID,
    room_in: RoomUpdate,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id)
):
    """Update room details"""
    try:
        return await update_room_service(db, room_id, room_in)
    except RoomNotFoundServiceError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except DatabaseServiceError as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{room_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_room(
    room_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id)
):
    """Delete a room"""
    try:
        await delete_room_service(db, room_id)
    except RoomNotFoundServiceError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RoomServiceError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except DatabaseServiceError as e:
        raise HTTPException(status_code=500, detail=str(e)) 