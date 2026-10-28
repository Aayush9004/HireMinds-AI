"""
Pydantic schemas for Phase 10: Reports and Integration.

Provides unified report structures combining Resume Analysis, Job Matching,
ATS Scoring & Evidence, Technical Assessments, Mock Interviews, and
Personalized Improvement Plans.
"""
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class ResumeDiagnosticReport(BaseModel):
    """Diagnostic analysis of candidate's parsed resume."""

    resume_id: int
    candidate_id: int
    candidate_name: str
    filename: str
    is_reviewed_by_candidate: bool
    extracted_skills: List[str] = Field(default_factory=list)
    education_records_count: int
    has_experience_section: bool
    has_projects_section: bool
    word_count: int
    completeness_score: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Deterministic 0-100 completeness rating calculated in Python",
    )
    formatting_recommendations: List[str] = Field(default_factory=list)
    generated_at: datetime


class MatchingReportSection(BaseModel):
    """Summary of lexical, semantic, and skill-level matching."""

    match_id: Optional[int] = None
    tfidf_score: Optional[float] = None
    semantic_score: Optional[float] = None
    skill_score: Optional[float] = None
    blended_score: Optional[float] = None
    matched_skills: List[str] = Field(default_factory=list)
    missing_skills: List[str] = Field(default_factory=list)
    calculated_at: Optional[datetime] = None


class AtsReportSection(BaseModel):
    """Explainable ATS scoring breakdown, weights, rationales, and evidence."""

    ats_score: Optional[float] = None
    confidence: Optional[str] = None
    component_scores: Dict[str, Optional[float]] = Field(default_factory=dict)
    effective_weights: Dict[str, float] = Field(default_factory=dict)
    rationales: Dict[str, str] = Field(default_factory=dict)
    evidence: Dict[str, Any] = Field(default_factory=dict)
    missing_information: Any = Field(default_factory=dict)
    disclaimer: str


class AssessmentReportSection(BaseModel):
    """Technical MCQ and coding assessment attempt results."""

    has_assessment: bool
    assessment_id: Optional[int] = None
    attempt_id: Optional[int] = None
    status: Optional[str] = None
    score: Optional[float] = None
    mcq_score: Optional[float] = None
    coding_score: Optional[float] = None
    passing_score: Optional[float] = None
    passed: Optional[bool] = None
    attempted_at: Optional[datetime] = None


class MockInterviewReportSection(BaseModel):
    """AI mock interview rubric scores, feedback, and study topics."""

    has_interview: bool
    session_id: Optional[int] = None
    status: Optional[str] = None
    overall_score: Optional[float] = None
    technical_correctness: Optional[float] = None
    relevance: Optional[float] = None
    clarity: Optional[float] = None
    reasoning: Optional[float] = None
    strengths: List[str] = Field(default_factory=list)
    weaknesses: List[str] = Field(default_factory=list)
    interview_suggestions: List[str] = Field(default_factory=list)
    recommended_topics: List[str] = Field(default_factory=list)
    disclaimer: str


class PersonalizedImprovementPlan(BaseModel):
    """Actionable improvement roadmap synthesized across all performance signals."""

    composite_readiness_score: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Blended readiness index computed in Python across ATS, Assessment, and Interview",
    )
    readiness_level: str
    priority_skill_gaps: List[str] = Field(default_factory=list)
    resume_action_items: List[str] = Field(default_factory=list)
    technical_focus_areas: List[str] = Field(default_factory=list)
    interview_coaching_points: List[str] = Field(default_factory=list)
    executive_summary: str


class ComprehensiveCandidateJobReport(BaseModel):
    """
    Unified report linking Candidate Resume, Target Job, Matching, ATS,
    Assessment, Mock Interview, and Personalized Improvement Plan.
    """

    candidate_id: int
    candidate_name: str
    candidate_email: str
    job_id: int
    job_title: str
    company_name: str
    application_status: Optional[str] = None
    applied_at: Optional[datetime] = None

    resume_analysis: ResumeDiagnosticReport
    matching: Optional[MatchingReportSection] = None
    ats: Optional[AtsReportSection] = None
    assessment: Optional[AssessmentReportSection] = None
    mock_interview: Optional[MockInterviewReportSection] = None
    improvement_plan: PersonalizedImprovementPlan
    generated_at: datetime
