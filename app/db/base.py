from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import UUID
import uuid

Base = declarative_base()

def generate_uuid():
    """Generate a UUID for new records."""
    return uuid.uuid4() 