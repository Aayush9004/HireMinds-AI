"""
Match orchestrator service.

This module ties together TF-IDF, semantic, and skill matching into a single
pipeline. It also handles persistence (reading/writing to MatchResult table).

Blended score formula (rationale):
  The three signals capture different aspects of fit:
    • TF-IDF score      (30%)  – exact keyword overlap
    • Semantic score    (40%)  – conceptual / meaning similarity
    • Skill score       (30%)  – precise skill-level alignment

  These weights can be tuned via environment variables in a future iteration.
  For now they are sensible defaults based on typical ATS system research.
"""
from __future__ import annotations

import logging
from typing import Dict, Any, Optional, List

from sqlalchemy.orm import Session

from app.models.job import Job
from app.models.match import MatchResult
from app.models.resume import Resume
from app.services.tfidf_matcher import compute_tfidf_similarity
from app.services.skill_matcher import compute_skill_match

logger = logging.getLogger(__name__)

# Weight configuration for blended score
TFIDF_WEIGHT = 0.30
SEMANTIC_WEIGHT = 0.40
SKILL_WEIGHT = 0.30


def _build_job_text(job: Job) -> str:
    """
    Concatenate the relevant job fields into a single plain-text document
    suitable for vectorisation.
    """
    parts = [
        job.title,
        job.company_name,
        job.description or "",
        " ".join(job.required_skills or []),
        " ".join(job.preferred_skills or []),
        job.required_education or "",
        f"{job.min_experience_years} years experience",
    ]
    return " ".join(p for p in parts if p)


def compute_match(
    resume: Resume,
    job: Job,
    use_semantic: bool = True,
) -> Dict[str, Any]:
    """
    Run all matching algorithms for a resume–job pair and return a dict with
    all scores and detail data.

    Parameters
    ----------
    resume     : Resume  ORM object with raw_text and extracted_skills.
    job        : Job     ORM object with description and skill fields.
    use_semantic : bool  Whether to run the (slower) semantic algorithm.

    Returns
    -------
    dict with keys matching MatchResult columns + skill_match_details.
    """
    resume_text = resume.raw_text or ""
    job_text = _build_job_text(job)

    # ------------------------------------------------------------------ #
    # 1. TF-IDF score                                                      #
    # ------------------------------------------------------------------ #
    tfidf_score = compute_tfidf_similarity(resume_text, job_text)
    logger.debug("TF-IDF score for resume=%d job=%d: %.4f", resume.id, job.id, tfidf_score)

    # ------------------------------------------------------------------ #
    # 2. Semantic score (optional, slower)                                 #
    # ------------------------------------------------------------------ #
    semantic_score: Optional[float] = None
    if use_semantic:
        try:
            from app.services.semantic_matcher import compute_semantic_similarity  # noqa: WPS433
            semantic_score = compute_semantic_similarity(resume_text, job_text)
            logger.debug(
                "Semantic score for resume=%d job=%d: %.4f",
                resume.id, job.id, semantic_score
            )
        except Exception as exc:
            logger.warning("Semantic scoring failed, skipping: %s", exc)
            semantic_score = None

    # ------------------------------------------------------------------ #
    # 3. Skill matching                                                    #
    # ------------------------------------------------------------------ #
    # Use corrected data if the candidate has reviewed the resume
    skills = resume.extracted_skills or []
    if resume.is_reviewed_by_candidate and resume.candidate_corrected_data:
        corrected = resume.candidate_corrected_data
        if "skills" in corrected and corrected["skills"]:
            skills = corrected["skills"]

    skill_details = compute_skill_match(
        resume_skills=skills,
        required_skills=job.required_skills or [],
        preferred_skills=job.preferred_skills or [],
        resume_raw_text=resume_text,
    )
    skill_score: float = skill_details["skill_match_score"]

    # ------------------------------------------------------------------ #
    # 4. Blended overall score                                             #
    # ------------------------------------------------------------------ #
    if semantic_score is not None:
        algorithm_used = "both"
        overall = (
            TFIDF_WEIGHT * tfidf_score
            + SEMANTIC_WEIGHT * semantic_score
            + SKILL_WEIGHT * skill_score
        )
    else:
        # Redistribute semantic weight to TF-IDF when semantic unavailable
        algorithm_used = "tfidf"
        overall = (
            (TFIDF_WEIGHT + SEMANTIC_WEIGHT) * tfidf_score
            + SKILL_WEIGHT * skill_score
        )

    overall = round(min(1.0, max(0.0, overall)), 4)

    return {
        "tfidf_score": tfidf_score,
        "semantic_score": semantic_score,
        "skill_match_score": skill_score,
        "skill_match_details": skill_details,
        "overall_score": overall,
        "algorithm_used": algorithm_used,
        "resume_text_snapshot": resume_text[:1000],
    }


def upsert_match_result(
    db: Session,
    resume: Resume,
    job: Job,
    match_data: Dict[str, Any],
) -> MatchResult:
    """
    Insert or update the MatchResult row for a resume–job pair.

    SQLAlchemy does not have a generic UPSERT, so we do a SELECT then
    INSERT/UPDATE manually.
    """
    existing = (
        db.query(MatchResult)
        .filter(
            MatchResult.resume_id == resume.id,
            MatchResult.job_id == job.id,
        )
        .first()
    )

    if existing:
        # Update all columns in place
        existing.tfidf_score = match_data["tfidf_score"]
        existing.semantic_score = match_data["semantic_score"]
        existing.skill_match_score = match_data["skill_match_score"]
        existing.skill_match_details = match_data["skill_match_details"]
        existing.overall_score = match_data["overall_score"]
        existing.algorithm_used = match_data["algorithm_used"]
        existing.resume_text_snapshot = match_data["resume_text_snapshot"]
        db.commit()
        db.refresh(existing)
        return existing
    else:
        result = MatchResult(
            resume_id=resume.id,
            job_id=job.id,
            candidate_id=resume.user_id,
            tfidf_score=match_data["tfidf_score"],
            semantic_score=match_data["semantic_score"],
            skill_match_score=match_data["skill_match_score"],
            skill_match_details=match_data["skill_match_details"],
            overall_score=match_data["overall_score"],
            algorithm_used=match_data["algorithm_used"],
            resume_text_snapshot=match_data["resume_text_snapshot"],
        )
        db.add(result)
        db.commit()
        db.refresh(result)
        return result


def get_match_result(
    db: Session,
    resume_id: int,
    job_id: int,
) -> Optional[MatchResult]:
    """Fetch a cached MatchResult row, or None if it does not exist yet."""
    return (
        db.query(MatchResult)
        .filter(
            MatchResult.resume_id == resume_id,
            MatchResult.job_id == job_id,
        )
        .first()
    )


def get_top_matches_for_job(
    db: Session,
    job_id: int,
    limit: int = 20,
) -> List[MatchResult]:
    """
    Return the top N candidates (by overall_score) who have matched
    against a specific job. Used by recruiters to shortlist candidates.
    """
    return (
        db.query(MatchResult)
        .filter(MatchResult.job_id == job_id)
        .order_by(MatchResult.overall_score.desc())
        .limit(limit)
        .all()
    )


def get_top_matches_for_candidate(
    db: Session,
    candidate_id: int,
    resume_id: int,
    limit: int = 20,
) -> List[MatchResult]:
    """
    Return the top N jobs (by overall_score) for a specific candidate+resume.
    Used by candidates to see their best-fit opportunities.
    """
    return (
        db.query(MatchResult)
        .filter(
            MatchResult.candidate_id == candidate_id,
            MatchResult.resume_id == resume_id,
        )
        .order_by(MatchResult.overall_score.desc())
        .limit(limit)
        .all()
    )
