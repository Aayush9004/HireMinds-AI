"""
User database model with role-based definitions (Candidate, Recruiter, Admin)
"""
import enum
from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy import String, Boolean, DateTime, Enum, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

if TYPE_CHECKING:
    from app.models.resume import Resume
    from app.models.job import Job, JobApplication


class UserRole(str, enum.Enum):
    """
    Role definitions for HireMinds AI users.
    - CANDIDATE: Job seeker, uploads resumes, takes assessments and mock interviews.
    - RECRUITER: Manages job listings, reviews applications and candidate rankings.
    - ADMIN: System administrator.
    """
    CANDIDATE = "candidate"
    RECRUITER = "recruiter"
    ADMIN = "admin"


class User(Base):
    """
    User entity representing system accounts.
    """
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, values_callable=lambda obj: [e.value for e in obj], native_enum=False, length=20),
        default=UserRole.CANDIDATE,
        nullable=False,
        index=True,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    resumes: Mapped[list["Resume"]] = relationship("Resume", back_populates="user", cascade="all, delete-orphan")
    posted_jobs: Mapped[list["Job"]] = relationship("Job", back_populates="recruiter", cascade="all, delete-orphan")
    job_applications: Mapped[list["JobApplication"]] = relationship("JobApplication", back_populates="candidate", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email='{self.email}', role='{self.role}')>"
