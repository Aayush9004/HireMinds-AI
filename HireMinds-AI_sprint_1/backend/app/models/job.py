"""
Job Listing and Job Application database models.
"""
import enum
from datetime import datetime
from typing import Optional, List, TYPE_CHECKING
from sqlalchemy import (
    String,
    Integer,
    Float,
    Text,
    Boolean,
    DateTime,
    ForeignKey,
    JSON,
    Enum,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.resume import Resume


class ApplicationStatus(str, enum.Enum):
    """
    Status lifecycle for candidate job applications.
    """
    APPLIED = "applied"
    UNDER_REVIEW = "under_review"
    SHORTLISTED = "shortlisted"
    ASSESSMENT_PENDING = "assessment_pending"
    INTERVIEW_SCHEDULED = "interview_scheduled"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


class Job(Base):
    """
    Job vacancy created and managed by recruiters.
    """
    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)
    recruiter_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(200), index=True, nullable=False)
    company_name: Mapped[str] = mapped_column(String(200), nullable=False)
    location: Mapped[str] = mapped_column(String(150), default="Remote", nullable=False)
    job_type: Mapped[str] = mapped_column(String(50), default="Full-time", nullable=False)
    description: Mapped[str] = mapped_column(Text(length=4294967295), nullable=False)

    # Requirements
    required_skills: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    preferred_skills: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    min_experience_years: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    required_education: Mapped[str] = mapped_column(String(200), default="Bachelor's Degree", nullable=False)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True, nullable=False)

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
    recruiter: Mapped["User"] = relationship("User", back_populates="posted_jobs")
    applications: Mapped[List["JobApplication"]] = relationship(
        "JobApplication",
        back_populates="job",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Job(id={self.id}, title='{self.title}', recruiter_id={self.recruiter_id})>"


class JobApplication(Base):
    """
    Candidate application submitted for a specific job listing.
    """
    __tablename__ = "job_applications"

    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)
    job_id: Mapped[int] = mapped_column(
        ForeignKey("jobs.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    candidate_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    resume_id: Mapped[int] = mapped_column(
        ForeignKey("resumes.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    cover_letter: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[ApplicationStatus] = mapped_column(
        Enum(ApplicationStatus, values_callable=lambda obj: [e.value for e in obj], native_enum=False, length=30),
        default=ApplicationStatus.APPLIED,
        index=True,
        nullable=False,
    )
    recruiter_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

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
    job: Mapped["Job"] = relationship("Job", back_populates="applications")
    candidate: Mapped["User"] = relationship("User", back_populates="job_applications")
    resume: Mapped["Resume"] = relationship("Resume")

    __table_args__ = (
        UniqueConstraint("job_id", "candidate_id", name="uq_job_candidate_application"),
    )

    def __repr__(self) -> str:
        return f"<JobApplication(id={self.id}, job_id={self.job_id}, candidate_id={self.candidate_id}, status='{self.status}')>"
