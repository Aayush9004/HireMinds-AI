"""
Phase 9: AI Mock Interview API endpoints.

Routes
------
POST /interviews/start                            Candidate starts or resumes an interview
GET  /interviews/                                 Candidate/Recruiter lists sessions
GET  /interviews/{session_id}                     Views full session details
GET  /interviews/{session_id}/current-question    Gets current unanswered question
POST /interviews/{session_id}/questions/{question_id}/answer  Candidate submits an answer
POST /interviews/{session_id}/complete            Candidate finalizes session
GET  /interviews/{session_id}/evaluation          Retrieves session evaluation report

Security & Authorization
------------------------
* Candidates can start, answer, and view their own mock interviews.
* Recruiters can view interviews of candidates for jobs they own.
* Admins can view and manage all sessions.
* Evaluations are strictly separated from ATS scoring and matching tables.
"""
from __future__ import annotations

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_candidate
from app.core.database import get_db
from app.models.interview import (
    InterviewAnswer,
    InterviewEvaluation,
    InterviewQuestion,
    InterviewSession,
    InterviewStatus,
)
from app.models.job import Job
from app.models.user import User, UserRole
from app.schemas.interview import (
    InterviewAnswerResponse,
    InterviewAnswerSubmitRequest,
    InterviewAnswerSubmitResult,
    InterviewCurrentQuestionResponse,
    InterviewEvaluationResponse,
    InterviewQuestionPublic,
    InterviewSessionListResponse,
    InterviewSessionResponse,
    InterviewStartRequest,
)
from app.services import interview_service
from app.services.llm_client import (
    LLMAPIError,
    LLMConfigurationError,
    LLMResponseError,
    LLMTimeoutError,
)

router = APIRouter()
logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------- #
# Authorization Helpers                                                        #
# --------------------------------------------------------------------------- #

def _get_session_or_404(db: Session, session_id: int) -> InterviewSession:
    session = db.query(InterviewSession).filter(InterviewSession.id == session_id).first()
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Interview session not found.",
        )
    return session


def _get_question_or_404(db: Session, question_id: int) -> InterviewQuestion:
    question = db.query(InterviewQuestion).filter(InterviewQuestion.id == question_id).first()
    if question is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Interview question not found.",
        )
    return question


def _assert_can_view_session(session: InterviewSession, current_user: User) -> None:
    if current_user.role == UserRole.ADMIN:
        return
    if current_user.id == session.candidate_id:
        return
    if current_user.role == UserRole.RECRUITER and session.job and session.job.recruiter_id == current_user.id:
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="You do not have permission to view this interview session.",
    )


def _format_session_response(session: InterviewSession) -> InterviewSessionResponse:
    current_q = interview_service.get_current_unanswered_question(session)
    return InterviewSessionResponse(
        id=session.id,
        job_id=session.job_id,
        candidate_id=session.candidate_id,
        resume_id=session.resume_id,
        status=session.status,
        title=session.title,
        description=session.description,
        difficulty=session.difficulty,
        focus_areas=session.focus_areas or [],
        target_question_count=session.target_question_count,
        max_follow_ups=session.max_follow_ups,
        generation_model=session.generation_model,
        generation_prompt_version=session.generation_prompt_version,
        started_at=session.started_at,
        completed_at=session.completed_at,
        created_at=session.created_at,
        updated_at=session.updated_at,
        questions=[InterviewQuestionPublic.model_validate(q) for q in session.questions],
        answers=[InterviewAnswerResponse.model_validate(a) for a in session.answers],
        evaluation=InterviewEvaluationResponse.model_validate(session.evaluation) if session.evaluation else None,
        current_question=InterviewQuestionPublic.model_validate(current_q) if current_q else None,
    )


# --------------------------------------------------------------------------- #
# Endpoints                                                                    #
# --------------------------------------------------------------------------- #

@router.post(
    "/start",
    response_model=InterviewSessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Start or resume an AI mock interview",
    description="Initializes a new mock interview session or returns the active session if one is in progress.",
)
def start_or_resume_interview(
    request: InterviewStartRequest,
    current_user: User = Depends(require_candidate),
    db: Session = Depends(get_db),
):
    try:
        session, _, _ = interview_service.start_or_resume_interview_session(
            db=db,
            candidate=current_user,
            request=request,
        )
        return _format_session_response(session)
    except LLMConfigurationError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))
    except LLMTimeoutError as exc:
        raise HTTPException(status_code=status.HTTP_504_GATEWAY_TIMEOUT, detail=str(exc))
    except (LLMAPIError, LLMResponseError) as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))


@router.get(
    "/",
    response_model=InterviewSessionListResponse,
    summary="List mock interview sessions",
    description="Candidates see their own sessions. Recruiters can view sessions for their posted jobs.",
)
@router.get(
    "",
    response_model=InterviewSessionListResponse,
    include_in_schema=False,
)
def list_interviews(
    job_id: Optional[int] = Query(None, description="Filter by job ID"),
    session_status: Optional[InterviewStatus] = Query(None, alias="status", description="Filter by status"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(InterviewSession)

    if current_user.role == UserRole.CANDIDATE:
        query = query.filter(InterviewSession.candidate_id == current_user.id)
    elif current_user.role == UserRole.RECRUITER:
        # Join jobs to ensure recruiter only sees sessions for their jobs
        query = query.join(Job).filter(Job.recruiter_id == current_user.id)

    if job_id is not None:
        query = query.filter(InterviewSession.job_id == job_id)
    if session_status is not None:
        query = query.filter(InterviewSession.status == session_status)

    sessions = query.order_by(InterviewSession.created_at.desc()).all()
    items = [_format_session_response(s) for s in sessions]
    return InterviewSessionListResponse(items=items, total=len(items))


@router.get(
    "/{session_id}",
    response_model=InterviewSessionResponse,
    summary="Get interview session details",
    description="Retrieves the session with questions, answers, and evaluation.",
)
def get_interview_session(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session = _get_session_or_404(db, session_id)
    _assert_can_view_session(session, current_user)
    return _format_session_response(session)


@router.get(
    "/{session_id}/current-question",
    response_model=InterviewCurrentQuestionResponse,
    summary="Get current unanswered question",
    description="Returns the active pending question to answer for this session.",
)
def get_current_question(
    session_id: int,
    current_user: User = Depends(require_candidate),
    db: Session = Depends(get_db),
):
    session = _get_session_or_404(db, session_id)
    _assert_can_view_session(session, current_user)

    current_q = interview_service.get_current_unanswered_question(session)
    answered_count = len(session.answers)
    is_completed = session.status == InterviewStatus.COMPLETED or (
        current_q is None and answered_count >= session.target_question_count
    )

    return InterviewCurrentQuestionResponse(
        session_id=session.id,
        session_status=session.status,
        current_question=InterviewQuestionPublic.model_validate(current_q) if current_q else None,
        answered_count=answered_count,
        target_question_count=session.target_question_count,
        is_completed=is_completed,
    )


@router.post(
    "/{session_id}/questions/{question_id}/answer",
    response_model=InterviewAnswerSubmitResult,
    summary="Submit answer to current question",
    description="Evaluates candidate answer against 4-dimension rubric and delivers next question or completes session.",
)
def submit_answer(
    session_id: int,
    question_id: int,
    payload: InterviewAnswerSubmitRequest,
    current_user: User = Depends(require_candidate),
    db: Session = Depends(get_db),
):
    session = _get_session_or_404(db, session_id)
    question = _get_question_or_404(db, question_id)

    try:
        result = interview_service.submit_interview_answer(
            db=db,
            session=session,
            question=question,
            answer_text=payload.answer_text,
            candidate=current_user,
        )
        return InterviewAnswerSubmitResult(
            answer=InterviewAnswerResponse.model_validate(result["answer"]),
            session_status=result["session_status"],
            has_next_question=result["has_next_question"],
            next_question=InterviewQuestionPublic.model_validate(result["next_question"]) if result["next_question"] else None,
            is_completed=result["is_completed"],
            message=result["message"],
        )
    except LLMConfigurationError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))
    except LLMTimeoutError as exc:
        raise HTTPException(status_code=status.HTTP_504_GATEWAY_TIMEOUT, detail=str(exc))
    except (LLMAPIError, LLMResponseError) as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))


@router.post(
    "/{session_id}/complete",
    response_model=InterviewSessionResponse,
    summary="Complete interview session",
    description="Explicitly completes an active interview session and generates post-interview evaluation.",
)
def complete_interview(
    session_id: int,
    current_user: User = Depends(require_candidate),
    db: Session = Depends(get_db),
):
    session = _get_session_or_404(db, session_id)
    if session.candidate_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only complete your own interview sessions.",
        )

    if session.status != InterviewStatus.COMPLETED:
        interview_service.finalize_interview_session(db, session)

    return _format_session_response(session)


@router.get(
    "/{session_id}/evaluation",
    response_model=InterviewEvaluationResponse,
    summary="Get interview evaluation report",
    description="Retrieves the final session rubric breakdown, strengths, weaknesses, and study recommendations.",
)
def get_interview_evaluation(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session = _get_session_or_404(db, session_id)
    _assert_can_view_session(session, current_user)

    if session.evaluation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evaluation has not been generated for this session yet.",
        )

    return InterviewEvaluationResponse.model_validate(session.evaluation)
