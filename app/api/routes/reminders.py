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
    _log("info", trace_id, "Creating new reminder", 
         request={
             "room_id": str(reminder_in.room_id),
             "user_id": str(current_user.id),
             "title": reminder_in.title,
             "start_time": reminder_in.start_time.isoformat() if reminder_in.start_time else None,
             "rrule": reminder_in.rrule
         })
    
    try:
        reminder_repo = ReminderRepository(db)
        reminder = await reminder_repo.create(
            obj_in=reminder_in,
            trace_id=trace_id
        )
        _log("info", trace_id, "Successfully created reminder",
             response={
                 "reminder_id": str(reminder.id),
                 "title": reminder.title,
                 "start_time": reminder.start_time.isoformat(),
                 "next_trigger_time": reminder.next_trigger_time.isoformat() if reminder.next_trigger_time else None
             })
        return reminder
    except Exception as e:
        _log("error", trace_id, "Failed to create reminder",
             error=str(e),
             request={
                 "room_id": str(reminder_in.room_id),
                 "user_id": str(current_user.id)
             })
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
    _log("debug", trace_id, "Fetching reminder",
         request={
             "reminder_id": str(reminder_id),
             "user_id": str(current_user.id)
         })
    
    reminder_repo = ReminderRepository(db)
    reminder = await reminder_repo.get_by_id(
        reminder_id=reminder_id,
        trace_id=trace_id
    )
    
    if not reminder:
        _log("error", trace_id, "Reminder not found",
             request={
                 "reminder_id": str(reminder_id),
                 "user_id": str(current_user.id)
             })
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reminder not found"
        )
    
    _log("debug", trace_id, "Successfully fetched reminder",
         response={
             "reminder_id": str(reminder.id),
             "title": reminder.title,
             "start_time": reminder.start_time.isoformat(),
             "next_trigger_time": reminder.next_trigger_time.isoformat() if reminder.next_trigger_time else None
         })
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
    _log("debug", trace_id, "Fetching room reminders",
         request={
             "room_id": str(room_id),
             "user_id": str(current_user.id),
             "skip": skip,
             "limit": limit
         })
    
    reminder_repo = ReminderRepository(db)
    reminders = await reminder_repo.get_by_room(
        room_id=room_id,
        trace_id=trace_id,
        skip=skip,
        limit=limit
    )
    
    _log("debug", trace_id, "Successfully fetched room reminders",
         response={
             "room_id": str(room_id),
             "count": len(reminders),
             "reminders": [
                 {
                     "id": str(r.id),
                     "title": r.title,
                     "start_time": r.start_time.isoformat(),
                     "next_trigger_time": r.next_trigger_time.isoformat() if r.next_trigger_time else None
                 } for r in reminders
             ]
         })
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
    _log("debug", trace_id, "Fetching user created reminders",
         request={
             "user_id": str(current_user.id),
             "skip": skip,
             "limit": limit
         })
    
    reminder_repo = ReminderRepository(db)
    reminders = await reminder_repo.get_by_creator(
        user_id=current_user.id,
        trace_id=trace_id,
        skip=skip,
        limit=limit
    )
    
    _log("debug", trace_id, "Successfully fetched user created reminders",
         response={
             "user_id": str(current_user.id),
             "count": len(reminders),
             "reminders": [
                 {
                     "id": str(r.id),
                     "title": r.title,
                     "start_time": r.start_time.isoformat(),
                     "next_trigger_time": r.next_trigger_time.isoformat() if r.next_trigger_time else None
                 } for r in reminders
             ]
         })
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
    _log("info", trace_id, "Updating reminder",
         request={
             "reminder_id": str(reminder_id),
             "user_id": str(current_user.id),
             "updates": reminder_in.dict(exclude_unset=True)
         })
    
    reminder_repo = ReminderRepository(db)
    reminder = await reminder_repo.get_by_id(
        reminder_id=reminder_id,
        trace_id=trace_id
    )
    
    if not reminder:
        _log("error", trace_id, "Reminder not found",
             request={
                 "reminder_id": str(reminder_id),
                 "user_id": str(current_user.id)
             })
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
        _log("info", trace_id, "Successfully updated reminder",
             response={
                 "reminder_id": str(updated_reminder.id),
                 "title": updated_reminder.title,
                 "start_time": updated_reminder.start_time.isoformat(),
                 "next_trigger_time": updated_reminder.next_trigger_time.isoformat() if updated_reminder.next_trigger_time else None
             })
        return updated_reminder
    except Exception as e:
        _log("error", trace_id, "Failed to update reminder",
             error=str(e),
             request={
                 "reminder_id": str(reminder_id),
                 "user_id": str(current_user.id)
             })
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
    _log("info", trace_id, "Deleting reminder",
         request={
             "reminder_id": str(reminder_id),
             "user_id": str(current_user.id)
         })
    
    reminder_repo = ReminderRepository(db)
    reminder = await reminder_repo.get_by_id(
        reminder_id=reminder_id,
        trace_id=trace_id
    )
    
    if not reminder:
        _log("error", trace_id, "Reminder not found",
             request={
                 "reminder_id": str(reminder_id),
                 "user_id": str(current_user.id)
             })
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reminder not found"
        )
    
    try:
        deleted_reminder = await reminder_repo.delete(
            reminder_id=reminder_id,
            trace_id=trace_id
        )
        _log("info", trace_id, "Successfully deleted reminder",
             response={
                 "reminder_id": str(deleted_reminder.id),
                 "title": deleted_reminder.title,
                 "start_time": deleted_reminder.start_time.isoformat(),
                 "next_trigger_time": deleted_reminder.next_trigger_time.isoformat() if deleted_reminder.next_trigger_time else None
             })
        return deleted_reminder
    except Exception as e:
        _log("error", trace_id, "Failed to delete reminder",
             error=str(e),
             request={
                 "reminder_id": str(reminder_id),
                 "user_id": str(current_user.id)
             })
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete reminder"
        ) 