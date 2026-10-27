"""
Pydantic schemas for Authentication Tokens and JWT payloads.
"""
from typing import Optional
from pydantic import BaseModel, Field
from app.schemas.user import UserResponse


class TokenResponse(BaseModel):
    """
    Schema returned upon successful authentication.
    """
    access_token: str = Field(..., description="Signed JWT Bearer access token")
    token_type: str = Field("bearer", description="Token type (bearer)")
    expires_in: int = Field(..., description="Access token expiration in seconds")
    user: UserResponse = Field(..., description="Authenticated user details")


class TokenPayload(BaseModel):
    """
    Schema for decoded claims inside the JWT token.
    """
    sub: Optional[str] = None
    user_id: Optional[int] = None
    role: Optional[str] = None
    exp: Optional[int] = None
