"""
Pydantic schemas for User registration, login, and profile representations.
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from app.models.user import UserRole


class UserRegister(BaseModel):
    """
    Schema for candidate and recruiter account registration.
    """
    email: EmailStr = Field(..., description="Valid email address for login")
    password: str = Field(..., min_length=8, max_length=128, description="Secure plaintext password (min 8 chars)")
    full_name: str = Field(..., min_length=2, max_length=150, description="Full legal or professional name")
    role: UserRole = Field(
        default=UserRole.CANDIDATE,
        description="Account role: candidate (default) or recruiter",
    )


class UserLogin(BaseModel):
    """
    Schema for user authentication request.
    """
    email: EmailStr = Field(..., description="Registered account email")
    password: str = Field(..., min_length=1, description="Account password")


class UserResponse(BaseModel):
    """
    Schema for returning user account details (excluding sensitive credentials).
    """
    id: int
    email: EmailStr
    full_name: str
    role: UserRole
    is_active: bool
    is_verified: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserProfileUpdate(BaseModel):
    """
    Schema for updating basic user profile information.
    """
    full_name: Optional[str] = Field(None, min_length=2, max_length=150)
