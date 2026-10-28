"""
Phase 9: AI mock interview models.

A mock interview belongs to one candidate and one job. Questions are generated
from the job requirements and the candidate's skills, then asked one at a time.
Follow-up questions are linked to the question that triggered them.

Evaluation is intentionally separate from ATS scoring: these tables are never
read by ``ats_service`` and never influence match results.
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


class InterviewStatus(str, enum.Enum):
    """Lifecycle of a candidate's mock interview session."""

    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class InterviewSession(Base):
    """One candidate's AI mock interview for a selected job."""

    __tablename__ = "interview_sessions"

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
    resume_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("resumes.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
        comment="Optional resume used to personalize the interview",
    )

    status: Mapped[InterviewStatus] = mapped_column(
        Enum(
            InterviewStatus,
            values_callable=lambda obj: [e.value for e in obj],
            native_enum=False,
            length=20,
        ),
        default=InterviewStatus.IN_PROGRESS,
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    difficulty: Mapped[str] = mapped_column(String(20), default="mixed", nullable=False)
    focus_areas: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)

    target_question_count: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    max_follow_ups: Mapped[int] = mapped_column(Integer, default=3, nullable=False)

    # Provenance only; never store prompts or API keys here.
    generation_model: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    generation_prompt_version: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
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
    job = relationship("Job")
    candidate = relationship("User")
    resume = relationship("Resume")
    questions: Mapped[List["InterviewQuestion"]] = relationship(
        "InterviewQuestion",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="InterviewQuestion.order_index",
    )
    answers: Mapped[List["InterviewAnswer"]] = relationship(
        "InterviewAnswer",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="InterviewAnswer.id",
    )
    evaluation: Mapped[Optional["InterviewEvaluation"]] = relationship(
        "InterviewEvaluation",
        back_populates="session",
        cascade="all, delete-orphan",
        uselist=False,
    )

    def __repr__(self) -> str:
        return (
            f"<InterviewSession(id={self.id}, job_id={self.job_id}, "
            f"candidate_id={self.candidate_id}, status='{self.status}')>"
        )


class InterviewQuestion(Base):
    """One open-ended interview question, initial or contextual follow-up."""

    __tablename__ = "interview_questions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(
        ForeignKey("interview_sessions.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    parent_question_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("interview_questions.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
        comment="Set when this question is a follow-up to an earlier answer",
    )

    order_index: Mapped[int] = mapped_column(Integer, nullable=False)
    is_follow_up: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    skill_tag: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    difficulty: Mapped[str] = mapped_column(String(20), default="medium", nullable=False)
    rationale: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    session: Mapped["InterviewSession"] = relationship(
        "InterviewSession", back_populates="questions"
    )
    answer: Mapped[Optional["InterviewAnswer"]] = relationship(
        "InterviewAnswer",
        back_populates="question",
        cascade="all, delete-orphan",
        uselist=False,
    )

    __table_args__ = (
        UniqueConstraint(
            "session_id",
            "order_index",
            name="uq_interview_question_order",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<InterviewQuestion(id={self.id}, session_id={self.session_id}, "
            f"order={self.order_index}, follow_up={self.is_follow_up})>"
        )


class InterviewAnswer(Base):
    """A candidate's answer plus its rubric-based evaluation."""

    __tablename__ = "interview_answers"

    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(
        ForeignKey("interview_sessions.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    question_id: Mapped[int] = mapped_column(
        ForeignKey("interview_questions.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    answer_text: Mapped[str] = mapped_column(Text, nullable=False)

    # Predefined rubric, each dimension scored 1-5 by the LLM.
    technical_correctness: Mapped[float] = mapped_column(Float, nullable=False)
    relevance: Mapped[float] = mapped_column(Float, nullable=False)
    clarity: Mapped[float] = mapped_column(Float, nullable=False)
    reasoning: Mapped[float] = mapped_column(Float, nullable=False)
    overall_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        comment="0-100 score derived from the four rubric dimensions",
    )
    feedback: Mapped[str] = mapped_column(Text, nullable=False)
    evaluation_details: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

    evaluated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
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
    session: Mapped["InterviewSession"] = relationship(
        "InterviewSession", back_populates="answers"
    )
    question: Mapped["InterviewQuestion"] = relationship(
        "InterviewQuestion", back_populates="answer"
    )

    __table_args__ = (
        UniqueConstraint("question_id", name="uq_interview_answer_question"),
    )

    def __repr__(self) -> str:
        return (
            f"<InterviewAnswer(id={self.id}, session_id={self.session_id}, "
            f"question_id={self.question_id}, overall={self.overall_score})>"
        )


class InterviewEvaluation(Base):
    """Session-level qualitative evaluation and rubric averages."""

    __tablename__ = "interview_evaluations"

    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(
        ForeignKey("interview_sessions.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    overall_score: Mapped[float] = mapped_column(Float, nullable=False)
    technical_correctness: Mapped[float] = mapped_column(Float, nullable=False)
    relevance: Mapped[float] = mapped_column(Float, nullable=False)
    clarity: Mapped[float] = mapped_column(Float, nullable=False)
    reasoning: Mapped[float] = mapped_column(Float, nullable=False)

    overall_summary: Mapped[str] = mapped_column(Text, nullable=False)
    strengths: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    weaknesses: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    improvement_suggestions: Mapped[List[str]] = mapped_column(
        JSON, default=list, nullable=False
    )
    recommended_topics: Mapped[List[str]] = mapped_column(
        JSON, default=list, nullable=False
    )

    disclaimer: Mapped[str] = mapped_column(Text, nullable=False)
    rubric_version: Mapped[str] = mapped_column(String(50), nullable=False)
    generation_model: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    generation_status: Mapped[str] = mapped_column(
        String(20),
        default="llm",
        nullable=False,
        comment="'llm' for model-generated feedback, 'fallback' for deterministic aggregation",
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
    session: Mapped["InterviewSession"] = relationship(
        "InterviewSession", back_populates="evaluation"
    )

    __table_args__ = (
        UniqueConstraint("session_id", name="uq_interview_evaluation_session"),
    )

    def __repr__(self) -> str:
        return (
            f"<InterviewEvaluation(id={self.id}, session_id={self.session_id}, "
            f"overall={self.overall_score}, status='{self.generation_status}')>"
        )
