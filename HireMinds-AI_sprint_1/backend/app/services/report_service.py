"""
Phase 10: Report aggregation and analysis service.

Aggregates data across Resume Parsing, Matching Engine, ATS Scoring,
Technical Assessments, and AI Mock Interviews to generate actionable,
explainable diagnostic reports and personalized candidate improvement plans.

Design rules
------------
* Python is used for all numerical calculations (averages, gaps, indices).
* LLM is used only when natural-language executive summaries are helpful.
* Fallback to deterministic text when LLM is unavailable or unconfigured.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.models.assessment import Assessment, AssessmentAttempt
from app.models.interview import InterviewEvaluation, InterviewSession, InterviewStatus
from app.models.job import Job, JobApplication
from app.models.match import MatchResult
from app.models.resume import Resume
from app.models.user import User
from app.schemas.report import (
    AssessmentReportSection,
    AtsReportSection,
    ComprehensiveCandidateJobReport,
    MatchingReportSection,
    MockInterviewReportSection,
    PersonalizedImprovementPlan,
    ResumeDiagnosticReport,
)
from app.services.ats_service import DISCLAIMER as DISCLAIMER_ATS
from app.services.interview_service import DISCLAIMER_TEXT as DISCLAIMER_INTERVIEW
from app.services.llm_client import BaseLLMClient, get_llm_client

logger = logging.getLogger(__name__)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _candidate_skills(resume: Optional[Resume]) -> List[str]:
    if resume is None:
        return []
    skills = list(getattr(resume, "extracted_skills", None) or [])
    if getattr(resume, "is_reviewed_by_candidate", False):
        corrected = getattr(resume, "candidate_corrected_data", None) or {}
        if isinstance(corrected, dict) and corrected.get("skills"):
            skills = list(corrected["skills"])
    return [str(s).strip() for s in skills if str(s).strip()]


# --------------------------------------------------------------------------- #
# Section Builders                                                            #
# --------------------------------------------------------------------------- #

def build_resume_diagnostic_report(resume: Resume, candidate: User) -> ResumeDiagnosticReport:
    """Build structural diagnostics and completeness score for a resume."""
    text = resume.raw_text or ""
    word_count = len(text.split())
    skills = _candidate_skills(resume)
    edu_records = resume.extracted_education or []
    exp_dict = resume.extracted_experience or {}
    proj_records = resume.extracted_projects or []

    has_exp = bool(exp_dict.get("roles") or exp_dict.get("raw_text") or exp_dict.get("years"))
    has_proj = bool(proj_records)

    # Deterministic Python score calculation:
    score = 0.0
    recs: List[str] = []

    if word_count >= 100:
        score += 20.0
    else:
        recs.append("Resume content is sparse (under 100 words); expand work and project descriptions.")

    if len(skills) >= 5:
        score += 25.0
    elif len(skills) >= 1:
        score += 15.0
        recs.append("Add more specific technical tools, programming languages, and frameworks.")
    else:
        recs.append("No technical skills were detected. Add a dedicated 'Skills' section.")

    if len(edu_records) >= 1:
        score += 20.0
    else:
        recs.append("Include your university degree, institution, and graduation year.")

    if has_exp:
        score += 20.0
    else:
        recs.append("Add professional experience or internships detailing technical contributions.")

    if resume.is_reviewed_by_candidate:
        score += 15.0
    else:
        recs.append("Review and verify your automatically extracted resume metadata.")

    return ResumeDiagnosticReport(
        resume_id=resume.id,
        candidate_id=candidate.id,
        candidate_name=candidate.full_name,
        filename=resume.filename,
        is_reviewed_by_candidate=resume.is_reviewed_by_candidate,
        extracted_skills=skills,
        education_records_count=len(edu_records),
        has_experience_section=has_exp,
        has_projects_section=has_proj,
        word_count=word_count,
        completeness_score=round(score, 2),
        formatting_recommendations=recs,
        generated_at=_now(),
    )


def build_matching_section(
    match: Optional[MatchResult],
    job: Job,
    candidate_skills: List[str],
) -> MatchingReportSection:
    """Extract lexical, semantic, and skill-level matching details."""
    if match is None:
        cand_set = {s.lower() for s in candidate_skills}
        req_set = {s.lower() for s in (job.required_skills or [])}
        missing = [s for s in (job.required_skills or []) if s.lower() not in cand_set]
        matched = [s for s in (job.required_skills or []) if s.lower() in cand_set]
        return MatchingReportSection(
            matched_skills=matched,
            missing_skills=missing,
        )

    details = match.skill_match_details or {}
    matched_skills = list(details.get("matched", []) or getattr(match, "matched_skills", None) or [])
    missing_skills = list(details.get("missing", []) or getattr(match, "missing_skills", None) or [])
    blended = getattr(match, "overall_score", None)
    if blended is None:
        blended = getattr(match, "blended_score", None)

    return MatchingReportSection(
        match_id=match.id,
        tfidf_score=round(match.tfidf_score * 100, 2) if match.tfidf_score is not None else None,
        semantic_score=round(match.semantic_score * 100, 2) if match.semantic_score is not None else None,
        skill_score=round(match.skill_match_score * 100, 2) if match.skill_match_score is not None else None,
        blended_score=round(blended * 100, 2) if blended is not None else None,
        matched_skills=matched_skills,
        missing_skills=missing_skills,
        calculated_at=match.updated_at,
    )


def build_ats_section(match: Optional[MatchResult]) -> Optional[AtsReportSection]:
    """Extract explainable ATS breakdown and rationales."""
    if match is None or match.ats_score is None:
        return None

    explanation = getattr(match, "ats_breakdown", None) or getattr(match, "ats_explanation", None) or {}
    component_scores = explanation.get("component_scores") or {
        "skill": getattr(match, "ats_component_skill", None),
        "experience": getattr(match, "ats_component_experience", None),
        "education": getattr(match, "ats_component_education", None),
        "project": getattr(match, "ats_component_project", None),
        "semantic": getattr(match, "ats_component_semantic", None),
    }

    effective_weights = explanation.get("effective_weights") or {}
    rationales = explanation.get("rationales") or {}
    evidence = explanation.get("evidence") or {}
    missing_info = explanation.get("missing_information") or {}
    disclaimer = explanation.get("disclaimer") or DISCLAIMER_ATS

    return AtsReportSection(
        ats_score=round(match.ats_score, 2),
        confidence=match.ats_confidence,
        component_scores=component_scores,
        effective_weights=effective_weights,
        rationales=rationales,
        evidence=evidence,
        missing_information=missing_info,
        disclaimer=disclaimer,
    )


def build_assessment_section(
    db: Session,
    job_id: int,
    candidate_id: int,
) -> AssessmentReportSection:
    """Retrieve technical assessment attempt results for this job and candidate."""
    attempt = (
        db.query(AssessmentAttempt)
        .join(Assessment, Assessment.id == AssessmentAttempt.assessment_id)
        .filter(
            Assessment.job_id == job_id,
            AssessmentAttempt.candidate_id == candidate_id,
        )
        .order_by(AssessmentAttempt.created_at.desc())
        .first()
    )

    if attempt is None:
        return AssessmentReportSection(has_assessment=False)

    assessment = attempt.assessment
    passing_score = assessment.passing_score if assessment else 60.0
    passed = (attempt.score >= passing_score) if attempt.score is not None else None

    return AssessmentReportSection(
        has_assessment=True,
        assessment_id=attempt.assessment_id,
        attempt_id=attempt.id,
        status=attempt.status.value if hasattr(attempt.status, "value") else str(attempt.status),
        score=attempt.score,
        mcq_score=attempt.mcq_score,
        coding_score=attempt.coding_score,
        passing_score=passing_score,
        passed=passed,
        attempted_at=attempt.submitted_at or attempt.started_at,
    )


def build_mock_interview_section(
    db: Session,
    job_id: int,
    candidate_id: int,
) -> MockInterviewReportSection:
    """Retrieve mock interview evaluations for this job and candidate."""
    session = (
        db.query(InterviewSession)
        .filter(
            InterviewSession.job_id == job_id,
            InterviewSession.candidate_id == candidate_id,
        )
        .order_by(InterviewSession.created_at.desc())
        .first()
    )

    if session is None or session.evaluation is None:
        return MockInterviewReportSection(
            has_interview=False,
            disclaimer=DISCLAIMER_INTERVIEW,
        )

    eval_obj = session.evaluation
    return MockInterviewReportSection(
        has_interview=True,
        session_id=session.id,
        status=session.status.value if hasattr(session.status, "value") else str(session.status),
        overall_score=eval_obj.overall_score,
        technical_correctness=eval_obj.technical_correctness,
        relevance=eval_obj.relevance,
        clarity=eval_obj.clarity,
        reasoning=eval_obj.reasoning,
        strengths=eval_obj.strengths or [],
        weaknesses=eval_obj.weaknesses or [],
        interview_suggestions=eval_obj.improvement_suggestions or [],
        recommended_topics=eval_obj.recommended_topics or [],
        disclaimer=eval_obj.disclaimer or DISCLAIMER_INTERVIEW,
    )


# --------------------------------------------------------------------------- #
# Personalized Improvement Plan                                               #
# --------------------------------------------------------------------------- #

def build_improvement_plan(
    diagnostic: ResumeDiagnosticReport,
    job: Job,
    matching_section: MatchingReportSection,
    ats_section: Optional[AtsReportSection],
    assessment_section: AssessmentReportSection,
    interview_section: MockInterviewReportSection,
    llm_client: Optional[BaseLLMClient] = None,
) -> PersonalizedImprovementPlan:
    """
    Synthesize performance signals into an actionable improvement plan.
    Calculations done deterministically in Python; natural-language narrative synthesized.
    """
    scores: List[float] = []

    if ats_section and ats_section.ats_score is not None:
        scores.append(ats_section.ats_score)
    elif matching_section.blended_score is not None:
        scores.append(matching_section.blended_score)

    if assessment_section.has_assessment and assessment_section.score is not None:
        scores.append(assessment_section.score)

    if interview_section.has_interview and interview_section.overall_score is not None:
        scores.append(interview_section.overall_score)

    if scores:
        composite_score = round(sum(scores) / len(scores), 2)
    else:
        composite_score = round(diagnostic.completeness_score, 2)

    if composite_score >= 80.0:
        readiness_level = "High Readiness"
    elif composite_score >= 60.0:
        readiness_level = "Moderate Readiness"
    else:
        readiness_level = "Needs Preparation"

    priority_gaps = list(matching_section.missing_skills)
    resume_actions = list(diagnostic.formatting_recommendations)

    tech_focus = list(priority_gaps)
    if assessment_section.has_assessment and (assessment_section.passed is False):
        tech_focus.append("Review timed coding problem patterns and syntax test cases")

    interview_points = list(interview_section.interview_suggestions)
    if not interview_points and interview_section.has_interview:
        interview_points.append("Focus on structured articulation of technical trade-offs")

    # Generate or fallback executive summary
    executive_summary = (
        f"Candidate demonstrates {readiness_level.lower()} (composite score: {composite_score}/100) "
        f"for the {job.title} role at {getattr(job, 'company_name', 'Company')}. "
    )
    if priority_gaps:
        executive_summary += f"Primary skill gaps to address include: {', '.join(priority_gaps[:3])}. "
    if interview_section.has_interview and interview_section.overall_score:
        executive_summary += f"Interview performance reflected an overall rating of {interview_section.overall_score}/100."

    # If LLM is available, optionally enhance executive summary
    try:
        client = llm_client or get_llm_client()
        prompt = f"""You are a professional technical career advisor compiling a 2-3 sentence executive recommendation summary.

Role: {job.title}
Composite Readiness: {composite_score}/100 ({readiness_level})
Missing Skills: {', '.join(priority_gaps) or 'None'}
Interview Strengths: {', '.join(interview_section.strengths) or 'None'}
Interview Weaknesses: {', '.join(interview_section.weaknesses) or 'None'}

Return ONLY a JSON object with this exact key:
{{
  "executive_summary": "2-3 sentences of constructive, empowering advice."
}}
"""
        raw = client.generate_json(prompt)
        if isinstance(raw, dict) and raw.get("executive_summary"):
            executive_summary = str(raw["executive_summary"]).strip()
    except Exception as exc:
        logger.debug("Using deterministic executive summary fallback: %s", exc)

    return PersonalizedImprovementPlan(
        composite_readiness_score=composite_score,
        readiness_level=readiness_level,
        priority_skill_gaps=priority_gaps,
        resume_action_items=resume_actions,
        technical_focus_areas=tech_focus,
        interview_coaching_points=interview_points,
        executive_summary=executive_summary,
    )


# --------------------------------------------------------------------------- #
# Main Report Aggregator                                                      #
# --------------------------------------------------------------------------- #

def generate_comprehensive_report(
    db: Session,
    job_id: int,
    resume_id: int,
    candidate: User,
    llm_client: Optional[BaseLLMClient] = None,
) -> ComprehensiveCandidateJobReport:
    """Generate unified report combining all system modules."""
    job = db.query(Job).filter(Job.id == job_id).first()
    if job is None:
        raise ValueError(f"Job with ID {job_id} not found.")

    resume = db.query(Resume).filter(Resume.id == resume_id).first()
    if resume is None:
        raise ValueError(f"Resume with ID {resume_id} not found.")

    # 1. Resume Diagnostic Section
    resume_diagnostic = build_resume_diagnostic_report(resume, candidate)

    # 2. Matching and ATS Sections
    match = (
        db.query(MatchResult)
        .filter(
            MatchResult.job_id == job_id,
            MatchResult.resume_id == resume_id,
        )
        .first()
    )
    matching_section = build_matching_section(match, job, resume_diagnostic.extracted_skills)
    ats_section = build_ats_section(match)

    # 3. Technical Assessment Section
    assessment_section = build_assessment_section(db, job_id, candidate.id)

    # 4. Mock Interview Section
    interview_section = build_mock_interview_section(db, job_id, candidate.id)

    # 5. Personalized Improvement Plan
    improvement_plan = build_improvement_plan(
        diagnostic=resume_diagnostic,
        job=job,
        matching_section=matching_section,
        ats_section=ats_section,
        assessment_section=assessment_section,
        interview_section=interview_section,
        llm_client=llm_client,
    )

    # 6. Application Status
    application = (
        db.query(JobApplication)
        .filter(
            JobApplication.job_id == job_id,
            JobApplication.candidate_id == candidate.id,
        )
        .first()
    )

    app_status = None
    applied_at = None
    if application is not None:
        app_status = (
            application.status.value
            if hasattr(application.status, "value")
            else str(application.status)
        )
        applied_at = getattr(application, "created_at", None)

    return ComprehensiveCandidateJobReport(
        candidate_id=candidate.id,
        candidate_name=candidate.full_name,
        candidate_email=candidate.email,
        job_id=job.id,
        job_title=job.title,
        company_name=getattr(job, "company_name", "Company"),
        application_status=app_status,
        applied_at=applied_at,
        resume_analysis=resume_diagnostic,
        matching=matching_section,
        ats=ats_section,
        assessment=assessment_section,
        mock_interview=interview_section,
        improvement_plan=improvement_plan,
        generated_at=_now(),
    )
