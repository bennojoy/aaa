from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID
import logging
import json
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from dateutil.rrule import rrulestr

from app.models.reminder import Reminder
from app.schemas.reminder import ReminderCreate, ReminderUpdate
from app.core.logging import logger

class ReminderRepository:
    """
    Repository for managing reminders in the database.
    
    This repository handles all database operations for reminders, including:
    - Creating new reminders
    - Retrieving reminders by various criteria
    - Updating existing reminders
    - Deleting reminders
    - Managing reminder triggers and recurrence
    
    All operations include JSON-formatted logging with trace_id for request tracking.
    """

    def __init__(self, db: AsyncSession):
        """
        Initialize the repository with a database session.
        
        Args:
            db (AsyncSession): SQLAlchemy async database session
        """
        self.db = db

    async def create(self, *, obj_in: ReminderCreate, trace_id: str) -> Reminder:
        """
        Create a new reminder.
        
        Args:
            obj_in (ReminderCreate): Reminder creation data
            trace_id (str): Request trace ID for tracking
            
        Returns:
            Reminder: Created reminder object
            
        Raises:
            Exception: If reminder creation fails
        """
        logger.info(
            "Repository: Creating new reminder",
            extra={
                "event": "repository_reminder_create",
                "room_id": str(obj_in.room_id),
                "created_by": str(obj_in.created_by_user_id),
                "trace_id": trace_id
            }
        )
        
        try:
            # Ensure start_time is in UTC
            if obj_in.start_time.tzinfo is None:
                obj_in.start_time = obj_in.start_time.replace(tzinfo=timezone.utc)
            
            # Calculate next trigger time
            next_trigger_time = obj_in.start_time
            if obj_in.rrule:
                rule = rrulestr(obj_in.rrule, dtstart=obj_in.start_time)
                next_trigger_time = rule.after(datetime.now(timezone.utc))

            db_obj = Reminder(
                room_id=obj_in.room_id,
                created_by_user_id=obj_in.created_by_user_id,
                title=obj_in.title,
                description=obj_in.description,
                start_time=obj_in.start_time,
                rrule=obj_in.rrule,
                next_trigger_time=next_trigger_time
            )
            self.db.add(db_obj)
            await self.db.commit()
            await self.db.refresh(db_obj)
            
            logger.info(
                "Repository: Successfully created reminder",
                extra={
                    "event": "repository_reminder_create_success",
                    "reminder_id": str(db_obj.id),
                    "trace_id": trace_id
                }
            )
            return db_obj
        except Exception as e:
            logger.error(
                "Repository: Failed to create reminder",
                extra={
                    "event": "repository_reminder_create_failed",
                    "error": str(e),
                    "room_id": str(obj_in.room_id),
                    "trace_id": trace_id
                }
            )
            await self.db.rollback()
            raise

    async def get_by_id(self, reminder_id: UUID, trace_id: str) -> Optional[Reminder]:
        """
        Get a reminder by its ID.
        
        Args:
            reminder_id (UUID): Reminder ID
            trace_id (str): Request trace ID for tracking
            
        Returns:
            Optional[Reminder]: Reminder object if found, None otherwise
        """
        logger.debug(
            "Repository: Fetching reminder by ID",
            extra={
                "event": "repository_reminder_get",
                "reminder_id": str(reminder_id),
                "trace_id": trace_id
            }
        )
        result = await self.db.execute(
            select(Reminder).filter(Reminder.id == reminder_id)
        )
        return result.scalar_one_or_none()

    async def get_by_room(
        self,
        room_id: UUID,
        trace_id: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[Reminder]:
        """
        Get all reminders for a specific room.
        
        Args:
            room_id (UUID): Room ID
            trace_id (str): Request trace ID for tracking
            skip (int): Number of records to skip
            limit (int): Maximum number of records to return
            
        Returns:
            List[Reminder]: List of reminders in the room
        """
        logger.debug(
            "Repository: Fetching reminders for room",
            extra={
                "event": "repository_room_reminders_get",
                "room_id": str(room_id),
                "skip": skip,
                "limit": limit,
                "trace_id": trace_id
            }
        )
        result = await self.db.execute(
            select(Reminder)
            .filter(Reminder.room_id == room_id)
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    async def get_by_creator(
        self,
        user_id: UUID,
        trace_id: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[Reminder]:
        """
        Get all reminders created by a specific user.
        
        Args:
            user_id (UUID): User ID
            trace_id (str): Request trace ID for tracking
            skip (int): Number of records to skip
            limit (int): Maximum number of records to return
            
        Returns:
            List[Reminder]: List of reminders created by the user
        """
        logger.debug(
            "Repository: Fetching reminders by creator",
            extra={
                "event": "repository_user_reminders_get",
                "user_id": str(user_id),
                "skip": skip,
                "limit": limit,
                "trace_id": trace_id
            }
        )
        result = await self.db.execute(
            select(Reminder)
            .filter(Reminder.created_by_user_id == user_id)
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    async def update(
        self,
        *,
        db_obj: Reminder,
        obj_in: ReminderUpdate,
        trace_id: str
    ) -> Reminder:
        """
        Update an existing reminder.
        
        Args:
            db_obj (Reminder): Existing reminder object
            obj_in (ReminderUpdate): Update data
            trace_id (str): Request trace ID for tracking
            
        Returns:
            Reminder: Updated reminder object
            
        Raises:
            Exception: If reminder update fails
        """
        logger.info(
            "Repository: Updating reminder",
            extra={
                "event": "repository_reminder_update",
                "reminder_id": str(db_obj.id),
                "trace_id": trace_id
            }
        )
        try:
            update_data = obj_in.model_dump(exclude_unset=True)
            
            # If start_time or rrule is updated, recalculate next_trigger_time
            if "start_time" in update_data or "rrule" in update_data:
                start_time = update_data.get("start_time", db_obj.start_time)
                rrule = update_data.get("rrule", db_obj.rrule)
                
                if rrule:
                    rule = rrulestr(rrule, dtstart=start_time)
                    update_data["next_trigger_time"] = rule.after(datetime.now(timezone.utc))
                else:
                    update_data["next_trigger_time"] = start_time

            for field in update_data:
                setattr(db_obj, field, update_data[field])
            
            self.db.add(db_obj)
            await self.db.commit()
            await self.db.refresh(db_obj)
            
            logger.info(
                "Repository: Successfully updated reminder",
                extra={
                    "event": "repository_reminder_update_success",
                    "reminder_id": str(db_obj.id),
                    "trace_id": trace_id
                }
            )
            return db_obj
        except Exception as e:
            logger.error(
                "Repository: Failed to update reminder",
                extra={
                    "event": "repository_reminder_update_failed",
                    "reason": "update_error",
                    "reminder_id": str(db_obj.id),
                    "error": str(e),
                    "trace_id": trace_id
                }
            )
            await self.db.rollback()
            raise

    async def delete(self, *, reminder_id: UUID, trace_id: str) -> Reminder:
        """
        Delete a reminder.
        
        Args:
            reminder_id (UUID): Reminder ID
            trace_id (str): Request trace ID for tracking
            
        Returns:
            Reminder: Deleted reminder object
            
        Raises:
            Exception: If reminder deletion fails
        """
        logger.info(
            "Repository: Deleting reminder",
            extra={
                "event": "repository_reminder_delete",
                "reminder_id": str(reminder_id),
                "trace_id": trace_id
            }
        )
        try:
            result = await self.db.execute(
                select(Reminder).filter(Reminder.id == reminder_id)
            )
            obj = result.scalar_one_or_none()
            if obj:
                await self.db.delete(obj)
                await self.db.commit()
            
            logger.info(
                "Repository: Successfully deleted reminder",
                extra={
                    "event": "repository_reminder_delete_success",
                    "reminder_id": str(reminder_id),
                    "trace_id": trace_id
                }
            )
            return obj
        except Exception as e:
            logger.error(
                "Repository: Failed to delete reminder",
                extra={
                    "event": "repository_reminder_delete_failed",
                    "reason": "delete_error",
                    "reminder_id": str(reminder_id),
                    "error": str(e),
                    "trace_id": trace_id
                }
            )
            await self.db.rollback()
            raise

    async def get_due_reminders(self, *, limit: int = 100, trace_id: str) -> List[Reminder]:
        """
        Get reminders that are due to be triggered.
        
        Args:
            limit (int): Maximum number of reminders to return
            trace_id (str): Request trace ID for tracking
            
        Returns:
            List[Reminder]: List of due reminders
        """
        logger.debug(
            "Repository: Fetching due reminders",
            extra={
                "event": "repository_due_reminders_get",
                "limit": limit,
                "trace_id": trace_id
            }
        )
        result = await self.db.execute(
            select(Reminder)
            .filter(
                Reminder.status == "ACTIVE",
                Reminder.next_trigger_time <= datetime.now(timezone.utc)
            )
            .limit(limit)
        )
        return result.scalars().all()

    async def update_triggered(
        self,
        *,
        db_obj: Reminder,
        trace_id: str
    ) -> Reminder:
        """
        Update a reminder after it has been triggered.
        
        Args:
            db_obj (Reminder): Reminder object to update
            trace_id (str): Request trace ID for tracking
            
        Returns:
            Reminder: Updated reminder object
            
        Raises:
            Exception: If reminder update fails
        """
        logger.info(
            "Repository: Updating triggered reminder",
            extra={
                "event": "repository_reminder_triggered_update",
                "reminder_id": str(db_obj.id),
                "trace_id": trace_id
            }
        )
        try:
            now = datetime.now(timezone.utc)
            db_obj.last_triggered_at = now
            
            # Calculate next trigger time if recurring
            if db_obj.rrule:
                rule = rrulestr(db_obj.rrule, dtstart=db_obj.start_time)
                db_obj.next_trigger_time = rule.after(now)
            else:
                db_obj.status = "COMPLETED"
            
            self.db.add(db_obj)
            await self.db.commit()
            await self.db.refresh(db_obj)
            
            logger.info(
                "Repository: Successfully updated triggered reminder",
                extra={
                    "event": "repository_reminder_triggered_update_success",
                    "reminder_id": str(db_obj.id),
                    "next_trigger": str(db_obj.next_trigger_time),
                    "trace_id": trace_id
                }
            )
            return db_obj
        except Exception as e:
            logger.error(
                "Repository: Failed to update triggered reminder",
                extra={
                    "event": "repository_reminder_triggered_update_failed",
                    "reason": "update_error",
                    "reminder_id": str(db_obj.id),
                    "error": str(e),
                    "trace_id": trace_id
                }
            )
            await self.db.rollback()
            raise 