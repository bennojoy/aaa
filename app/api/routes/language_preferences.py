from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.services.language_preference_service import LanguagePreferenceService
from app.schemas.language_preference import (
    LanguagePreferenceUpdate,
    LanguagePreferenceResponse,
    LanguagePreferenceResetResponse
)
from app.api.deps import get_current_user
from app.models.user import User
import uuid

router = APIRouter()

@router.put(
    "/users/{user_id}/rooms/{room_id}/language-preferences",
    response_model=LanguagePreferenceResponse
)
async def update_language_preferences(
    user_id: str,
    room_id: str,
    preferences: LanguagePreferenceUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update language preferences for a user in a specific room"""
    try:
        user_id_uuid = uuid.UUID(user_id)
        room_id_uuid = uuid.UUID(room_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid ID format")
    
    service = LanguagePreferenceService(db)
    return await service.update_preferences(str(user_id_uuid), str(room_id_uuid), preferences)

@router.get(
    "/users/{user_id}/rooms/{room_id}/language-preferences",
    response_model=LanguagePreferenceResponse
)
async def get_language_preferences(
    user_id: str,
    room_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get language preferences for a user in a specific room"""
    try:
        user_id_uuid = uuid.UUID(user_id)
        room_id_uuid = uuid.UUID(room_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid ID format")
    
    service = LanguagePreferenceService(db)
    return await service.get_preferences(str(user_id_uuid), str(room_id_uuid))

@router.delete(
    "/users/{user_id}/rooms/{room_id}/language-preferences",
    response_model=LanguagePreferenceResetResponse
)
async def reset_language_preferences(
    user_id: str,
    room_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Reset language preferences for a user in a specific room to default values"""
    try:
        user_id_uuid = uuid.UUID(user_id)
        room_id_uuid = uuid.UUID(room_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid ID format")
    
    service = LanguagePreferenceService(db)
    return await service.reset_preferences(str(user_id_uuid), str(room_id_uuid)) 