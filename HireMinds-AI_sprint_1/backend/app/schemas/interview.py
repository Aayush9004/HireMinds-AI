"""
Pydantic schemas for Phase 9 AI Mock Interviews.

Schemas cover session creation, sequential question retrieval, answer submissions
with rubric evaluations, and comprehensive session feedback.
"""
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.interview import InterviewStatus


class InterviewStartRequest(BaseModel):
    """Candidate request to start or resume an AI mock interview."""

    job_id: int = Field(..., gt=0, description="Target job ID for the mock interview")
    resume_id: Optional[int] = Field(
        None,
        gt=0,
        description="Optional candidate resume ID to ground candidate skills",
    )
    title: Optional[str] = Field(
        None,
        max_length=200,
        description="Optional custom title for this mock interview session",
    )
    difficulty: Optional[str] = Field(
        "mixed",
        max_length=20,
        description="Interview difficulty: easy, medium, hard, or mixed",
    )
    focus_areas: Optional[List[str]] = Field(
        default_factory=list,
        description="Optional focus skills or topics (e.g. ['System Design', 'Python'])",
    )
    target_question_count: int = Field(
        5,
        ge=3,
        le=10,
        description="Target number of questions for this session (3-10)",
    )
    max_follow_ups: int = Field(
        3,
        ge=0,
        le=5,
        description="Maximum contextual follow-up questions allowed across this session",
    )


class InterviewQuestionPublic(BaseModel):
    """Candidate-safe view of an interview question."""

    id: int
    session_id: int
    order_index: int
    is_follow_up: bool
    parent_question_id: Optional[int] = None
    prompt: str
    skill_tag: Optional[str] = None
    difficulty: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InterviewAnswerSubmitRequest(BaseModel):
    """Candidate answer submission for an active question."""

    answer_text: str = Field(
        ...,
        min_length=1,
        max_length=10000,
        description="Candidate's technical answer text",
    )


class InterviewAnswerResponse(BaseModel):
    """Evaluated interview answer with 4-dimension rubric feedback."""

    id: int
    session_id: int
    question_id: int
    answer_text: str
    technical_correctness: float = Field(..., ge=1.0, le=5.0)
    relevance: float = Field(..., ge=1.0, le=5.0)
    clarity: float = Field(..., ge=1.0, le=5.0)
    reasoning: float = Field(..., ge=1.0, le=5.0)
    overall_score: float = Field(..., ge=0.0, le=100.0)
    feedback: str
    evaluation_details: Optional[Dict[str, Any]] = None
    evaluated_at: datetime
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InterviewAnswerSubmitResult(BaseModel):
    """Result of submitting an answer, including next steps."""

    answer: InterviewAnswerResponse
    session_status: InterviewStatus
    has_next_question: bool
    next_question: Optional[InterviewQuestionPublic] = None
    is_completed: bool = False
    message: str


class InterviewEvaluationResponse(BaseModel):
    """Session-level evaluation, qualitative strengths/weaknesses, and study advice."""

    id: int
    session_id: int
    overall_score: float
    technical_correctness: float
    relevance: float
    clarity: float
    reasoning: float
    overall_summary: str
    strengths: List[str] = Field(default_factory=list)
    weaknesses: List[str] = Field(default_factory=list)
    improvement_suggestions: List[str] = Field(default_factory=list)
    recommended_topics: List[str] = Field(default_factory=list)
    disclaimer: str
    rubric_version: str
    generation_model: Optional[str] = None
    generation_status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InterviewSessionResponse(BaseModel):
    """Complete representation of an AI mock interview session."""

    id: int
    job_id: int
    candidate_id: int
    resume_id: Optional[int] = None
    status: InterviewStatus
    title: str
    description: Optional[str] = None
    difficulty: str
    focus_areas: List[str] = Field(default_factory=list)
    target_question_count: int
    max_follow_ups: int
    generation_model: Optional[str] = None
    generation_prompt_version: Optional[str] = None
    started_at: datetime
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    questions: List[InterviewQuestionPublic] = Field(default_factory=list)
    answers: List[InterviewAnswerResponse] = Field(default_factory=list)
    evaluation: Optional[InterviewEvaluationResponse] = None
    current_question: Optional[InterviewQuestionPublic] = None

    model_config = ConfigDict(from_attributes=True)


class InterviewSessionListResponse(BaseModel):
    """Paginated or listed interview sessions."""

    items: List[InterviewSessionResponse]
    total: int


class InterviewCurrentQuestionResponse(BaseModel):
    """Status and the current unanswered question for a session."""

    session_id: int
    session_status: InterviewStatus
    current_question: Optional[InterviewQuestionPublic] = None
    answered_count: int
    target_question_count: int
    is_completed: bool
