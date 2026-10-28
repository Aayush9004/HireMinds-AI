"""
Database models package
Exports Base and all models for discovery by Alembic and FastAPI.
"""
from app.core.database import Base
from app.models.user import User, UserRole
from app.models.resume import Resume
from app.models.job import Job, JobApplication, ApplicationStatus
from app.models.match import MatchResult
from app.models.assessment import (
    Assessment,
    AssessmentQuestion,
    AssessmentAttempt,
    AssessmentAnswer,
    AssessmentStatus,
    QuestionType,
    AttemptStatus,
)
from app.models.interview import (
    InterviewSession,
    InterviewQuestion,
    InterviewAnswer,
    InterviewEvaluation,
    InterviewStatus,
)

__all__ = [
    "Base",
    "User",
    "UserRole",
    "Resume",
    "Job",
    "JobApplication",
    "ApplicationStatus",
    "MatchResult",
    "Assessment",
    "AssessmentQuestion",
    "AssessmentAttempt",
    "AssessmentAnswer",
    "AssessmentStatus",
    "QuestionType",
    "AttemptStatus",
    "InterviewSession",
    "InterviewQuestion",
    "InterviewAnswer",
    "InterviewEvaluation",
    "InterviewStatus",
]
