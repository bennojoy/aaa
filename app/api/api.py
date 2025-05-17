from fastapi import APIRouter

from app.api.routes import reminders

api_router = APIRouter()

# ... existing routes ...

# Add reminder routes
api_router.include_router(
    reminders.router,
    prefix="/reminders",
    tags=["reminders"]
) 