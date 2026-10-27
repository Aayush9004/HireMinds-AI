"""
FastAPI dependencies for Authentication, User resolution, and Role-Based Access Control (RBAC).
"""
from typing import List, Generator
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.user import User, UserRole

# OAuth2 scheme configured for OpenAPI docs authentication UI
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login/oauth"
)


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """
    Decodes the JWT token and fetches the corresponding authenticated user from the database.
    Raises HTTP 401 if token is expired, invalid, or user does not exist.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials or session has expired",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception

    email: str = payload.get("sub")
    user_id: int = payload.get("user_id")
    if email is None or user_id is None:
        raise credentials_exception

    user = db.query(User).filter(User.id == user_id, User.email == email).first()
    if user is None:
        raise credentials_exception

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user account",
        )

    return user


class RoleChecker:
    """
    Enforces Role-Based Access Control (RBAC).
    Permits access only if current user's role is in the allowed_roles list.
    """
    def __init__(self, allowed_roles: List[UserRole]):
        self.allowed_roles = allowed_roles

    def __call__(self, current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation not permitted. Required role: {[r.value for r in self.allowed_roles]}",
            )
        return current_user


# Role dependency helpers
require_candidate = RoleChecker([UserRole.CANDIDATE, UserRole.ADMIN])
require_recruiter = RoleChecker([UserRole.RECRUITER, UserRole.ADMIN])
require_admin = RoleChecker([UserRole.ADMIN])


def check_resource_owner(resource_owner_id: int, current_user: User) -> None:
    """
    Verify that the authenticated user owns the resource, or is an administrator.
    Prevents horizontal privilege escalation.
    """
    if current_user.id != resource_owner_id and current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You do not have permission to access another user's private data.",
        )
