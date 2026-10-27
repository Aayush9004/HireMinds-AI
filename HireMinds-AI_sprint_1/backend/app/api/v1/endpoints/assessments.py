"""
Phase 8 technical assessment endpoints.

Routes
------
POST /assessments/generate                         recruiter generates an assessment
GET  /assessments                                  recruiter lists own assessments
GET  /assessments/{assessment_id}                  recruiter views full assessment
GET  /assessments/{assessment_id}/attempts         recruiter views candidate attempts
POST /assessments/{assessment_id}/start            candidate starts an attempt
POST /assessments/attempts/{attempt_id}/submit     candidate submits answers
GET  /assessments/attempts/{attempt_id}/result     candidate/recruiter views result

Security
--------
* Candidates never receive correct answers or hidden coding test cases.
* Recruiters can access only assessments they created; admins can access all.
* Candidates can access only their own attempts.
* Coding submissions are never executed in this process.
"""
from __future__ import annotations

import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import check_resource_owner, get_current_user, require_candidate, require_recruiter
from app.core.database import get_db
from app.models.assessment import Assessment, AssessmentAttempt
from app.models.job import Job, JobApplication
from app.models.resume import Resume
from app.models.user import User, UserRole
from app.schemas.assessment import (
    AssessmentAttemptsResponse,
    AssessmentGenerateRequest,
    AssessmentListResponse,
    AssessmentResponse,
    AttemptResultResponse,
    AttemptStartResponse,
    AttemptSubmitRequest,
)
from app.services import assessment_service
from app.services.llm_client import (
    LLMAPIError,
    LLMConfigurationError,
    LLMResponseError,
    LLMTimeoutError,
)

router = APIRouter()
logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------- #
# Helpers                                                                      #
# --------------------------------------------------------------------------- #
def _get_assessment_or_404(db: Session, assessment_id: int) -> Assessment:
    assessment = db.query(Assessment).filter(Assessment.id == assessment_id).first()
    if assessment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assessment not found.",
        )
    return assessment


def _get_attempt_or_404(db: Session, attempt_id: int) -> AssessmentAttempt:
    attempt = db.query(AssessmentAttempt).filter(AssessmentAttempt.id == attempt_id).first()
    if attempt is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assessment attempt not found.",
        )
    return attempt


def _get_job_or_404(db: Session, job_id: int) -> Job:
    job = db.query(Job).filter(Job.id == job_id).first()
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found.",
        )
    return job


def _validate_optional_resume(db: Session, job: Job, resume_id: int) -> Resume:
    """
    A recruiter may personalize an assessment with an applicant's resume only.
    This prevents using arbitrary resumes as a skill source.
    """
    resume = db.query(Resume).filter(Resume.id == resume_id).first()
    if resume is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume not found.",
        )
    application = (
        db.query(JobApplication)
        .filter(
            JobApplication.job_id == job.id,
            JobApplication.candidate_id == resume.user_id,
        )
        .first()
    )
    if application is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "The selected resume does not belong to a candidate who applied "
                "to this job."
            ),
        )
    return resume


# --------------------------------------------------------------------------- #
# Generation                                                                   #
# --------------------------------------------------------------------------- #
@router.post(
    "/generate",
    response_model=AssessmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate a personalized technical assessment",
    description=(
        "Uses the configured LLM provider (Gemini or DeepSeek) to generate "
        "validated MCQ and coding questions from the job requirements and, "
        "optionally, an applicant's skills. Invalid LLM output, timeouts and API "
        "failures return explicit errors; no partial assessment is stored."
    ),
)
def generate_assessment(
    request: AssessmentGenerateRequest,
    current_user: User = Depends(require_recruiter),
    db: Session = Depends(get_db),
) -> AssessmentResponse:
    job = _get_job_or_404(db, request.job_id)
    check_resource_owner(resource_owner_id=job.recruiter_id, current_user=current_user)

    resume = (
        _validate_optional_resume(db, job, request.resume_id)
        if request.resume_id is not None
        else None
    )

    try:
        assessment = assessment_service.generate_assessment(
            db=db,
            job=job,
            recruiter=current_user,
            resume=resume,
            mcq_count=request.mcq_count,
            coding_count=request.coding_count,
            title=request.title,
            duration_minutes=request.duration_minutes,
            passing_score=request.passing_score,
            difficulty=request.difficulty,
            additional_instructions=request.additional_instructions,
        )
    except LLMConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except LLMTimeoutError as exc:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=str(exc),
        ) from exc
    except LLMResponseError as exc:
        logger.warning("Invalid LLM assessment response: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Invalid LLM response: {exc}",
        ) from exc
    except LLMAPIError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc
    except assessment_service.AssessmentGenerationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Generated assessment failed validation: {exc}",
        ) from exc

    return AssessmentResponse(**assessment_service.build_assessment_response(assessment))


@router.get(
    "",
    response_model=AssessmentListResponse,
    status_code=status.HTTP_200_OK,
    summary="List recruiter's assessments",
)
def list_assessments(
    current_user: User = Depends(require_recruiter),
    db: Session = Depends(get_db),
) -> AssessmentListResponse:
    query = db.query(Assessment)
    if current_user.role != UserRole.ADMIN:
        query = query.filter(Assessment.created_by_id == current_user.id)
    assessments: List[Assessment] = query.order_by(Assessment.created_at.desc()).all()
    return AssessmentListResponse(
        total=len(assessments),
        items=[
            AssessmentResponse(**assessment_service.build_assessment_response(assessment))
            for assessment in assessments
        ],
    )


# --------------------------------------------------------------------------- #
# Candidate attempt lifecycle                                                  #
# --------------------------------------------------------------------------- #
@router.post(
    "/{assessment_id}/start",
    response_model=AttemptStartResponse,
    status_code=status.HTTP_200_OK,
    summary="Start an assessment attempt",
    description=(
        "Creates an in-progress attempt or resumes an existing one. Candidate-facing "
        "questions omit correct answers and hidden test cases."
    ),
)
def start_assessment(
    assessment_id: int,
    current_user: User = Depends(require_candidate),
    db: Session = Depends(get_db),
) -> AttemptStartResponse:
    assessment = _get_assessment_or_404(db, assessment_id)
    attempt = assessment_service.start_attempt(db, assessment, current_user)
    return AttemptStartResponse(
        **assessment_service.build_attempt_start_response(attempt)
    )


@router.post(
    "/attempts/{attempt_id}/submit",
    response_model=AttemptResultResponse,
    status_code=status.HTTP_200_OK,
    summary="Submit assessment answers",
    description=(
        "Stores answers and evaluates them deterministically. MCQ answers are compared "
        "with stored correct answers. Coding answers are evaluated only by the secure "
        "sandbox; if it is unavailable they are stored but excluded from the score."
    ),
)
def submit_assessment(
    attempt_id: int,
    body: AttemptSubmitRequest,
    current_user: User = Depends(require_candidate),
    db: Session = Depends(get_db),
) -> AttemptResultResponse:
    attempt = _get_attempt_or_404(db, attempt_id)
    assessment_service.authorize_attempt_submit(attempt, current_user)
    attempt = assessment_service.submit_attempt(db, attempt, body.answers)
    return AttemptResultResponse(
        **assessment_service.build_attempt_result_response(attempt)
    )


@router.get(
    "/attempts/{attempt_id}/result",
    response_model=AttemptResultResponse,
    status_code=status.HTTP_200_OK,
    summary="Get an assessment result",
    description=(
        "Candidates can read only their own attempt; recruiters can read attempts "
        "for assessments they created; admins can read all."
    ),
)
def get_attempt_result(
    attempt_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AttemptResultResponse:
    attempt = _get_attempt_or_404(db, attempt_id)
    assessment = attempt.assessment
    assessment_service.authorize_attempt_result(attempt, assessment, current_user)
    include_private = current_user.role in (UserRole.RECRUITER, UserRole.ADMIN)
    return AttemptResultResponse(
        **assessment_service.build_attempt_result_response(
            attempt, include_private_details=include_private
        )
    )


# --------------------------------------------------------------------------- #
# Recruiter review                                                             #
# --------------------------------------------------------------------------- #
@router.get(
    "/{assessment_id}/attempts",
    response_model=AssessmentAttemptsResponse,
    status_code=status.HTTP_200_OK,
    summary="List attempts for an assessment",
)
def list_assessment_attempts(
    assessment_id: int,
    current_user: User = Depends(require_recruiter),
    db: Session = Depends(get_db),
) -> AssessmentAttemptsResponse:
    assessment = _get_assessment_or_404(db, assessment_id)
    assessment_service.authorize_assessment_owner(assessment, current_user)
    attempts = (
        db.query(AssessmentAttempt)
        .filter(AssessmentAttempt.assessment_id == assessment.id)
        .order_by(AssessmentAttempt.started_at.desc())
        .all()
    )
    return AssessmentAttemptsResponse(
        assessment_id=assessment.id,
        total=len(attempts),
        items=[
            assessment_service.build_attempt_summary(attempt)
            for attempt in attempts
        ],
    )


@router.get(
    "/{assessment_id}",
    response_model=AssessmentResponse,
    status_code=status.HTTP_200_OK,
    summary="Get a full assessment",
    description=(
        "Recruiter-only view including correct answers, explanations and hidden test cases."
    ),
)
def get_assessment(
    assessment_id: int,
    current_user: User = Depends(require_recruiter),
    db: Session = Depends(get_db),
) -> AssessmentResponse:
    assessment = _get_assessment_or_404(db, assessment_id)
    assessment_service.authorize_assessment_owner(assessment, current_user)
    return AssessmentResponse(**assessment_service.build_assessment_response(assessment))
