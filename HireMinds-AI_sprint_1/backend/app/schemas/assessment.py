"""
Pydantic schemas for Phase 8 technical assessments.

Security note
-------------
Candidate-facing schemas never contain ``correct_answer`` or hidden coding test
cases. Recruiter-facing schemas include them for review and grading.
"""
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, ConfigDict

from app.models.assessment import (
    AssessmentStatus,
    AttemptStatus,
    QuestionType,
)


class QuestionOption(BaseModel):
    """One answer option for an MCQ."""

    key: str = Field(..., min_length=1, max_length=10)
    text: str = Field(..., min_length=1, max_length=1000)


class CodingTestCase(BaseModel):
    """One test case for a coding question."""

    input: Any = Field(..., description="Argument list passed to the function, or a single scalar argument")
    expected: Any = Field(..., description="Expected return value")
    hidden: bool = Field(False, description="Hidden test cases are not shown to candidates")


class AssessmentGenerateRequest(BaseModel):
    """Recruiter request to generate a personalized assessment."""

    job_id: int = Field(..., gt=0)
    resume_id: Optional[int] = Field(
        None,
        gt=0,
        description="Optional applicant resume whose skills personalize the assessment",
    )
    mcq_count: int = Field(5, ge=0, le=20)
    coding_count: int = Field(1, ge=0, le=5)
    title: Optional[str] = Field(None, max_length=200)
    duration_minutes: int = Field(60, ge=1, le=240)
    passing_score: float = Field(60.0, ge=0.0, le=100.0)
    difficulty: Optional[str] = Field(
        None,
        description="Optional difficulty hint: easy, medium, hard, or mixed",
    )
    additional_instructions: Optional[str] = Field(
        None,
        max_length=2000,
        description="Optional recruiter guidance for question generation",
    )


class AssessmentQuestionPublic(BaseModel):
    """Candidate-safe question view: no correct answers or hidden tests."""

    id: int
    question_type: QuestionType
    prompt: str
    options: List[QuestionOption] = Field(default_factory=list)
    points: float
    skill_tag: Optional[str] = None
    difficulty: str
    order_index: int

    # Coding-only fields
    language: Optional[str] = None
    function_name: Optional[str] = None
    starter_code: Optional[str] = None
    sample_test_cases: List[CodingTestCase] = Field(
        default_factory=list,
        description="Visible (non-hidden) test cases only",
    )
    time_limit_ms: Optional[int] = None
    memory_limit_mb: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class AssessmentQuestionAdmin(AssessmentQuestionPublic):
    """Recruiter-safe question view including answers and hidden tests."""

    correct_answer: Optional[str] = None
    explanation: Optional[str] = None
    test_cases: List[CodingTestCase] = Field(default_factory=list)


class AssessmentResponse(BaseModel):
    """Full assessment for the recruiter who owns it."""

    id: int
    job_id: int
    created_by_id: int
    title: str
    description: Optional[str] = None
    status: AssessmentStatus
    duration_minutes: int
    passing_score: float
    generation_model: Optional[str] = None
    generation_prompt_version: Optional[str] = None
    question_count: int
    questions: List[AssessmentQuestionAdmin]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AttemptStartResponse(BaseModel):
    """Response returned when a candidate starts an assessment."""

    attempt_id: int
    assessment_id: int
    title: str
    duration_minutes: int
    status: AttemptStatus
    started_at: datetime
    questions: List[AssessmentQuestionPublic]
    instructions: str


class AnswerSubmit(BaseModel):
    """One submitted answer."""

    question_id: int = Field(..., gt=0)
    selected_option: Optional[str] = Field(
        None,
        max_length=255,
        description="Option key for MCQ questions",
    )
    answer_text: Optional[str] = Field(
        None,
        max_length=100_000,
        description="Candidate source code for coding questions",
    )


class AttemptSubmitRequest(BaseModel):
    """Candidate submission for an assessment attempt."""

    answers: List[AnswerSubmit] = Field(default_factory=list)


class AnswerResult(BaseModel):
    """Deterministic evaluation of one answer."""

    question_id: int
    question_type: QuestionType
    selected_option: Optional[str] = None
    is_correct: Optional[bool] = None
    points_awarded: float
    max_points: float
    evaluation_status: str
    details: Dict[str, Any] = Field(default_factory=dict)


class AttemptResultResponse(BaseModel):
    """Result of a submitted attempt."""

    attempt_id: int
    assessment_id: int
    candidate_id: int
    status: AttemptStatus
    score: Optional[float] = Field(None, ge=0.0, le=100.0)
    mcq_score: Optional[float] = Field(None, ge=0.0, le=100.0)
    coding_score: Optional[float] = Field(None, ge=0.0, le=100.0)
    earned_points: Optional[float] = None
    total_points: Optional[float] = None
    evaluated_points: Optional[float] = None
    evaluation_complete: bool
    sandbox_available: bool
    submitted_at: Optional[datetime] = None
    evaluated_at: Optional[datetime] = None
    answers: List[AnswerResult] = Field(default_factory=list)
    limitations: List[str] = Field(default_factory=list)


class AttemptSummary(BaseModel):
    """Recruiter-facing summary of one candidate attempt."""

    attempt_id: int
    candidate_id: int
    candidate_name: Optional[str] = None
    candidate_email: Optional[str] = None
    status: AttemptStatus
    score: Optional[float] = None
    started_at: datetime
    submitted_at: Optional[datetime] = None
    evaluated_at: Optional[datetime] = None


class AssessmentAttemptsResponse(BaseModel):
    """All attempts for one assessment."""

    assessment_id: int
    total: int
    items: List[AttemptSummary]


class AssessmentListResponse(BaseModel):
    """Recruiter's assessments."""

    total: int
    items: List[AssessmentResponse]
