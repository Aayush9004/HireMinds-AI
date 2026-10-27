"""
Pydantic schemas for Resume-Job Matching API responses.

Why separate schemas from models?
----------------------------------
SQLAlchemy models are the database layer – they define tables and columns.
Pydantic schemas are the API layer – they define what JSON looks like.

Keeping them separate means:
  • We can include computed fields in the response without storing them in DB
  • We can hide sensitive DB columns from the API response
  • We can have different shapes for requests vs responses
"""
from __future__ import annotations

from datetime import datetime
from typing import Dict, Any, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class SkillMatchDetails(BaseModel):
    """
    Breakdown of skill-level matching between a resume and a job.
    """
    skill_match_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Fraction of required job skills found in the resume (0–1)",
    )
    matched_required: List[str] = Field(
        default_factory=list,
        description="Required job skills found in the resume",
    )
    missing_required: List[str] = Field(
        default_factory=list,
        description="Required job skills NOT found in the resume",
    )
    matched_preferred: List[str] = Field(
        default_factory=list,
        description="Preferred/nice-to-have skills found in the resume",
    )
    missing_preferred: List[str] = Field(
        default_factory=list,
        description="Preferred skills NOT found in the resume",
    )
    evidence: Dict[str, str] = Field(
        default_factory=dict,
        description="Resume sentences that mention matched skills",
    )
    total_required: int
    total_preferred: int
    total_resume_skills: int


class MatchResultResponse(BaseModel):
    """
    Full match result for a resume–job pair, returned by POST /matching/compute.
    """
    id: int
    resume_id: int
    job_id: int
    candidate_id: int

    tfidf_score: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="TF-IDF cosine similarity (0–1)",
    )
    semantic_score: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Sentence Transformer cosine similarity (0–1)",
    )
    skill_match_score: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Fraction of required skills matched (0–1)",
    )
    overall_score: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Weighted blend of all algorithm scores",
    )
    algorithm_used: str = Field(
        ...,
        description="Algorithm(s) used: 'tfidf', 'semantic', or 'both'",
    )
    skill_match_details: Optional[SkillMatchDetails] = None

    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MatchResultSummary(BaseModel):
    """
    Lightweight match result for list views (no skill detail).
    """
    id: int
    resume_id: int
    job_id: int
    candidate_id: int
    tfidf_score: Optional[float] = None
    semantic_score: Optional[float] = None
    skill_match_score: Optional[float] = None
    overall_score: Optional[float] = None
    algorithm_used: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ComputeMatchRequest(BaseModel):
    """
    Request body for POST /matching/compute.
    Candidates can choose whether to run the slower semantic algorithm.
    """
    use_semantic: bool = Field(
        True,
        description="Include Sentence Transformer semantic scoring (slower but more accurate)",
    )


class AlgorithmComparisonResponse(BaseModel):
    """
    Side-by-side comparison of TF-IDF and semantic scores for evaluation.
    Returned by GET /matching/compare/{resume_id}/{job_id}.
    """
    resume_id: int
    job_id: int

    tfidf_score: float
    semantic_score: Optional[float] = None
    skill_match_score: float
    overall_score: float

    tfidf_interpretation: str
    semantic_interpretation: Optional[str] = None
    skill_interpretation: str
    overall_interpretation: str

    algorithm_comparison: Dict[str, Any]


def _interpret_score(score: float, label: str) -> str:
    """Return a human-readable interpretation of a similarity score."""
    if score >= 0.8:
        return f"{label}: Excellent match ({score:.0%})"
    elif score >= 0.6:
        return f"{label}: Good match ({score:.0%})"
    elif score >= 0.4:
        return f"{label}: Moderate match ({score:.0%})"
    elif score >= 0.2:
        return f"{label}: Weak match ({score:.0%})"
    else:
        return f"{label}: Poor match ({score:.0%})"
