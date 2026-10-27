"""
Pytest test suite for Authentication and Authorization
Tests registration, login, JWT validation, RBAC, expired tokens, and private resource ownership.
"""
import uuid
from datetime import timedelta
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings
from app.core.security import create_access_token
from app.core.database import SessionLocal
from app.models.user import User

client = TestClient(app)


@pytest.fixture(scope="module")
def cleanup_test_users():
    """
    Module-level fixture to clean up all test users created during test runs.
    """
    created_emails = []
    yield created_emails

    # Teardown: delete created test accounts
    db = SessionLocal()
    try:
        if created_emails:
            db.query(User).filter(User.email.in_(created_emails)).delete(synchronize_session=False)
            db.commit()
    finally:
        db.close()


def test_candidate_registration_success(cleanup_test_users):
    """
    Test successful candidate registration.
    """
    unique_email = f"candidate_{uuid.uuid4().hex[:8]}@example.com"
    cleanup_test_users.append(unique_email)

    payload = {
        "email": unique_email,
        "password": "StrongPassword123!",
        "full_name": "Aayush Candidate",
        "role": "candidate",
    }
    response = client.post(f"{settings.API_V1_STR}/auth/register", json=payload)
    assert response.status_code == 201

    data = response.json()
    assert data["email"] == unique_email
    assert data["full_name"] == "Aayush Candidate"
    assert data["role"] == "candidate"
    assert "id" in data
    assert "hashed_password" not in data  # Sensitive fields must never be exposed


def test_recruiter_registration_success(cleanup_test_users):
    """
    Test successful recruiter registration.
    """
    unique_email = f"recruiter_{uuid.uuid4().hex[:8]}@example.com"
    cleanup_test_users.append(unique_email)

    payload = {
        "email": unique_email,
        "password": "StrongPassword123!",
        "full_name": "Sarah Recruiter",
        "role": "recruiter",
    }
    response = client.post(f"{settings.API_V1_STR}/auth/register", json=payload)
    assert response.status_code == 201

    data = response.json()
    assert data["email"] == unique_email
    assert data["role"] == "recruiter"


def test_duplicate_email_registration_fails(cleanup_test_users):
    """
    Test that registering an already registered email returns HTTP 409 Conflict.
    """
    unique_email = f"dup_{uuid.uuid4().hex[:8]}@example.com"
    cleanup_test_users.append(unique_email)

    payload = {
        "email": unique_email,
        "password": "StrongPassword123!",
        "full_name": "First User",
        "role": "candidate",
    }
    res1 = client.post(f"{settings.API_V1_STR}/auth/register", json=payload)
    assert res1.status_code == 201

    # Attempt duplicate registration
    res2 = client.post(f"{settings.API_V1_STR}/auth/register", json=payload)
    assert res2.status_code == 409
    assert "already exists" in res2.json()["detail"]


def test_registration_validation_rules():
    """
    Test validation errors on password length and invalid email formatting.
    """
    # 1. Password too short (< 8 chars)
    res_short_pwd = client.post(
        f"{settings.API_V1_STR}/auth/register",
        json={"email": "valid@example.com", "password": "123", "full_name": "Short Pwd", "role": "candidate"},
    )
    assert res_short_pwd.status_code == 422

    # 2. Invalid email format
    res_invalid_email = client.post(
        f"{settings.API_V1_STR}/auth/register",
        json={"email": "not-an-email", "password": "ValidPassword123!", "full_name": "Bad Email", "role": "candidate"},
    )
    assert res_invalid_email.status_code == 422

    # 3. Disallow self-registration as admin
    res_admin = client.post(
        f"{settings.API_V1_STR}/auth/register",
        json={"email": "admin@example.com", "password": "ValidPassword123!", "full_name": "Fake Admin", "role": "admin"},
    )
    assert res_admin.status_code == 400


def test_login_success_and_invalid_credentials(cleanup_test_users):
    """
    Test user login with valid credentials and rejection of invalid credentials.
    """
    email = f"auth_test_{uuid.uuid4().hex[:8]}@example.com"
    cleanup_test_users.append(email)
    password = "CorrectPassword123!"

    # Register user
    reg_res = client.post(
        f"{settings.API_V1_STR}/auth/register",
        json={"email": email, "password": password, "full_name": "Auth Tester", "role": "candidate"},
    )
    assert reg_res.status_code == 201

    # 1. Login with correct password
    login_res = client.post(
        f"{settings.API_V1_STR}/auth/login",
        json={"email": email, "password": password},
    )
    assert login_res.status_code == 200
    token_data = login_res.json()
    assert "access_token" in token_data
    assert token_data["token_type"] == "bearer"
    assert token_data["user"]["email"] == email

    # 2. Login with wrong password
    bad_pwd_res = client.post(
        f"{settings.API_V1_STR}/auth/login",
        json={"email": email, "password": "WrongPassword!"},
    )
    assert bad_pwd_res.status_code == 401
    assert "Invalid email or password" in bad_pwd_res.json()["detail"]

    # 3. Login with non-existent email
    no_user_res = client.post(
        f"{settings.API_V1_STR}/auth/login",
        json={"email": "nonexistent@example.com", "password": password},
    )
    assert no_user_res.status_code == 401


def test_protected_me_endpoint_and_unauthorized_access(cleanup_test_users):
    """
    Test /auth/me requires valid Bearer token.
    """
    email = f"me_test_{uuid.uuid4().hex[:8]}@example.com"
    cleanup_test_users.append(email)
    password = "Password123!"

    reg = client.post(
        f"{settings.API_V1_STR}/auth/register",
        json={"email": email, "password": password, "full_name": "Me User", "role": "candidate"},
    )
    token = client.post(
        f"{settings.API_V1_STR}/auth/login",
        json={"email": email, "password": password},
    ).json()["access_token"]

    # 1. Access without token -> 401
    unauth_res = client.get(f"{settings.API_V1_STR}/auth/me")
    assert unauth_res.status_code == 401

    # 2. Access with malformed token -> 401
    bad_token_res = client.get(
        f"{settings.API_V1_STR}/auth/me",
        headers={"Authorization": "Bearer not-a-valid-jwt"},
    )
    assert bad_token_res.status_code == 401

    # 3. Access with valid token -> 200
    auth_res = client.get(
        f"{settings.API_V1_STR}/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert auth_res.status_code == 200
    assert auth_res.json()["email"] == email


def test_role_based_access_control(cleanup_test_users):
    """
    Test RBAC: Candidates cannot access recruiter endpoints, and Recruiters cannot access candidate endpoints.
    """
    cand_email = f"cand_rbac_{uuid.uuid4().hex[:8]}@example.com"
    rec_email = f"rec_rbac_{uuid.uuid4().hex[:8]}@example.com"
    cleanup_test_users.extend([cand_email, rec_email])

    # Register Candidate
    client.post(
        f"{settings.API_V1_STR}/auth/register",
        json={"email": cand_email, "password": "Password123!", "full_name": "Cand RBAC", "role": "candidate"},
    )
    cand_token = client.post(
        f"{settings.API_V1_STR}/auth/login",
        json={"email": cand_email, "password": "Password123!"},
    ).json()["access_token"]

    # Register Recruiter
    client.post(
        f"{settings.API_V1_STR}/auth/register",
        json={"email": rec_email, "password": "Password123!", "full_name": "Rec RBAC", "role": "recruiter"},
    )
    rec_token = client.post(
        f"{settings.API_V1_STR}/auth/login",
        json={"email": rec_email, "password": "Password123!"},
    ).json()["access_token"]

    cand_headers = {"Authorization": f"Bearer {cand_token}"}
    rec_headers = {"Authorization": f"Bearer {rec_token}"}

    # Candidate accessing Candidate route -> 200
    assert client.get(f"{settings.API_V1_STR}/auth/candidate/profile", headers=cand_headers).status_code == 200

    # Candidate accessing Recruiter route -> 403 Forbidden
    assert client.get(f"{settings.API_V1_STR}/auth/recruiter/profile", headers=cand_headers).status_code == 403

    # Recruiter accessing Recruiter route -> 200
    assert client.get(f"{settings.API_V1_STR}/auth/recruiter/profile", headers=rec_headers).status_code == 200

    # Recruiter accessing Candidate route -> 403 Forbidden
    assert client.get(f"{settings.API_V1_STR}/auth/candidate/profile", headers=rec_headers).status_code == 403


def test_expired_token_rejection(cleanup_test_users):
    """
    Test that an expired JWT token is rejected with HTTP 401.
    """
    email = f"expired_{uuid.uuid4().hex[:8]}@example.com"
    cleanup_test_users.append(email)

    reg = client.post(
        f"{settings.API_V1_STR}/auth/register",
        json={"email": email, "password": "Password123!", "full_name": "Expired User", "role": "candidate"},
    )
    user_id = reg.json()["id"]

    # Generate token that expired 10 minutes ago
    expired_token = create_access_token(
        subject=email,
        role="candidate",
        user_id=user_id,
        expires_delta=timedelta(minutes=-10),
    )

    response = client.get(
        f"{settings.API_V1_STR}/auth/me",
        headers={"Authorization": f"Bearer {expired_token}"},
    )
    assert response.status_code == 401
    assert "expired" in response.json()["detail"].lower()


def test_private_resource_ownership(cleanup_test_users):
    """
    Test that users cannot access another user's private resources (horizontal privilege separation).
    """
    user1_email = f"user1_{uuid.uuid4().hex[:8]}@example.com"
    user2_email = f"user2_{uuid.uuid4().hex[:8]}@example.com"
    cleanup_test_users.extend([user1_email, user2_email])

    reg1 = client.post(
        f"{settings.API_V1_STR}/auth/register",
        json={"email": user1_email, "password": "Password123!", "full_name": "User One", "role": "candidate"},
    )
    user1_id = reg1.json()["id"]
    token1 = client.post(
        f"{settings.API_V1_STR}/auth/login",
        json={"email": user1_email, "password": "Password123!"},
    ).json()["access_token"]

    reg2 = client.post(
        f"{settings.API_V1_STR}/auth/register",
        json={"email": user2_email, "password": "Password123!", "full_name": "User Two", "role": "candidate"},
    )
    user2_id = reg2.json()["id"]
    token2 = client.post(
        f"{settings.API_V1_STR}/auth/login",
        json={"email": user2_email, "password": "Password123!"},
    ).json()["access_token"]

    headers1 = {"Authorization": f"Bearer {token1}"}

    # 1. User 1 accesses their own private resource -> 200 OK
    res_own = client.get(f"{settings.API_V1_STR}/auth/users/{user1_id}/private-data", headers=headers1)
    assert res_own.status_code == 200
    assert res_own.json()["user_id"] == user1_id

    # 2. User 1 attempts to access User 2's private resource -> 403 Forbidden
    res_other = client.get(f"{settings.API_V1_STR}/auth/users/{user2_id}/private-data", headers=headers1)
    assert res_other.status_code == 403
    assert "Access denied" in res_other.json()["detail"]
