from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.routes import auth, rooms, participants, language_preferences
# from app.api.routes import users
# from app.api.routes import messages
from app.middlewares.trace_id import TraceIDMiddleware
from app.middlewares.rate_limiter import RateLimiter
from app.middlewares.security import SecurityMiddleware
from app.middlewares.auth_rate_limiter import AuthRateLimiter
from app.core.logging import logger
from app.db.session import init_db
import uuid

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    debug=settings.DEBUG
)

# Test log message
logger.info("Application starting up")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Modify in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add security middleware
app.add_middleware(SecurityMiddleware)

# Add rate limiter middleware
app.add_middleware(RateLimiter)

# Add auth-specific rate limiter middleware
app.add_middleware(AuthRateLimiter)

# Add trace ID middleware
app.add_middleware(TraceIDMiddleware)

# Import and include routers
app.include_router(auth.router, prefix=settings.API_V1_STR)
app.include_router(rooms.router, prefix=settings.API_V1_STR)
app.include_router(participants.router, prefix=settings.API_V1_STR)
app.include_router(
    language_preferences.router,
    prefix="/api",
    tags=["language-preferences"]
)
# app.include_router(users.router, prefix=settings.API_V1_STR)
# app.include_router(messages.router, prefix=settings.API_V1_STR)

@app.on_event("startup")
async def startup_event():
    """Initialize application on startup."""
    # Initialize database
    await init_db()
    
    # Log startup
    logger.info(
        "Application started",
        extra={
            "event": "app_startup",
            "app_name": settings.PROJECT_NAME,
            "version": settings.VERSION,
            "debug": settings.DEBUG
        }
    )

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info(
        "Application shutting down",
        extra={
            "event": "app_shutdown",
            "app_name": settings.PROJECT_NAME
        }
    )

@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "app_name": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "status": "running"
    } 