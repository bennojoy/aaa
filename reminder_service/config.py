from pydantic_settings import BaseSettings
from typing import Optional
import logging
import json
from app.core.config import settings as app_settings

class Settings(BaseSettings):
    # Database settings
    SQLITE_DB_PATH: str = "sqlite+aiosqlite:///./chat_platform.db"
    SQLALCHEMY_DATABASE_URI: Optional[str] = None
    DB_ECHO: bool = False
    
    # Kafka settings
    KAFKA_BOOTSTRAP_SERVERS: str = "localhost:29092"
    KAFKA_TOPIC: str = "messages.ToUser"
    
    # Scanner settings
    SCAN_INTERVAL_SECONDS: int = 60
    BATCH_SIZE: int = 100
    
    # System settings
    SYSTEM_USER_UUID: str = app_settings.SYSTEM_USER_UUID
    
    # Logging
    LOG_LEVEL: str = "INFO"
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Set default database URI if not provided
        if not self.SQLALCHEMY_DATABASE_URI:
            self.SQLALCHEMY_DATABASE_URI = self.SQLITE_DB_PATH

# Initialize settings
settings = Settings()

# Configure logging
class JSONFormatter(logging.Formatter):
    def format(self, record):
        if isinstance(record.msg, dict):
            return json.dumps(record.msg)
        return json.dumps({"event": record.msg})

logger = logging.getLogger("reminder_scanner")
logger.setLevel(getattr(logging, settings.LOG_LEVEL))
handler = logging.StreamHandler()
handler.setFormatter(JSONFormatter())
logger.addHandler(handler)
