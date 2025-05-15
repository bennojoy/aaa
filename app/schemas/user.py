from pydantic import BaseModel, Field, validator, EmailStr, constr
from typing import Optional
from datetime import datetime
from app.models.user import UserType, LoginStatus
import re
import uuid

class UserBase(BaseModel):
    """Base user schema with common attributes"""
    phone_number: str
    alias: Optional[str] = None
    user_type: str = "human"
    language: str = "en"

class UserCreate(UserBase):
    """Schema for creating a new user"""
    password: str

    @validator('phone_number')
    def validate_phone_number(cls, v):
        # Basic phone number validation (international format)
        if not re.match(r'^\+[1-9]\d{1,14}$', v):
            raise ValueError('Phone number must be in international format (e.g., +1234567890)')
        return v

class UserLogin(BaseModel):
    """Schema for user login"""
    identifier: str  # Can be phone number or alias
    password: str

class UserResponse(UserBase):
    """Schema for user response"""
    id: uuid.UUID
    is_active: bool
    is_online: bool
    login_status: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    trace_id: Optional[str] = None

    class Config:
        from_attributes = True

class TokenResponse(BaseModel):
    """Schema for token response"""
    access_token: str
    token_type: str
    trace_id: str
    user_id: str

class AliasCheck(BaseModel):
    """Schema for checking alias availability"""
    alias: str

class AliasUpdate(BaseModel):
    """Schema for updating user alias"""
    new_alias: str

class GeneratedAliasResponse(BaseModel):
    """Schema for generated alias response"""
    alias: str
    trace_id: Optional[str] = None 