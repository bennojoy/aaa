import asyncio
import uuid
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select, and_
from dateutil.rrule import rrulestr

from app.models.reminder import Reminder as ReminderModel  # SQLAlchemy model
from .config import settings, logger
from .models import ReminderMessage  # Pydantic model for Kafka
from .producer import ReminderProducer

class ReminderScanner:
    def __init__(self):
        # Database setup - using same pattern as app
        self.engine = create_async_engine(
            settings.SQLALCHEMY_DATABASE_URI,
            echo=settings.DB_ECHO,
            future=True
        )
        self.async_session = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False
        )
        
        # Kafka producer
        self.producer = ReminderProducer()

    async def start(self):
        """Start the reminder scanner."""
        try:
            # Start Kafka producer
            await self.producer.start()
            
            logger.info({
                "event": "scanner_started",
                "scan_interval": settings.SCAN_INTERVAL_SECONDS
            })
            
            # Main loop
            while True:
                try:
                    logger.info({
                        "event": "scan_cycle_started",
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    })
                    
                    await self.scan_reminders()
                    
                    logger.info({
                        "event": "scan_cycle_completed",
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    })
                    
                except Exception as e:
                    logger.error({
                        "event": "scan_failed",
                        "error": str(e),
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    })
                
                # Wait for next scan
                logger.info({
                    "event": "sleeping",
                    "duration_seconds": settings.SCAN_INTERVAL_SECONDS,
                    "next_scan": (datetime.now(timezone.utc) + timedelta(seconds=settings.SCAN_INTERVAL_SECONDS)).isoformat()
                })
                await asyncio.sleep(settings.SCAN_INTERVAL_SECONDS)
                
        except Exception as e:
            logger.error({
                "event": "scanner_failed",
                "error": str(e)
            })
            raise
        finally:
            await self.stop()

    async def stop(self):
        """Stop the reminder scanner."""
        await self.producer.stop()
        await self.engine.dispose()
        logger.info({"event": "scanner_stopped"})

    async def scan_reminders(self):
        """Scan for due reminders and process them."""
        async with self.async_session() as session:
            async with session.begin():
                try:
                    # Get current time in UTC
                    now = datetime.now(timezone.utc)
                    
                    # Query for due reminders using SQLAlchemy model
                    stmt = select(ReminderModel).where(
                        and_(
                            ReminderModel.status == "ACTIVE",
                            ReminderModel.next_trigger_time <= now
                        )
                    ).with_for_update(skip_locked=True).limit(settings.BATCH_SIZE)
                    
                    result = await session.execute(stmt)
                    reminders = result.scalars().all()
                    
                    if not reminders:
                        logger.info({
                            "event": "no_reminders_found",
                            "timestamp": now.isoformat()
                        })
                        return
                    
                    logger.info({
                        "event": "reminders_found",
                        "count": len(reminders),
                        "timestamp": now.isoformat(),
                        "reminders": [
                            {
                                "id": str(r.id),
                                "room_id": str(r.room_id),
                                "title": r.title,
                                "description": r.description
                            } for r in reminders
                        ]
                    })
                    
                    # Process each reminder
                    for reminder in reminders:
                        try:
                            # Generate trace ID for this operation
                            trace_id = str(uuid.uuid4())
                            
                            # Create reminder payload
                            payload = {
                                "type": "reminder",
                                "reminder_id": str(reminder.id),
                                "title": reminder.title,
                                "description": reminder.description,
                                "start_time": reminder.start_time.isoformat(),
                                "next_trigger_time": reminder.next_trigger_time.isoformat(),
                                "rrule": reminder.rrule,
                                "status": reminder.status,
                                "created_at": reminder.created_at.isoformat(),
                                "updated_at": reminder.updated_at.isoformat(),
                                "last_triggered_at": reminder.last_triggered_at.isoformat() if reminder.last_triggered_at else None
                            }
                            
                            # Create message content
                            content = f"Reminder: {reminder.title}"
                            if reminder.description:
                                content += f"\n{reminder.description}"
                            
                            # Create reminder message using Pydantic model
                            message = ReminderMessage(
                                room_id=reminder.room_id,
                                sender_id=settings.SYSTEM_USER_UUID,  # Use system user instead of creator
                                content=content,
                                trace_id=trace_id,
                                timestamp=now,
                                payload=payload
                            )
                            
                            # Send to Kafka
                            await self.producer.send_reminder(message)
                            
                            # Update reminder
                            if reminder.rrule:
                                # Calculate next trigger time for recurring reminder
                                rule = rrulestr(reminder.rrule, dtstart=reminder.start_time)
                                next_time = rule.after(now)
                                reminder.next_trigger_time = next_time
                                reminder.last_triggered_at = now
                            else:
                                # Mark one-time reminder as completed
                                reminder.status = "COMPLETED"
                                reminder.last_triggered_at = now
                            
                            logger.info({
                                "event": "reminder_processed",
                                "room_id": str(message.room_id),
                                "sender_id": str(message.sender_id),
                                "content": message.content,
                                "trace_id": message.trace_id,
                                "timestamp": message.timestamp.isoformat(),
                                "payload": message.payload
                            })
                            
                        except Exception as e:
                            logger.error({
                                "event": "reminder_processing_failed",
                                "room_id": str(reminder.room_id),
                                "title": reminder.title,
                                "description": reminder.description,
                                "error": str(e),
                                "timestamp": now.isoformat()
                            })
                            raise
                except Exception as e:
                    logger.error({
                        "event": "session_error",
                        "error": str(e),
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    })
                    raise

async def main():
    scanner = ReminderScanner()
    await scanner.start()

if __name__ == "__main__":
    asyncio.run(main())
