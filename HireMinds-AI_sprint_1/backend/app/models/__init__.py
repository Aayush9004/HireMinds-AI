"""
Database models package
Exports Base and all models for discovery by Alembic and FastAPI.
"""
from app.core.database import Base
from app.models.user import User, UserRole
from app.models.resume import Resume
from app.models.job import Job, JobApplication, ApplicationStatus
from app.models.match import MatchResult

__all__ = [
    "Base",
    "User",
    "UserRole",
    "Resume",
    "Job",
    "JobApplication",
    "ApplicationStatus",
    "MatchResult",
]
