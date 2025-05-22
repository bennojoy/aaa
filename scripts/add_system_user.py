import asyncio
import logging
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from app.models.user import User, UserType
from app.core.config import settings
from app.core.security import hash_password

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# System user details
SYSTEM_USER_UUID = "2d90c5f0-f3ca-4fb4-a726-ac90316635d6"
SYSTEM_USER_PHONE = "+1234567890"  # This is a dummy phone number
SYSTEM_USER_ALIAS = "system"  # Using 'system' as alias
SYSTEM_USER_PASSWORD = "system_password"  # This is a dummy password

async def add_system_user():
    """Add system user to the database"""
    try:
        # Create async engine
        engine = create_async_engine(settings.SQLALCHEMY_DATABASE_URI)
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with async_session() as session:
            # Check if system user already exists
            existing_user = await session.get(User, UUID(SYSTEM_USER_UUID))
            if existing_user:
                logger.info("System user already exists in database")
                return

            # Create system user
            system_user = User(
                id=UUID(SYSTEM_USER_UUID),
                phone_number=SYSTEM_USER_PHONE,
                alias=SYSTEM_USER_ALIAS,
                hashed_password=hash_password(SYSTEM_USER_PASSWORD),
                user_type=UserType.SYSTEM,  # Using SYSTEM type for system user
                is_active=True
            )

            session.add(system_user)
            await session.commit()
            logger.info("Successfully added system user to database")

    except Exception as e:
        logger.error(f"Error adding system user: {str(e)}")
        raise

if __name__ == "__main__":
    asyncio.run(add_system_user()) 