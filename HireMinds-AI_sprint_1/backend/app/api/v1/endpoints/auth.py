"""
Authentication and User Management endpoints for HireMinds AI
Supports candidate/recruiter registration, login, profile inspection, and RBAC demonstration.
"""
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.database import get_db
from app.core.security import get_password_hash, verify_password, create_access_token
from app.api.deps import (
    get_current_user,
    require_candidate,
    require_recruiter,
    check_resource_owner,
)
from app.models.user import User, UserRole
from app.schemas.user import UserRegister, UserLogin, UserResponse
from app.schemas.auth import TokenResponse

router = APIRouter()


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new Candidate or Recruiter",
    description="Registers a new user account. Validates email uniqueness and hashes password with Argon2id.",
)
def register(
    user_in: UserRegister,
    db: Session = Depends(get_db),
) -> User:
    # Check if email is already taken
    existing_user = db.query(User).filter(User.email == user_in.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )

    # Disallow self-registration as ADMIN for security
    if user_in.role == UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Admin accounts cannot be self-registered.",
        )

    # Hash password with Argon2
    hashed_pwd = get_password_hash(user_in.password)

    # Create user entity
    new_user = User(
        email=user_in.email,
        hashed_password=hashed_pwd,
        full_name=user_in.full_name,
        role=user_in.role,
        is_active=True,
        is_verified=False,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="User Login",
    description="Authenticates user using email and password, returning a signed JWT access token.",
)
def login(
    login_data: UserLogin,
    db: Session = Depends(get_db),
) -> TokenResponse:
    user = db.query(User).filter(User.email == login_data.email).first()
    if not user or not verify_password(login_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive. Please contact support.",
        )

    access_token = create_access_token(
        subject=user.email,
        role=user.role.value,
        user_id=user.id,
    )

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserResponse.model_validate(user),
    )


@router.post(
    "/login/oauth",
    response_model=TokenResponse,
    include_in_schema=True,
    summary="OAuth2 compatible Login for Swagger UI",
)
def login_oauth(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
) -> TokenResponse:
    """
    Standard OAuth2 password form handler for interactive Swagger UI authentication.
    """
    return login(UserLogin(email=form_data.username, password=form_data.password), db=db)


@router.get(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Current User Profile",
    description="Returns the profile details of the currently authenticated user.",
)
def read_current_user_profile(
    current_user: User = Depends(get_current_user),
) -> User:
    return current_user


@router.get(
    "/candidate/profile",
    status_code=status.HTTP_200_OK,
    summary="Candidate Protected Route",
    description="Protected route accessible only by users with the Candidate or Admin role.",
)
def get_candidate_dashboard_info(
    current_user: User = Depends(require_candidate),
) -> dict:
    return {
        "message": f"Welcome to candidate portal, {current_user.full_name}",
        "role": current_user.role.value,
        "email": current_user.email,
    }


@router.get(
    "/recruiter/profile",
    status_code=status.HTTP_200_OK,
    summary="Recruiter Protected Route",
    description="Protected route accessible only by users with the Recruiter or Admin role.",
)
def get_recruiter_dashboard_info(
    current_user: User = Depends(require_recruiter),
) -> dict:
    return {
        "message": f"Welcome to recruiter portal, {current_user.full_name}",
        "role": current_user.role.value,
        "email": current_user.email,
    }


@router.get(
    "/users/{user_id}/private-data",
    status_code=status.HTTP_200_OK,
    summary="Access Private User Resource",
    description="Demonstrates strict ownership check: users can only access their own private data.",
)
def get_private_user_resource(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    # Enforce resource ownership
    check_resource_owner(resource_owner_id=user_id, current_user=current_user)

    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return {
        "user_id": target_user.id,
        "email": target_user.email,
        "full_name": target_user.full_name,
        "private_data": "CONFIDENTIAL: Only authorized owner or admin can read this.",
    }
