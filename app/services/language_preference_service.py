from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.language_preference import RoomUserLanguagePreference
from app.schemas.language_preference import LanguagePreferenceUpdate
from fastapi import HTTPException
import uuid

class LanguagePreferenceService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def update_preferences(
        self, 
        user_id: str, 
        room_id: str, 
        preferences: LanguagePreferenceUpdate
    ) -> RoomUserLanguagePreference:
        # Convert string IDs to UUID for validation
        try:
            user_id_uuid = uuid.UUID(user_id)
            room_id_uuid = uuid.UUID(room_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid ID format")
        
        # Check if user is member of room
        # TODO: Add room membership check
        
        stmt = select(RoomUserLanguagePreference).where(
            RoomUserLanguagePreference.user_id == str(user_id_uuid),
            RoomUserLanguagePreference.room_id == str(room_id_uuid)
        )
        result = await self.db.execute(stmt)
        db_preference = result.scalar_one_or_none()

        if db_preference:
            db_preference.outgoing_language = preferences.outgoing_language
            db_preference.incoming_language = preferences.incoming_language
        else:
            db_preference = RoomUserLanguagePreference(
                user_id=str(user_id_uuid),
                room_id=str(room_id_uuid),
                outgoing_language=preferences.outgoing_language,
                incoming_language=preferences.incoming_language
            )
            self.db.add(db_preference)

        await self.db.commit()
        await self.db.refresh(db_preference)
        return db_preference

    async def get_preferences(
        self, 
        user_id: str, 
        room_id: str
    ) -> RoomUserLanguagePreference:
        try:
            user_id_uuid = uuid.UUID(user_id)
            room_id_uuid = uuid.UUID(room_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid ID format")
        
        stmt = select(RoomUserLanguagePreference).where(
            RoomUserLanguagePreference.user_id == str(user_id_uuid),
            RoomUserLanguagePreference.room_id == str(room_id_uuid)
        )
        result = await self.db.execute(stmt)
        preference = result.scalar_one_or_none()

        if not preference:
            raise HTTPException(
                status_code=404,
                detail="Language preferences not found"
            )
        return preference

    async def reset_preferences(
        self, 
        user_id: str, 
        room_id: str
    ) -> dict:
        try:
            user_id_uuid = uuid.UUID(user_id)
            room_id_uuid = uuid.UUID(room_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid ID format")
        
        stmt = select(RoomUserLanguagePreference).where(
            RoomUserLanguagePreference.user_id == str(user_id_uuid),
            RoomUserLanguagePreference.room_id == str(room_id_uuid)
        )
        result = await self.db.execute(stmt)
        preference = result.scalar_one_or_none()

        if preference:
            await self.db.delete(preference)
            await self.db.commit()
        
        return {"message": f"Language preferences reset to default for user {user_id} in room {room_id}"} 