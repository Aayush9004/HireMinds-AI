"""
Pytest integration tests for Database Connectivity, Session Management, and User Model
"""
import uuid
import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from app.core.database import engine, SessionLocal, check_db_connection
from app.models.user import User, UserRole


def test_database_connectivity_helper():
    """
    Test that check_db_connection successfully queries the MySQL database.
    """
    status = check_db_connection()
    assert status["connected"] is True
    assert status["database"] == "hireminds_ai"


def test_database_engine_raw_query():
    """
    Test direct execution of SQL on the SQLAlchemy engine.
    """
    with engine.connect() as conn:
        val = conn.execute(text("SELECT 42")).scalar()
        assert val == 42


def test_user_model_crud_and_roles():
    """
    Test inserting, querying, role assignment, and deleting User records.
    Ensures rollback/cleanup preserves clean state.
    """
    db = SessionLocal()
    unique_suffix = uuid.uuid4().hex[:8]
    candidate_email = f"candidate_{unique_suffix}@example.com"
    recruiter_email = f"recruiter_{unique_suffix}@example.com"

    try:
        # 1. Create candidate user
        candidate = User(
            email=candidate_email,
            hashed_password="secure_hashed_password_mock",
            full_name="Aayush Candidate",
            role=UserRole.CANDIDATE,
        )
        db.add(candidate)

        # 2. Create recruiter user
        recruiter = User(
            email=recruiter_email,
            hashed_password="secure_hashed_password_mock",
            full_name="Jane Recruiter",
            role=UserRole.RECRUITER,
        )
        db.add(recruiter)
        db.commit()

        # 3. Query and verify candidate
        fetched_candidate = db.query(User).filter(User.email == candidate_email).first()
        assert fetched_candidate is not None
        assert fetched_candidate.full_name == "Aayush Candidate"
        assert fetched_candidate.role == UserRole.CANDIDATE
        assert fetched_candidate.is_active is True
        assert fetched_candidate.is_verified is False
        assert fetched_candidate.created_at is not None
        assert fetched_candidate.updated_at is not None

        # 4. Query and verify recruiter
        fetched_recruiter = db.query(User).filter(User.email == recruiter_email).first()
        assert fetched_recruiter is not None
        assert fetched_recruiter.role == UserRole.RECRUITER

        # 5. Test unique email constraint
        duplicate_user = User(
            email=candidate_email,
            hashed_password="another_password",
            full_name="Duplicate User",
            role=UserRole.CANDIDATE,
        )
        db.add(duplicate_user)
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()

    finally:
        # Cleanup created test users
        db.query(User).filter(User.email.in_([candidate_email, recruiter_email])).delete(synchronize_session=False)
        db.commit()
        db.close()
