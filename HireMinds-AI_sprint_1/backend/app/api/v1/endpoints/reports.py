"""
Phase 10: Unified Report endpoints.

Routes
------
GET /reports/resume/{resume_id}                          Candidate resume diagnostic report
GET /reports/candidate/job/{job_id}/resume/{resume_id}   Comprehensive candidate-job report
GET /reports/recruiter/job/{job_id}/candidate/{candidate_id} Recruiter candidate application report

Security & Authorization
------------------------
* Candidates can only access reports for resumes they own.
* Recruiters can only access candidate reports for jobs they own and where candidate applied.
* Admins have full access.
"""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import check_resource_owner, get_current_user, require_candidate, require_recruiter
from app.core.database import get_db
from app.models.job import Job, JobApplication
from app.models.resume import Resume
from app.models.user import User, UserRole
from app.schemas.report import (
    ComprehensiveCandidateJobReport,
    ResumeDiagnosticReport,
)
from app.services import report_service

router = APIRouter()
logger = logging.getLogger(__name__)


def _get_resume_or_404(db: Session, resume_id: int) -> Resume:
    resume = db.query(Resume).filter(Resume.id == resume_id).first()
    if resume is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume not found.",
        )
    return resume


def _get_job_or_404(db: Session, job_id: int) -> Job:
    job = db.query(Job).filter(Job.id == job_id).first()
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found.",
        )
    return job


def _get_user_or_404(db: Session, user_id: int) -> User:
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )
    return user


# --------------------------------------------------------------------------- #
# Endpoints                                                                    #
# --------------------------------------------------------------------------- #

@router.get(
    "/resume/{resume_id}",
    response_model=ResumeDiagnosticReport,
    summary="Get standalone resume diagnostic report",
    description="Returns structural diagnostics, skill inventory, and completeness score for a resume.",
)
def get_resume_diagnostic_report(
    resume_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    resume = _get_resume_or_404(db, resume_id)
    check_resource_owner(resume.user_id, current_user)
    return report_service.build_resume_diagnostic_report(resume, current_user)


@router.get(
    "/candidate/job/{job_id}/resume/{resume_id}",
    response_model=ComprehensiveCandidateJobReport,
    summary="Get comprehensive candidate evaluation report",
    description="Aggregates matching, ATS breakdown, assessment results, mock interview, and personalized improvement plan.",
)
def get_candidate_job_report(
    job_id: int,
    resume_id: int,
    current_user: User = Depends(require_candidate),
    db: Session = Depends(get_db),
):
    resume = _get_resume_or_404(db, resume_id)
    check_resource_owner(resume.user_id, current_user)
    job = _get_job_or_404(db, job_id)

    try:
        return report_service.generate_comprehensive_report(
            db=db,
            job_id=job.id,
            resume_id=resume.id,
            candidate=current_user,
        )
    except Exception as exc:
        logger.error("Failed to compile comprehensive candidate report: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Report compilation failed: {exc}",
        )


@router.get(
    "/recruiter/job/{job_id}/candidate/{candidate_id}",
    response_model=ComprehensiveCandidateJobReport,
    summary="Recruiter views candidate application report",
    description="Recruiter accesses comprehensive report for an applicant to a job they own.",
)
def get_recruiter_candidate_report(
    job_id: int,
    candidate_id: int,
    current_user: User = Depends(require_recruiter),
    db: Session = Depends(get_db),
):
    job = _get_job_or_404(db, job_id)
    if job.recruiter_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to view reports for jobs posted by another recruiter.",
        )

    candidate = _get_user_or_404(db, candidate_id)

    application = (
        db.query(JobApplication)
        .filter(
            JobApplication.job_id == job_id,
            JobApplication.candidate_id == candidate_id,
        )
        .first()
    )

    if application is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidate has not applied to this job listing.",
        )

    resume_id = application.resume_id
    if not resume_id:
        resume = db.query(Resume).filter(Resume.user_id == candidate_id).order_by(Resume.created_at.desc()).first()
        if not resume:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No resume found for this candidate application.",
            )
        resume_id = resume.id

    try:
        return report_service.generate_comprehensive_report(
            db=db,
            job_id=job.id,
            resume_id=resume_id,
            candidate=candidate,
        )
    except Exception as exc:
        logger.error("Failed to compile recruiter candidate report: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Report compilation failed: {exc}",
        )
