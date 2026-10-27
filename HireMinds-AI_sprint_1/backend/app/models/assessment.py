"""
Phase 8: Technical assessment models.

An assessment belongs to a job and is created by a recruiter. It contains
MCQ and/or coding questions generated from the job requirements and the
candidate's skills.

Attempts belong to candidates. Answers are stored per question so results can
be reproduced and audited. Correct answers and hidden coding tests are never
returned by candidate-facing serializers.
"""
import enum
from datetime import datetime
from typing import Any, Dict, List, Optional

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


class AssessmentStatus(str, enum.Enum):
    """Lifecycle of a technical assessment."""

    ACTIVE = "active"
    ARCHIVED = "archived"


class QuestionType(str, enum.Enum):
    """Supported assessment question types."""

    MCQ = "mcq"
    CODING = "coding"


class AttemptStatus(str, enum.Enum):
    """Lifecycle of a candidate's assessment attempt."""

    IN_PROGRESS = "in_progress"
    SUBMITTED = "submitted"
    EVALUATED = "evaluated"
    PARTIALLY_EVALUATED = "partially_evaluated"


class Assessment(Base):
    """A job-specific technical assessment."""

    __tablename__ = "assessments"

    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)
    job_id: Mapped[int] = mapped_column(
        ForeignKey("jobs.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    created_by_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[AssessmentStatus] = mapped_column(
        Enum(
            AssessmentStatus,
            values_callable=lambda obj: [e.value for e in obj],
            native_enum=False,
            length=20,
        ),
        default=AssessmentStatus.ACTIVE,
        nullable=False,
        index=True,
    )
    duration_minutes: Mapped[int] = mapped_column(Integer, default=60, nullable=False)
    passing_score: Mapped[float] = mapped_column(Float, default=60.0, nullable=False)

    # Provenance of the generated content. Never expose API keys or raw prompts.
    generation_model: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    generation_prompt_version: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

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
    questions: Mapped[List["AssessmentQuestion"]] = relationship(
        "AssessmentQuestion",
        back_populates="assessment",
        cascade="all, delete-orphan",
        order_by="AssessmentQuestion.order_index",
    )
    attempts: Mapped[List["AssessmentAttempt"]] = relationship(
        "AssessmentAttempt",
        back_populates="assessment",
        cascade="all, delete-orphan",
    )
    job = relationship("Job")
    created_by = relationship("User")

    def __repr__(self) -> str:
        return (
            f"<Assessment(id={self.id}, job_id={self.job_id}, "
            f"title='{self.title}', status='{self.status}')>"
        )


class AssessmentQuestion(Base):
    """One MCQ or coding question inside an assessment."""

    __tablename__ = "assessment_questions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)
    assessment_id: Mapped[int] = mapped_column(
        ForeignKey("assessments.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    question_type: Mapped[QuestionType] = mapped_column(
        Enum(
            QuestionType,
            values_callable=lambda obj: [e.value for e in obj],
            native_enum=False,
            length=20,
        ),
        nullable=False,
        index=True,
    )
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    explanation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    skill_tag: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    difficulty: Mapped[str] = mapped_column(String(20), default="medium", nullable=False)
    points: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # MCQ fields
    options: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(
        JSON,
        nullable=True,
        comment="List of {key, text} options; never returned to candidates with the answer",
    )
    correct_answer: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Option key of the correct answer; never exposed to candidates",
    )

    # Coding fields
    language: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    function_name: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    starter_code: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    test_cases: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(
        JSON,
        nullable=True,
        comment="List of {input, expected, hidden}; hidden cases are never exposed",
    )
    time_limit_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    memory_limit_mb: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    assessment: Mapped["Assessment"] = relationship("Assessment", back_populates="questions")
    answers: Mapped[List["AssessmentAnswer"]] = relationship(
        "AssessmentAnswer",
        back_populates="question",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return (
            f"<AssessmentQuestion(id={self.id}, assessment_id={self.assessment_id}, "
            f"type='{self.question_type}', points={self.points})>"
        )


class AssessmentAttempt(Base):
    """A candidate's attempt at one assessment."""

    __tablename__ = "assessment_attempts"

    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)
    assessment_id: Mapped[int] = mapped_column(
        ForeignKey("assessments.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    candidate_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    status: Mapped[AttemptStatus] = mapped_column(
        Enum(
            AttemptStatus,
            values_callable=lambda obj: [e.value for e in obj],
            native_enum=False,
            length=30,
        ),
        default=AttemptStatus.IN_PROGRESS,
        nullable=False,
        index=True,
    )

    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    submitted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    evaluated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    score: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        comment="Deterministic score 0-100 over evaluated questions",
    )
    mcq_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    coding_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    earned_points: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    total_points: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    result_details: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
        comment="Per-question results, score calculation, sandbox status and limitations",
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
    assessment: Mapped["Assessment"] = relationship("Assessment", back_populates="attempts")
    candidate = relationship("User")
    answers: Mapped[List["AssessmentAnswer"]] = relationship(
        "AssessmentAnswer",
        back_populates="attempt",
        cascade="all, delete-orphan",
        order_by="AssessmentAnswer.id",
    )

    __table_args__ = (
        UniqueConstraint(
            "assessment_id",
            "candidate_id",
            name="uq_assessment_candidate_attempt",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<AssessmentAttempt(id={self.id}, assessment_id={self.assessment_id}, "
            f"candidate_id={self.candidate_id}, status='{self.status}')>"
        )


class AssessmentAnswer(Base):
    """A candidate's answer to one question, with deterministic evaluation."""

    __tablename__ = "assessment_answers"

    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)
    attempt_id: Mapped[int] = mapped_column(
        ForeignKey("assessment_attempts.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    question_id: Mapped[int] = mapped_column(
        ForeignKey("assessment_questions.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    selected_option: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    answer_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    is_correct: Mapped[Optional[bool]] = mapped_column(
        Boolean,
        nullable=True,
        comment="True/False for MCQ and evaluated coding; null when not evaluated",
    )
    points_awarded: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    evaluation_details: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

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
    attempt: Mapped["AssessmentAttempt"] = relationship("AssessmentAttempt", back_populates="answers")
    question: Mapped["AssessmentQuestion"] = relationship("AssessmentQuestion", back_populates="answers")

    __table_args__ = (
        UniqueConstraint(
            "attempt_id",
            "question_id",
            name="uq_attempt_question_answer",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<AssessmentAnswer(id={self.id}, attempt_id={self.attempt_id}, "
            f"question_id={self.question_id}, points={self.points_awarded})>"
        )
