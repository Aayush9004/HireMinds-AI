"""
Phase 7 ATS scoring and candidate ranking endpoints.

Routes
------
GET  /ats/weights                       -> current weights, formula and policy
POST /ats/compute/{resume_id}/{job_id}  -> compute and store an ATS score
GET  /ats/{resume_id}/{job_id}          -> retrieve the stored explanation
GET  /ats/rankings/{job_id}             -> rank applicants for a recruiter's job

Access rules
------------
* Candidates may compute/view scores only for their own resumes.
* Recruiters may compute/view scores for their own job listings and rank their applicants.
* Admins may access everything.
* No endpoint changes application status; scoring never rejects a candidate.
"""
from __future__ import annotations

import logging
import math
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import check_resource_owner, get_current_user, require_recruiter
from app.core.database import get_db
from app.models.job import Job, JobApplication
from app.models.resume import Resume
from app.models.user import User, UserRole
from app.schemas.ats import (
    AtsRankingResponse,
    AtsScoreResponse,
    AtsWeightsResponse,
    ComputeAtsRequest,
    RankedCandidate,
)
from app.services import ats_service, match_service

router = APIRouter()
logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------- #
# Helpers                                                                      #
# --------------------------------------------------------------------------- #
def _get_resume_or_404(db: Session, resume_id: int) -> Resume:
    resume = db.query(Resume).filter(Resume.id == resume_id).first()
    if not resume:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume not found")
    return resume


def _get_job_or_404(db: Session, job_id: int) -> Job:
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return job


def _authorize_pair(resume: Resume, job: Job, current_user: User) -> None:
    """
    Allow the resume owner, the job's recruiter, or an admin.
    """
    if current_user.role == UserRole.ADMIN:
        return
    if current_user.id == resume.user_id:
        return
    if current_user.role == UserRole.RECRUITER and current_user.id == job.recruiter_id:
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=(
            "Access denied. Candidates may access only their own resumes; "
            "recruiters may access scores for their own job listings."
        ),
    )


def _stored_result_or_404(db: Session, resume_id: int, job_id: int):
    result = match_service.get_match_result(db, resume_id, job_id)
    if result is None or not result.ats_breakdown:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                "No ATS score found for this resume-job pair. "
                "POST to /api/v1/ats/compute/{resume_id}/{job_id} first."
            ),
        )
    return result


# --------------------------------------------------------------------------- #
# GET /ats/weights                                                             #
# --------------------------------------------------------------------------- #
@router.get(
    "/weights",
    response_model=AtsWeightsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get current ATS weights and scoring policy",
    description=(
        "Returns the configurable weights, the formula, and the missing-data policy. "
        "The weights are initial assumptions, not validated hiring criteria."
    ),
)
def get_ats_weights() -> AtsWeightsResponse:
    weights = ats_service.get_weights()
    return AtsWeightsResponse(
        weights=weights,
        formula=ats_service.get_formula(weights),
        scoring_version=ats_service.settings.ATS_SCORING_VERSION,
        normalization="Each component is normalised to 0-100; the weighted ATS score is also 0-100.",
        missing_data_policy=ats_service.MISSING_DATA_POLICY,
        disclaimer=ats_service.DISCLAIMER,
        limitations=ats_service.LIMITATIONS,
    )


# --------------------------------------------------------------------------- #
# POST /ats/compute/{resume_id}/{job_id}                                       #
# --------------------------------------------------------------------------- #
@router.post(
    "/compute/{resume_id}/{job_id}",
    response_model=AtsScoreResponse,
    status_code=status.HTTP_200_OK,
    summary="Compute or refresh an explainable ATS score",
    description=(
        "Runs the Phase 6 matching signals plus the Phase 7 ATS rubric, stores the "
        "score and full breakdown, and returns the explanation. Missing components are "
        "excluded and remaining weights are renormalised."
    ),
)
def compute_ats_score(
    resume_id: int,
    job_id: int,
    body: ComputeAtsRequest = ComputeAtsRequest(),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AtsScoreResponse:
    resume = _get_resume_or_404(db, resume_id)
    job = _get_job_or_404(db, job_id)
    _authorize_pair(resume, job, current_user)

    if not resume.raw_text or not resume.raw_text.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Resume has no extracted text. Upload a readable PDF first.",
        )

    logger.info(
        "Computing ATS score: resume=%d job=%d semantic=%s user=%d",
        resume_id, job_id, body.use_semantic, current_user.id,
    )
    result, _ = ats_service.compute_and_store(
        db=db,
        resume=resume,
        job=job,
        use_semantic=body.use_semantic,
    )
    return AtsScoreResponse(**ats_service.build_score_response(result))


# --------------------------------------------------------------------------- #
# GET /ats/rankings/{job_id}                                                   #
# --------------------------------------------------------------------------- #
@router.get(
    "/rankings/{job_id}",
    response_model=AtsRankingResponse,
    status_code=status.HTTP_200_OK,
    summary="Rank applicants for a job using ATS scores",
    description=(
        "Returns a paginated ranking of candidates who applied to the job. Cached scores "
        "are reused; missing scores are computed on demand. Unscored candidates appear last "
        "with rank=null. This endpoint never rejects or changes an application."
    ),
)
def get_job_rankings(
    job_id: int,
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    refresh: bool = Query(False, description="Recompute ATS scores for every applicant"),
    use_semantic: bool = Query(
        True,
        description="Include semantic similarity when computing missing scores",
    ),
    current_user: User = Depends(require_recruiter),
    db: Session = Depends(get_db),
) -> AtsRankingResponse:
    job = _get_job_or_404(db, job_id)
    check_resource_owner(resource_owner_id=job.recruiter_id, current_user=current_user)

    applications: List[JobApplication] = (
        db.query(JobApplication)
        .filter(JobApplication.job_id == job_id)
        .order_by(JobApplication.created_at.asc())
        .all()
    )

    items = []
    for application in applications:
        resume = application.resume
        if resume is None:
            items.append(
                ats_service.build_unscored_ranking_item(
                    application,
                    "The application's resume is no longer available.",
                )
            )
            continue
        try:
            result = ats_service.get_or_compute_for_ranking(
                db=db,
                resume=resume,
                job=job,
                refresh=refresh,
                use_semantic=use_semantic,
            )
            items.append(ats_service.build_ranking_item(application, result))
        except Exception as exc:  # pragma: no cover - defensive path
            logger.exception(
                "ATS ranking failed for application=%s resume=%s job=%s: %s",
                application.id, application.resume_id, job_id, exc,
            )
            items.append(
                ats_service.build_unscored_ranking_item(
                    application,
                    "The ATS score could not be computed for this applicant.",
                )
            )

    ranked = ats_service.rank_candidates(items)
    total = len(ranked)
    total_pages = math.ceil(total / page_size) if total > 0 else 1
    start = (page - 1) * page_size
    end = start + page_size

    return AtsRankingResponse(
        job_id=job.id,
        job_title=job.title,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        weights=ats_service.get_weights(),
        scoring_version=ats_service.settings.ATS_SCORING_VERSION,
        disclaimer=ats_service.DISCLAIMER,
        limitations=ats_service.LIMITATIONS,
        items=[RankedCandidate(**item) for item in ranked[start:end]],
    )


# --------------------------------------------------------------------------- #
# GET /ats/{resume_id}/{job_id}                                                #
# --------------------------------------------------------------------------- #
@router.get(
    "/{resume_id}/{job_id}",
    response_model=AtsScoreResponse,
    status_code=status.HTTP_200_OK,
    summary="Get a stored ATS score and its explanation",
    description=(
        "Returns the stored score, component scores, weights, rationales, evidence, "
        "missing-information notes and limitations."
    ),
)
def get_ats_score(
    resume_id: int,
    job_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AtsScoreResponse:
    resume = _get_resume_or_404(db, resume_id)
    job = _get_job_or_404(db, job_id)
    _authorize_pair(resume, job, current_user)

    result = _stored_result_or_404(db, resume_id, job_id)
    return AtsScoreResponse(**ats_service.build_score_response(result))
