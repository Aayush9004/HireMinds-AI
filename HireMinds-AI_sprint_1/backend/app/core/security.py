"""
Security utility module for HireMinds AI
Provides Argon2 password hashing and PyJWT token generation & verification.
"""
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Union
import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, InvalidHashError
from app.core.config import settings

# Initialize Argon2 Password Hasher
# Uses default RFC 9106 recommended parameters: Argon2id with 64MiB memory, 3 iterations, 4 parallelism
pwd_hasher = PasswordHasher()


def get_password_hash(password: str) -> str:
    """
    Generate an Argon2id secure hash for a plaintext password.
    """
    return pwd_hasher.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plaintext password against an Argon2 hash.
    Returns True if matching, False on mismatch or corrupted hash.
    """
    try:
        return pwd_hasher.verify(hashed_password, plain_password)
    except (VerifyMismatchError, InvalidHashError):
        return False


def create_access_token(
    subject: Union[str, Any],
    role: str,
    user_id: int,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    Create a signed JWT access token containing subject (email), user ID, role, and expiration.
    """
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode: Dict[str, Any] = {
        "sub": str(subject),
        "user_id": user_id,
        "role": role,
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    }

    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )
    return encoded_jwt


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Decode and validate a JWT access token.
    Returns the payload dictionary if valid, or None if expired/invalid.
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
        return payload
    except (jwt.PyJWTError, Exception):
        return None
