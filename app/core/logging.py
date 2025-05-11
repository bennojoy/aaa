import logging
import sys
import json
from pathlib import Path
from datetime import datetime
from app.core.config import settings
import structlog

print(f"Starting logging configuration... Log file will be at: {settings.LOG_FILE}")

# Create logs directory if it doesn't exist
log_path = Path(settings.LOG_FILE)
log_path.parent.mkdir(parents=True, exist_ok=True)
print(f"Log directory created/verified at: {log_path.parent}")

class JSONFormatter(logging.Formatter):
    def format(self, record):
        # Get all extra fields
        extra_fields = {k: v for k, v in record.__dict__.items() 
                       if k not in ['args', 'asctime', 'created', 'exc_info', 'exc_text', 
                                  'filename', 'funcName', 'id', 'levelname', 'levelno', 
                                  'lineno', 'module', 'msecs', 'message', 'msg', 
                                  'name', 'pathname', 'process', 'processName', 
                                  'relativeCreated', 'stack_info', 'thread', 'threadName']}
        
        # Create log record
        log_record = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "path": record.pathname
        }
        
        # Add extra fields
        log_record.update(extra_fields)
        
        # Add exception info if present
        if record.exc_info:
            log_record["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": self.formatException(record.exc_info)
            }
        
        return json.dumps(log_record)

# Configure root logger
logger = logging.getLogger()
logger.setLevel(getattr(logging, settings.LOG_LEVEL))

# Create formatter
formatter = JSONFormatter()

# Create handlers
file_handler = logging.FileHandler(settings.LOG_FILE)
file_handler.setFormatter(formatter)
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(formatter)

# Add handlers to logger
logger.addHandler(file_handler)
logger.addHandler(console_handler)

print("Root logger configured")

# Configure FastAPI logger
logging.getLogger("fastapi").setLevel(getattr(logging, settings.FASTAPI_LOG_LEVEL))
logging.getLogger("uvicorn").setLevel(getattr(logging, settings.UVICORN_LOG_LEVEL))
logging.getLogger("uvicorn.access").setLevel(getattr(logging, settings.UVICORN_LOG_LEVEL))

# Configure SQLAlchemy and related loggers
sqlalchemy_log_level = getattr(logging, settings.SQLALCHEMY_LOG_LEVEL)
for logger_name in [
    "sqlalchemy.engine",
    "sqlalchemy.pool",
    "sqlalchemy.dialects",
    "sqlalchemy.orm",
    "sqlalchemy.sql",
    "sqlalchemy.pool.impl",
    "sqlalchemy.engine.Engine",
    "sqlalchemy.engine.base",
    "sqlalchemy.engine.default",
    "sqlalchemy.engine.url",
    "sqlalchemy.engine.interfaces",
    "sqlalchemy.engine.result",
    "sqlalchemy.engine.strategies",
    "sqlalchemy.engine.util",
    "sqlalchemy.engine.reflection",
    "sqlalchemy.engine.events",
    "sqlalchemy.engine.logging",
    "sqlalchemy.engine.mock",
    "sqlalchemy.engine.mock.connection",
    "sqlalchemy.engine.mock.cursor",
    "sqlalchemy.engine.mock.dialect",
    "sqlalchemy.engine.mock.engine",
    "sqlalchemy.engine.mock.result",
    "sqlalchemy.engine.mock.row",
    "sqlalchemy.engine.mock.schema",
    "sqlalchemy.engine.mock.transaction",
    "sqlalchemy.engine.mock.util",
    "aiosqlite",
    "aiosqlite.core",
    "aiosqlite.connection",
    "aiosqlite.cursor",
    "aiosqlite.transaction",
    "aiosqlite.util"
]:
    logging.getLogger(logger_name).setLevel(sqlalchemy_log_level)

print("FastAPI, Uvicorn, SQLAlchemy, and aiosqlite loggers configured")

# Get application logger
logger = logging.getLogger("chat_platform")
logger.setLevel(getattr(logging, settings.LOG_LEVEL))
print("Application logger configured")

# Test log messages with different levels
logger.debug("This is a DEBUG message", extra={"trace_id": "test", "event": "test_debug"})
logger.info("This is an INFO message", extra={"trace_id": "test", "event": "test_info"})
logger.warning("This is a WARNING message", extra={"trace_id": "test", "event": "test_warning"})
logger.error("This is an ERROR message", extra={"trace_id": "test", "event": "test_error"})

print("Test log messages sent. Check both console and log file for output.")

# Example usage:
# logger.info("User logged in", extra={"event": "user_login", "user_id": 123})
# logger.error("Database connection failed", extra={"event": "db_connection_error"})

# Configure structlog
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.stdlib.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

# Get a logger instance
logger = structlog.get_logger()

# Example of binding context
def bind_context(**kwargs):
    return logger.bind(**kwargs) 