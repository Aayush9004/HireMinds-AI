"""
Resume-Job Matching API endpoints.

Route design:
  POST   /matching/compute/{resume_id}/{job_id}   → run matching + cache result
  GET    /matching/{resume_id}/{job_id}            → get cached result
  GET    /matching/compare/{resume_id}/{job_id}    → side-by-side algorithm compare
  GET    /matching/top-jobs/{resume_id}            → top matching jobs for a candidate
  GET    /matching/top-candidates/{job_id}         → top matching candidates (recruiter view)

Access rules:
  • Candidates can only view matches involving their own resumes.
  • Recruiters can view top-candidate results for their own job listings.
  • Computing a new match is allowed only by the resume owner (candidate).
"""
from __future__ import annotations

import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import (
    get_current_user,
    require_candidate,
    require_recruiter,
    check_resource_owner,
)
from app.core.database import get_db
from app.models.job import Job
from app.models.match import MatchResult
from app.models.resume import Resume
from app.models.user import User, UserRole
from app.schemas.match import (
    AlgorithmComparisonResponse,
    ComputeMatchRequest,
    MatchResultResponse,
    MatchResultSummary,
    SkillMatchDetails,
    _interpret_score,
)
from app.services import match_service

router = APIRouter()
logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------- #
# Helper: fetch resume, verify ownership                                       #
# --------------------------------------------------------------------------- #
def _get_resume_owned(resume_id: int, current_user: User, db: Session) -> Resume:
    resume = db.query(Resume).filter(Resume.id == resume_id).first()
    if not resume:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume not found")
    check_resource_owner(resume.user_id, current_user)
    return resume


def _get_job_or_404(job_id: int, db: Session) -> Job:
    job = db.query(Job).filter(Job.id == job_id, Job.is_active == True).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found or is no longer active",
        )
    return job


# --------------------------------------------------------------------------- #
# POST /matching/compute/{resume_id}/{job_id}                                  #
# --------------------------------------------------------------------------- #
@router.post(
    "/compute/{resume_id}/{job_id}",
    response_model=MatchResultResponse,
    status_code=status.HTTP_200_OK,
    summary="Compute or refresh match scores between a resume and a job",
    description=(
        "Runs TF-IDF, optionally Sentence Transformer, and skill matching. "
        "Saves (or updates) the result in the database. "
        "Only the resume owner (candidate) may trigger this."
    ),
)
def compute_match(
    resume_id: int,
    job_id: int,
    body: ComputeMatchRequest = ComputeMatchRequest(),
    current_user: User = Depends(require_candidate),
    db: Session = Depends(get_db),
) -> MatchResultResponse:
    resume = _get_resume_owned(resume_id, current_user, db)
    job = _get_job_or_404(job_id, db)

    if not resume.raw_text or not resume.raw_text.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Resume has no extracted text. Please upload a valid PDF first.",
        )

    logger.info(
        "Computing match: resume=%d, job=%d, semantic=%s, user=%d",
        resume_id, job_id, body.use_semantic, current_user.id,
    )

    match_data = match_service.compute_match(
        resume=resume,
        job=job,
        use_semantic=body.use_semantic,
    )

    db_result = match_service.upsert_match_result(db, resume, job, match_data)

    # Build response – we enrich with parsed skill details
    response = _build_match_response(db_result, match_data)
    return response


# --------------------------------------------------------------------------- #
# GET /matching/{resume_id}/{job_id}                                           #
# --------------------------------------------------------------------------- #
@router.get(
    "/{resume_id}/{job_id}",
    response_model=MatchResultResponse,
    summary="Retrieve cached match result",
    description="Returns the previously computed match. Call /compute first if none exists.",
)
def get_match(
    resume_id: int,
    job_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MatchResultResponse:
    # Candidates can only view their own; recruiters can view matches on their jobs
    result = db.query(MatchResult).filter(
        MatchResult.resume_id == resume_id,
        MatchResult.job_id == job_id,
    ).first()

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No match result found. POST to /matching/compute first.",
        )

    # Access control
    if current_user.role == UserRole.CANDIDATE:
        check_resource_owner(result.candidate_id, current_user)
    elif current_user.role == UserRole.RECRUITER:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job or job.recruiter_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only view match results for your own job listings.",
            )

    return _build_match_response(result, result.skill_match_details)


# --------------------------------------------------------------------------- #
# GET /matching/compare/{resume_id}/{job_id}                                   #
# --------------------------------------------------------------------------- #
@router.get(
    "/compare/{resume_id}/{job_id}",
    response_model=AlgorithmComparisonResponse,
    summary="Side-by-side algorithm comparison",
    description="Shows TF-IDF vs semantic scores with human-readable interpretation.",
)
def compare_algorithms(
    resume_id: int,
    job_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AlgorithmComparisonResponse:
    result = db.query(MatchResult).filter(
        MatchResult.resume_id == resume_id,
        MatchResult.job_id == job_id,
    ).first()

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No match result found. POST to /matching/compute first.",
        )

    # Access check
    if current_user.role == UserRole.CANDIDATE:
        check_resource_owner(result.candidate_id, current_user)

    tfidf = result.tfidf_score or 0.0
    semantic = result.semantic_score
    skill = result.skill_match_score or 0.0
    overall = result.overall_score or 0.0

    comparison = {
        "tfidf": {
            "score": tfidf,
            "strength": "Precise keyword matching, fast, no model loading",
            "weakness": "Cannot detect synonyms or paraphrases",
        },
        "semantic": {
            "score": semantic,
            "strength": "Understands meaning, handles synonyms and paraphrases",
            "weakness": "Slower, requires model download, less precise for exact terms",
        } if semantic is not None else None,
        "skill": {
            "score": skill,
            "strength": "Direct, explainable skill-level analysis",
            "weakness": "Depends on quality of skill extraction from resume",
        },
        "recommendation": (
            "Use Semantic + Skill matching for holistic candidate evaluation. "
            "Use TF-IDF as a fast pre-filter when processing large candidate pools."
        ),
    }

    return AlgorithmComparisonResponse(
        resume_id=resume_id,
        job_id=job_id,
        tfidf_score=tfidf,
        semantic_score=semantic,
        skill_match_score=skill,
        overall_score=overall,
        tfidf_interpretation=_interpret_score(tfidf, "TF-IDF"),
        semantic_interpretation=_interpret_score(semantic, "Semantic") if semantic is not None else None,
        skill_interpretation=_interpret_score(skill, "Skill Match"),
        overall_interpretation=_interpret_score(overall, "Overall"),
        algorithm_comparison=comparison,
    )


# --------------------------------------------------------------------------- #
# GET /matching/top-jobs/{resume_id}                                           #
# --------------------------------------------------------------------------- #
@router.get(
    "/top-jobs/{resume_id}",
    response_model=List[MatchResultSummary],
    summary="Top matching jobs for a candidate resume",
)
def top_jobs_for_resume(
    resume_id: int,
    limit: int = Query(default=10, ge=1, le=50),
    current_user: User = Depends(require_candidate),
    db: Session = Depends(get_db),
) -> List[MatchResultSummary]:
    resume = _get_resume_owned(resume_id, current_user, db)
    results = match_service.get_top_matches_for_candidate(
        db=db,
        candidate_id=current_user.id,
        resume_id=resume.id,
        limit=limit,
    )
    return results


# --------------------------------------------------------------------------- #
# GET /matching/top-candidates/{job_id}                                        #
# --------------------------------------------------------------------------- #
@router.get(
    "/top-candidates/{job_id}",
    response_model=List[MatchResultSummary],
    summary="Top matching candidates for a job (recruiter view)",
)
def top_candidates_for_job(
    job_id: int,
    limit: int = Query(default=10, ge=1, le=50),
    current_user: User = Depends(require_recruiter),
    db: Session = Depends(get_db),
) -> List[MatchResultSummary]:
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    if job.recruiter_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view candidates for your own job listings.",
        )

    results = match_service.get_top_matches_for_job(db=db, job_id=job_id, limit=limit)
    return results


# --------------------------------------------------------------------------- #
# Internal: build MatchResultResponse from ORM + raw dict                      #
# --------------------------------------------------------------------------- #
def _build_match_response(
    db_result: MatchResult,
    skill_data,
) -> MatchResultResponse:
    """
    Construct a MatchResultResponse from an ORM object plus optional
    skill_match_details (dict or None).
    """
    skill_details_obj = None
    raw = skill_data if isinstance(skill_data, dict) else getattr(db_result, "skill_match_details", None)

    if raw and isinstance(raw, dict):
        try:
            skill_details_obj = SkillMatchDetails(**raw)
        except Exception:
            skill_details_obj = None

    return MatchResultResponse(
        id=db_result.id,
        resume_id=db_result.resume_id,
        job_id=db_result.job_id,
        candidate_id=db_result.candidate_id,
        tfidf_score=db_result.tfidf_score,
        semantic_score=db_result.semantic_score,
        skill_match_score=db_result.skill_match_score,
        overall_score=db_result.overall_score,
        algorithm_used=db_result.algorithm_used,
        skill_match_details=skill_details_obj,
        created_at=db_result.created_at,
        updated_at=db_result.updated_at,
    )
