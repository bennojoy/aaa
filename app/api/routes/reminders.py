from datetime import datetime
from typing import List, Optional
from uuid import UUID
import logging
import json
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.repositories.reminder_repository import ReminderRepository
from app.schemas.reminder import Reminder, ReminderCreate, ReminderUpdate
from app.middlewares.trace_id import get_trace_id
from app.core.logging import logger

router = APIRouter(prefix="/reminders", tags=["reminders"])

def _log(level: str, trace_id: str, message: str, **kwargs):
    """
    Helper method for JSON-formatted logging in API routes.
    
    Args:
        level (str): Log level (info, error, debug)
        trace_id (str): Request trace ID for tracking
        message (str): Log message
        **kwargs: Additional fields to include in the log
    """
    log_data = {
        "timestamp": datetime.utcnow().isoformat(),
        "trace_id": trace_id,
        "message": message,
        "component": "reminder_api",
        **kwargs
    }
    getattr(logger, level)(json.dumps(log_data))

@router.post("/", response_model=Reminder)
async def create_reminder(
    *,
    reminder_in: ReminderCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Reminder:
    """
    Create a new reminder.
    
    Args:
        reminder_in (ReminderCreate): Reminder creation data
        db (AsyncSession): Database session
        current_user (User): Current authenticated user
        
    Returns:
        Reminder: Created reminder object
        
    Raises:
        HTTPException: If reminder creation fails
    """
    trace_id = get_trace_id()
    logger.info(
        "API: Creating new reminder",
        extra={
            "event": "api_reminder_create",
            "room_id": str(reminder_in.room_id),
            "user_id": str(current_user.id),
            "trace_id": trace_id
        }
    )
    
    try:
        reminder_repo = ReminderRepository(db)
        reminder = await reminder_repo.create(
            obj_in=reminder_in,
            trace_id=trace_id
        )
        logger.info(
            "API: Successfully created reminder",
            extra={
                "event": "api_reminder_create_success",
                "reminder_id": str(reminder.id),
                "trace_id": trace_id
            }
        )
        return reminder
    except Exception as e:
        logger.error(
            "API: Failed to create reminder",
            extra={
                "event": "api_reminder_create_failed",
                "error": str(e),
                "room_id": str(reminder_in.room_id),
                "trace_id": trace_id
            }
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create reminder"
        )

@router.get("/{reminder_id}", response_model=Reminder)
async def get_reminder(
    reminder_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Reminder:
    """
    Get a reminder by ID.
    
    Args:
        reminder_id (UUID): Reminder ID
        db (AsyncSession): Database session
        current_user (User): Current authenticated user
        
    Returns:
        Reminder: Reminder object
        
    Raises:
        HTTPException: If reminder not found
    """
    trace_id = get_trace_id()
    logger.debug(
        "API: Fetching reminder",
        extra={
            "event": "api_reminder_get",
            "reminder_id": str(reminder_id),
            "trace_id": trace_id
        }
    )
    
    reminder_repo = ReminderRepository(db)
    reminder = await reminder_repo.get_by_id(
        reminder_id=reminder_id,
        trace_id=trace_id
    )
    
    if not reminder:
        logger.error(
            "API: Reminder not found",
            extra={
                "event": "api_reminder_get_failed",
                "reason": "not_found",
                "reminder_id": str(reminder_id),
                "trace_id": trace_id
            }
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reminder not found"
        )
    
    return reminder

@router.get("/room/{room_id}", response_model=List[Reminder])
async def get_room_reminders(
    room_id: UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> List[Reminder]:
    """
    Get all reminders for a room.
    
    Args:
        room_id (UUID): Room ID
        skip (int): Number of records to skip
        limit (int): Maximum number of records to return
        db (AsyncSession): Database session
        current_user (User): Current authenticated user
        
    Returns:
        List[Reminder]: List of reminders in the room
    """
    trace_id = get_trace_id()
    logger.debug(
        "API: Fetching room reminders",
        extra={
            "event": "api_room_reminders_get",
            "room_id": str(room_id),
            "skip": skip,
            "limit": limit,
            "trace_id": trace_id
        }
    )
    
    reminder_repo = ReminderRepository(db)
    reminders = await reminder_repo.get_by_room(
        room_id=room_id,
        trace_id=trace_id,
        skip=skip,
        limit=limit
    )
    
    return reminders

@router.get("/user/created", response_model=List[Reminder])
async def get_user_created_reminders(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> List[Reminder]:
    """
    Get all reminders created by the current user.
    
    Args:
        skip (int): Number of records to skip
        limit (int): Maximum number of records to return
        db (AsyncSession): Database session
        current_user (User): Current authenticated user
        
    Returns:
        List[Reminder]: List of reminders created by the user
    """
    trace_id = get_trace_id()
    logger.debug(
        "API: Fetching user created reminders",
        extra={
            "event": "api_user_reminders_get",
            "user_id": str(current_user.id),
            "skip": skip,
            "limit": limit,
            "trace_id": trace_id
        }
    )
    
    reminder_repo = ReminderRepository(db)
    reminders = await reminder_repo.get_by_creator(
        user_id=current_user.id,
        trace_id=trace_id,
        skip=skip,
        limit=limit
    )
    
    return reminders

@router.put("/{reminder_id}", response_model=Reminder)
async def update_reminder(
    reminder_id: UUID,
    reminder_in: ReminderUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Reminder:
    """
    Update a reminder.
    
    Args:
        reminder_id (UUID): Reminder ID
        reminder_in (ReminderUpdate): Update data
        db (AsyncSession): Database session
        current_user (User): Current authenticated user
        
    Returns:
        Reminder: Updated reminder object
        
    Raises:
        HTTPException: If reminder not found or update fails
    """
    trace_id = get_trace_id()
    logger.info(
        "API: Updating reminder",
        extra={
            "event": "api_reminder_update",
            "reminder_id": str(reminder_id),
            "trace_id": trace_id
        }
    )
    
    reminder_repo = ReminderRepository(db)
    reminder = await reminder_repo.get_by_id(
        reminder_id=reminder_id,
        trace_id=trace_id
    )
    
    if not reminder:
        logger.error(
            "API: Reminder not found",
            extra={
                "event": "api_reminder_update_failed",
                "reason": "not_found",
                "reminder_id": str(reminder_id),
                "trace_id": trace_id
            }
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reminder not found"
        )
    
    try:
        updated_reminder = await reminder_repo.update(
            db_obj=reminder,
            obj_in=reminder_in,
            trace_id=trace_id
        )
        logger.info(
            "API: Successfully updated reminder",
            extra={
                "event": "api_reminder_update_success",
                "reminder_id": str(reminder_id),
                "trace_id": trace_id
            }
        )
        return updated_reminder
    except Exception as e:
        logger.error(
            "API: Failed to update reminder",
            extra={
                "event": "api_reminder_update_failed",
                "reason": "update_error",
                "reminder_id": str(reminder_id),
                "error": str(e),
                "trace_id": trace_id
            }
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update reminder"
        )

@router.delete("/{reminder_id}", response_model=Reminder)
async def delete_reminder(
    reminder_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Reminder:
    """
    Delete a reminder.
    
    Args:
        reminder_id (UUID): Reminder ID
        db (AsyncSession): Database session
        current_user (User): Current authenticated user
        
    Returns:
        Reminder: Deleted reminder object
        
    Raises:
        HTTPException: If reminder not found or deletion fails
    """
    trace_id = get_trace_id()
    logger.info(
        "API: Deleting reminder",
        extra={
            "event": "api_reminder_delete",
            "reminder_id": str(reminder_id),
            "trace_id": trace_id
        }
    )
    
    reminder_repo = ReminderRepository(db)
    reminder = await reminder_repo.get_by_id(
        reminder_id=reminder_id,
        trace_id=trace_id
    )
    
    if not reminder:
        logger.error(
            "API: Reminder not found",
            extra={
                "event": "api_reminder_delete_failed",
                "reason": "not_found",
                "reminder_id": str(reminder_id),
                "trace_id": trace_id
            }
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reminder not found"
        )
    
    try:
        deleted_reminder = await reminder_repo.delete(
            reminder_id=reminder_id,
            trace_id=trace_id
        )
        logger.info(
            "API: Successfully deleted reminder",
            extra={
                "event": "api_reminder_delete_success",
                "reminder_id": str(reminder_id),
                "trace_id": trace_id
            }
        )
        return deleted_reminder
    except Exception as e:
        logger.error(
            "API: Failed to delete reminder",
            extra={
                "event": "api_reminder_delete_failed",
                "reason": "delete_error",
                "reminder_id": str(reminder_id),
                "error": str(e),
                "trace_id": trace_id
            }
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete reminder"
        ) 