from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
import os
from pathlib import Path

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)

    PROJECT_NAME: str = "Chat Platform"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    DEBUG: bool = True
    # Database
    SQLITE_DB_PATH: str = "sqlite+aiosqlite:///./chat_platform.db"
    SQLALCHEMY_DATABASE_URI: Optional[str] = None

    # JWT
    SECRET_KEY: str = "your-secret-key-here"  # Change in production
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Logging
    LOG_LEVEL: str = "DEBUG"  # Main application log level
    LOG_FILE: str = "logs/app.log"
    SQLALCHEMY_LOG_LEVEL: str = "WARNING"  # SQLAlchemy and aiosqlite log level
    FASTAPI_LOG_LEVEL: str = "INFO"  # FastAPI log level
    UVICORN_LOG_LEVEL: str = "INFO"  # Uvicorn log level

    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60
    RATE_LIMIT_PER_HOUR: int = 1000
    RATE_LIMIT_PER_DAY: int = 10000

    # Security
    ALLOWED_HOSTS: list[str] = ["*"]  # Modify in production
    MAX_REQUEST_SIZE: int = 1024 * 1024  # 1MB
    REQUEST_TIMEOUT: int = 30  # seconds

    # Room Constraints
    MAX_USERS_PER_ROOM: int = 5  # Maximum number of users allowed in a room
    MAX_ROOMS_PER_USER: int = 10   # Maximum number of rooms a user can be in

    # System settings
    SYSTEM_USER_UUID: str = "2d90c5f0-f3ca-4fb4-a726-ac90316635d6"

    # Database settings
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./chat_platform.db")
    DB_ECHO: bool = True

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.SQLALCHEMY_DATABASE_URI:
            self.SQLALCHEMY_DATABASE_URI = self.SQLITE_DB_PATH

    # Create logs directory if it doesn't exist
    @property
    def LOG_DIR(self) -> Path:
        log_dir = Path(self.LOG_FILE).parent
        log_dir.mkdir(parents=True, exist_ok=True)
        return log_dir

settings = Settings() 