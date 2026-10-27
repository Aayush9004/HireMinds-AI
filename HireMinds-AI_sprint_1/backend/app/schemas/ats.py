"""
Pydantic schemas for the Phase 7 explainable ATS scoring API.
"""
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, ConfigDict


class AtsComponentScore(BaseModel):
    """One scored component of the ATS formula, with its explanation."""
    key: str
    label: str
    weight: float = Field(..., ge=0.0, le=1.0, description="Configured weight of this component")
    effective_weight: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Weight actually used after renormalisation for missing components",
    )
    score: Optional[float] = Field(
        None,
        ge=0.0,
        le=100.0,
        description="Component score 0-100; null when it could not be assessed",
    )
    weighted_contribution: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="effective_weight * score",
    )
    status: str = Field(
        ...,
        description="scored, partial, insufficient_data, or not_applicable",
    )
    confidence: str = Field(..., description="high, medium, low, or none")
    rationale: str = Field(..., description="Plain-language explanation of this component")
    evidence: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Supporting evidence (matched skills, experience sentences, projects, degrees)",
    )
    missing_information: List[str] = Field(
        default_factory=list,
        description="Information that was missing; never converted into a zero score",
    )
    data_quality: str = Field(
        ...,
        description="candidate_reviewed, auto_extracted_unverified, or model_generated",
    )
    details: Dict[str, Any] = Field(default_factory=dict, description="Structured component details")


class AtsBreakdown(BaseModel):
    """Full explainable breakdown of an ATS score."""
    components: List[AtsComponentScore]
    component_scores: Dict[str, Optional[float]]
    effective_weights: Dict[str, float]
    weight_coverage: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Sum of configured weights of components that could be scored",
    )
    renormalized: bool = Field(
        ...,
        description="True when at least one component was excluded and remaining weights were rescaled",
    )
    missing_information: List[Dict[str, Any]] = Field(default_factory=list)
    unverified_components: List[str] = Field(default_factory=list)
    formula: str
    disclaimer: str
    limitations: List[str]
    scoring_version: str
    computed_at: datetime
    data_verification: str
    status: str
    confidence: str


class AtsScoreResponse(BaseModel):
    """Stored ATS score plus its full explanation."""
    id: int
    resume_id: int
    job_id: int
    candidate_id: int
    ats_score: Optional[float] = Field(
        None,
        ge=0.0,
        le=100.0,
        description="Weighted ATS score 0-100; null when no component could be assessed",
    )
    status: str
    confidence: str
    scoring_version: str
    breakdown: AtsBreakdown
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ComputeAtsRequest(BaseModel):
    """Request body for computing or refreshing an ATS score."""
    use_semantic: bool = Field(
        True,
        description="Include the Sentence Transformer semantic component (slower but part of the default rubric)",
    )


class RankedCandidate(BaseModel):
    """One candidate row in a job ranking."""
    rank: Optional[int] = Field(
        None,
        description="1-based rank among scored candidates; null when no score is available",
    )
    application_id: Optional[int] = None
    candidate_id: int
    candidate_name: Optional[str] = None
    resume_id: int
    ats_score: Optional[float] = Field(None, ge=0.0, le=100.0)
    status: str
    confidence: str
    component_scores: Dict[str, Optional[float]] = Field(default_factory=dict)
    missing_information: List[Dict[str, Any]] = Field(default_factory=list)
    explanation_endpoint: Optional[str] = None


class AtsRankingResponse(BaseModel):
    """Ranked applicants for one job."""
    job_id: int
    job_title: str
    total: int
    page: int
    page_size: int
    total_pages: int
    weights: Dict[str, float]
    scoring_version: str
    disclaimer: str
    limitations: List[str]
    items: List[RankedCandidate]


class AtsWeightsResponse(BaseModel):
    """Public transparency endpoint: current weights and scoring policy."""
    weights: Dict[str, float]
    formula: str
    scoring_version: str
    normalization: str
    missing_data_policy: str
    disclaimer: str
    limitations: List[str]
