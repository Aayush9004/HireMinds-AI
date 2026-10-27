"""
MatchResult database model for storing resume-job matching scores.

Why store results?
------------------
Matching is computationally expensive (especially Sentence Transformers).
Caching the result lets recruiters and candidates query results instantly
on subsequent requests without re-running the algorithm.
"""
from datetime import datetime
from typing import Optional, Dict, Any

from sqlalchemy import (
    Integer,
    Float,
    Text,
    DateTime,
    ForeignKey,
    JSON,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if False:  # TYPE_CHECKING
    from app.models.user import User
    from app.models.resume import Resume
    from app.models.job import Job


class MatchResult(Base):
    """
    Cached matching result between one resume and one job listing.

    Stores scores from both algorithms so users can compare them side-by-side
    without paying the computation cost on every request.
    """
    __tablename__ = "match_results"

    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)

    resume_id: Mapped[int] = mapped_column(
        ForeignKey("resumes.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
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

    # -----------------------------------------------------------
    # Algorithm scores (0.0 – 1.0 scale; higher = better match)
    # -----------------------------------------------------------
    tfidf_score: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True,
        comment="Cosine similarity score from TF-IDF algorithm"
    )
    semantic_score: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True,
        comment="Cosine similarity score from Sentence Transformer embeddings"
    )

    # -----------------------------------------------------------
    # Skill matching breakdown
    # -----------------------------------------------------------
    # The full skill-comparison detail (matched / missing / preferred)
    skill_match_details: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON, nullable=True,
        comment="Detailed skill-level matching: matched, missing, preferred"
    )

    # A simple 0-1 ratio: matched_required_skills / total_required_skills
    skill_match_score: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True,
        comment="Fraction of required job skills found in the resume"
    )

    # -----------------------------------------------------------
    # Blended / overall score for quick ranking
    # -----------------------------------------------------------
    overall_score: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True, index=True,
        comment="Weighted blend of all scores for ranking"
    )

    # Which algorithm(s) were used to produce this result
    algorithm_used: Mapped[str] = mapped_column(
        String(50), default="tfidf", nullable=False,
        comment="'tfidf', 'semantic', or 'both'"
    )

    # Raw text snapshots used during computation (useful for debugging)
    resume_text_snapshot: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True,
        comment="First 1000 characters of resume text at match time"
    )

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
    resume = relationship("Resume")
    job = relationship("Job")
    candidate = relationship("User")

    __table_args__ = (
        UniqueConstraint(
            "resume_id", "job_id",
            name="uq_resume_job_match"
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<MatchResult(id={self.id}, resume_id={self.resume_id}, "
            f"job_id={self.job_id}, overall={self.overall_score:.3f})>"
        )
