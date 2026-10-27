"""
Pydantic schemas package
"""
from app.schemas.health import HealthResponse
from app.schemas.user import UserRegister, UserLogin, UserResponse, UserProfileUpdate
from app.schemas.auth import TokenResponse, TokenPayload
from app.schemas.resume import ResumeResponse, ResumeDetailResponse, ResumeCorrectionRequest
from app.schemas.job import (
    JobCreate,
    JobUpdate,
    JobResponse,
    PaginatedJobsResponse,
    JobApplicationCreate,
    JobApplicationStatusUpdate,
    JobApplicationResponse,
    PaginatedApplicationsResponse,
)
from app.schemas.ats import (
    AtsComponentScore,
    AtsBreakdown,
    AtsScoreResponse,
    ComputeAtsRequest,
    RankedCandidate,
    AtsRankingResponse,
    AtsWeightsResponse,
)
from app.schemas.assessment import (
    QuestionOption,
    CodingTestCase,
    AssessmentGenerateRequest,
    AssessmentQuestionPublic,
    AssessmentQuestionAdmin,
    AssessmentResponse,
    AttemptStartResponse,
    AnswerSubmit,
    AttemptSubmitRequest,
    AnswerResult,
    AttemptResultResponse,
    AttemptSummary,
    AssessmentAttemptsResponse,
    AssessmentListResponse,
)

__all__ = [
    "HealthResponse",
    "UserRegister",
    "UserLogin",
    "UserResponse",
    "UserProfileUpdate",
    "TokenResponse",
    "TokenPayload",
    "ResumeResponse",
    "ResumeDetailResponse",
    "ResumeCorrectionRequest",
    "JobCreate",
    "JobUpdate",
    "JobResponse",
    "PaginatedJobsResponse",
    "JobApplicationCreate",
    "JobApplicationStatusUpdate",
    "JobApplicationResponse",
    "PaginatedApplicationsResponse",
    "AtsComponentScore",
    "AtsBreakdown",
    "AtsScoreResponse",
    "ComputeAtsRequest",
    "RankedCandidate",
    "AtsRankingResponse",
    "AtsWeightsResponse",
    "QuestionOption",
    "CodingTestCase",
    "AssessmentGenerateRequest",
    "AssessmentQuestionPublic",
    "AssessmentQuestionAdmin",
    "AssessmentResponse",
    "AttemptStartResponse",
    "AnswerSubmit",
    "AttemptSubmitRequest",
    "AnswerResult",
    "AttemptResultResponse",
    "AttemptSummary",
    "AssessmentAttemptsResponse",
    "AssessmentListResponse",
]
