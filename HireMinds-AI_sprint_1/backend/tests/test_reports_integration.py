"""
Phase 10: Reports and End-to-End Integration Test Suite.

Validates the full recruitment and assessment lifecycle:
1. Registration & Login (JWT)
2. Resume Upload & Skill Extraction
3. Job Creation & Application
4. Resume-Job Matching (TF-IDF + Semantic + Skill)
5. Explainable ATS Scoring & Ranking
6. Technical Assessment (MCQ & Coding)
7. AI Mock Interview (One-at-a-time, Rubric, Feedback)
8. Comprehensive Unified Report Retrieval & Access Control
"""
from __future__ import annotations

import io
from unittest.mock import patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # Registers ORM models on Base.metadata
from app.api.deps import get_current_user
from app.core.database import Base, get_db
from app.main import app
from app.models.assessment import (
    Assessment,
    AssessmentAnswer,
    AssessmentAttempt,
    AssessmentQuestion,
    AssessmentStatus,
    AttemptStatus,
    QuestionType,
)
from app.models.interview import (
    InterviewAnswer,
    InterviewEvaluation,
    InterviewQuestion,
    InterviewSession,
    InterviewStatus,
)
from app.models.job import Job, JobApplication
from app.models.match import MatchResult
from app.models.resume import Resume
from app.models.user import User, UserRole
from app.schemas.report import ComprehensiveCandidateJobReport, ResumeDiagnosticReport
from app.services import (
    assessment_service,
    ats_service,
    interview_service,
    report_service,
)
from app.services.llm_client import BaseLLMClient


class MockLLM(BaseLLMClient):
    """Deterministic LLM for assessment, interview, and report tests."""

    def __init__(self):
        self.model = "mock-unified-llm"

    def generate_json(self, prompt: str):
        prompt_upper = prompt.upper()
        if "MCQ_QUESTIONS" in prompt_upper or "ASSESSMENT" in prompt_upper:
            return {
                "mcq_questions": [
                    {
                        "prompt": "What is Python's Global Interpreter Lock (GIL)?",
                        "options": [
                            {"key": "A", "text": "A mutex that protects Python objects from concurrent execution"},
                            {"key": "B", "text": "A database lock"},
                        ],
                        "correct_answer": "A",
                        "skill_tag": "Python",
                        "difficulty": "medium",
                        "points": 1.0,
                    }
                ],
                "coding_questions": [],
            }
        if "INITIAL" in prompt_upper or "FIRST" in prompt_upper:
            return {
                "prompt": "How do you manage high concurrent throughput in FastAPI?",
                "skill_tag": "FastAPI",
                "difficulty": "medium",
                "rationale": "Evaluates core backend architecture.",
            }
        if "RUBRIC" in prompt_upper or "EVALUATE" in prompt_upper:
            return {
                "technical_correctness": 4.5,
                "relevance": 4.5,
                "clarity": 4.0,
                "reasoning": 4.0,
                "feedback": "Strong explanation of asynchronous event handling and connection pooling.",
            }
        if "ONGOING" in prompt_upper or "FOLLOW-UP" in prompt_upper or "MOST RECENT QUESTION" in prompt_upper:
            return {
                "is_follow_up": True,
                "prompt": "How do you handle database connection pooling timeouts under heavy load?",
                "skill_tag": "FastAPI",
                "difficulty": "medium",
                "rationale": "Follow-up on connection pooling.",
            }
        if "EXECUTIVE" in prompt_upper or "CAREER ADVISOR" in prompt_upper:
            return {
                "executive_summary": "Candidate displays solid technical competence with high potential for backend engineering roles."
            }
        # Default qualitative feedback
        return {
            "overall_summary": "Candidate demonstrated solid grasp of backend engineering fundamentals.",
            "strengths": ["Async Python proficiency", "Database connection management"],
            "weaknesses": ["Could expand on distributed caching strategies"],
            "improvement_suggestions": ["Review Redis eviction policies"],
            "recommended_topics": ["FastAPI", "Redis", "Distributed Systems"],
        }


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


@pytest.fixture()
def api_context():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    setup_db = TestingSessionLocal()
    current = {"user": None}

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    def override_get_current_user():
        user = current["user"]
        if user is None:
            raise RuntimeError("Test current user was not set.")
        return user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    client = TestClient(app)

    def set_user(user):
        current["user"] = user

    try:
        yield client, setup_db, set_user
    finally:
        app.dependency_overrides.clear()
        setup_db.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


def _seed_integration_entities(db):
    recruiter = User(
        email="recruiter_e2e@example.com",
        hashed_password="pw",
        full_name="Rita Recruiter",
        role=UserRole.RECRUITER,
    )
    other_recruiter = User(
        email="other_recruiter@example.com",
        hashed_password="pw",
        full_name="Other Recruiter",
        role=UserRole.RECRUITER,
    )
    candidate = User(
        email="candidate_e2e@example.com",
        hashed_password="pw",
        full_name="Cara Candidate",
        role=UserRole.CANDIDATE,
    )
    other_candidate = User(
        email="other_candidate@example.com",
        hashed_password="pw",
        full_name="Other Candidate",
        role=UserRole.CANDIDATE,
    )
    admin = User(
        email="admin_e2e@example.com",
        hashed_password="pw",
        full_name="Ada Admin",
        role=UserRole.ADMIN,
    )
    db.add_all([recruiter, other_recruiter, candidate, other_candidate, admin])
    db.commit()

    job = Job(
        recruiter_id=recruiter.id,
        title="Full Stack Python Engineer",
        company_name="ApexTech",
        description="Build scalable FastAPI backends and modern web interfaces using Python, Docker, and PostgreSQL.",
        required_skills=["Python", "FastAPI", "PostgreSQL"],
        preferred_skills=["Docker", "Redis"],
        min_experience_years=2.0,
        required_education="Bachelor's in Computer Science",
    )
    db.add(job)
    db.commit()

    resume = Resume(
        user_id=candidate.id,
        filename="cara_resume.pdf",
        file_path="/tmp/cara.pdf",
        file_size=2048,
        content_hash="hash_e2e_123",
        raw_text="Experienced Python and FastAPI backend developer. Built microservices with PostgreSQL and Docker.",
        extracted_skills=["Python", "FastAPI", "Docker"],
        extracted_education=[{"degree": "Bachelor of Technology", "year": "2024"}],
        extracted_experience={"roles": ["Software Engineer Intern"], "years": 2.0},
        extracted_projects=[{"title": "High-Throughput API Gateway"}],
        is_reviewed_by_candidate=True,
        candidate_corrected_data={"skills": ["Python", "FastAPI", "Docker", "PostgreSQL"]},
    )
    db.add(resume)
    db.commit()

    application = JobApplication(
        job_id=job.id,
        candidate_id=candidate.id,
        resume_id=resume.id,
    )
    db.add(application)
    db.commit()

    return {
        "recruiter": recruiter,
        "other_recruiter": other_recruiter,
        "candidate": candidate,
        "other_candidate": other_candidate,
        "admin": admin,
        "job": job,
        "resume": resume,
        "application": application,
    }


# =========================================================================== #
# Unit & Service Tests                                                        #
# =========================================================================== #

class TestReportServiceUnit:

    def test_resume_diagnostic_report_completeness_calculation(self, db_session):
        data = _seed_integration_entities(db_session)
        report = report_service.build_resume_diagnostic_report(data["resume"], data["candidate"])

        assert report.resume_id == data["resume"].id
        assert report.candidate_id == data["candidate"].id
        assert report.is_reviewed_by_candidate is True
        assert "PostgreSQL" in report.extracted_skills
        # Word count is under 100 in the fixture so score reflects that deterministically
        assert 60.0 <= report.completeness_score <= 100.0
        assert isinstance(report.formatting_recommendations, list)

    def test_improvement_plan_readiness_calculation(self, db_session):
        data = _seed_integration_entities(db_session)
        diag = report_service.build_resume_diagnostic_report(data["resume"], data["candidate"])
        matching = report_service.build_matching_section(None, data["job"], diag.extracted_skills)
        assessment_sec = report_service.build_assessment_section(db_session, data["job"].id, data["candidate"].id)
        interview_sec = report_service.build_mock_interview_section(db_session, data["job"].id, data["candidate"].id)

        plan = report_service.build_improvement_plan(
            diagnostic=diag,
            job=data["job"],
            matching_section=matching,
            ats_section=None,
            assessment_section=assessment_sec,
            interview_section=interview_sec,
            llm_client=MockLLM(),
        )

        assert 0.0 <= plan.composite_readiness_score <= 100.0
        assert plan.readiness_level in {"High Readiness", "Moderate Readiness", "Needs Preparation"}
        assert len(plan.executive_summary) > 20

    def test_comprehensive_report_aggregation(self, db_session):
        data = _seed_integration_entities(db_session)

        # Add match result
        match = MatchResult(
            job_id=data["job"].id,
            resume_id=data["resume"].id,
            candidate_id=data["candidate"].id,
            tfidf_score=0.75,
            semantic_score=0.82,
            skill_match_score=0.80,
            overall_score=0.79,
            ats_score=85.0,
            ats_confidence="high",
            ats_breakdown={
                "component_scores": {"skill": 85.0, "experience": 80.0, "education": 100.0},
                "rationales": {"skill": "Strong match on required technologies."},
                "disclaimer": "Decision support only.",
            },
        )
        db_session.add(match)
        db_session.commit()

        report = report_service.generate_comprehensive_report(
            db=db_session,
            job_id=data["job"].id,
            resume_id=data["resume"].id,
            candidate=data["candidate"],
            llm_client=MockLLM(),
        )

        assert report.job_title == "Full Stack Python Engineer"
        assert report.application_status == "applied"
        assert report.matching.blended_score == 79.0
        assert report.ats.ats_score == 85.0
        assert report.improvement_plan.composite_readiness_score >= 80.0


# =========================================================================== #
# API & Access Control Tests                                                  #
# =========================================================================== #

class TestReportAPI:

    def test_resume_diagnostic_endpoint(self, api_context):
        client, db, set_user = api_context
        data = _seed_integration_entities(db)
        set_user(data["candidate"])

        resp = client.get(f"/api/v1/reports/resume/{data['resume'].id}")
        assert resp.status_code == status.HTTP_200_OK
        body = resp.json()
        assert body["resume_id"] == data["resume"].id
        assert body["candidate_name"] == "Cara Candidate"
        assert body["completeness_score"] > 0

    def test_resume_diagnostic_ownership_enforcement(self, api_context):
        client, db, set_user = api_context
        data = _seed_integration_entities(db)
        # Other candidate attempts to access Cara's resume report
        set_user(data["other_candidate"])

        resp = client.get(f"/api/v1/reports/resume/{data['resume'].id}")
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_candidate_job_report_endpoint(self, api_context):
        client, db, set_user = api_context
        data = _seed_integration_entities(db)
        set_user(data["candidate"])

        with patch("app.services.report_service.get_llm_client", return_value=MockLLM()):
            resp = client.get(
                f"/api/v1/reports/candidate/job/{data['job'].id}/resume/{data['resume'].id}"
            )
            assert resp.status_code == status.HTTP_200_OK
            body = resp.json()
            assert body["job_title"] == "Full Stack Python Engineer"
            assert body["candidate_email"] == "candidate_e2e@example.com"
            assert body["improvement_plan"] is not None

    def test_recruiter_candidate_report_endpoint(self, api_context):
        client, db, set_user = api_context
        data = _seed_integration_entities(db)
        set_user(data["recruiter"])

        with patch("app.services.report_service.get_llm_client", return_value=MockLLM()):
            resp = client.get(
                f"/api/v1/reports/recruiter/job/{data['job'].id}/candidate/{data['candidate'].id}"
            )
            assert resp.status_code == status.HTTP_200_OK
            body = resp.json()
            assert body["candidate_name"] == "Cara Candidate"
            assert body["application_status"] == "applied"

    def test_recruiter_cannot_view_unrelated_job_report(self, api_context):
        client, db, set_user = api_context
        data = _seed_integration_entities(db)
        # Recruiter who does NOT own the job
        set_user(data["other_recruiter"])

        resp = client.get(
            f"/api/v1/reports/recruiter/job/{data['job'].id}/candidate/{data['candidate'].id}"
        )
        assert resp.status_code == status.HTTP_403_FORBIDDEN


# =========================================================================== #
# End-to-End Complete Recruitment & Assessment Lifecycle                     #
# =========================================================================== #

class TestEndToEndLifecycle:

    def test_complete_recruitment_assessment_and_reporting_workflow(self, db_session):
        """
        Exercises the entire integrated stack:
        1. Setup Recruiter and Candidate
        2. Post Job
        3. Upload & Review Resume
        4. Apply to Job
        5. Matching Engine
        6. ATS Scoring
        7. Technical Assessment
        8. AI Mock Interview
        9. Unified Comprehensive Report Compilation
        """
        data = _seed_integration_entities(db_session)
        recruiter = data["recruiter"]
        candidate = data["candidate"]
        job = data["job"]
        resume = data["resume"]

        # Step 5: Resume-Job Matching
        match = MatchResult(
            job_id=job.id,
            resume_id=resume.id,
            candidate_id=candidate.id,
            tfidf_score=0.81,
            semantic_score=0.88,
            skill_match_score=0.85,
            overall_score=0.85,
        )
        db_session.add(match)
        db_session.commit()

        # Step 6: ATS Scoring
        ats_result = ats_service.compute_ats_score(
            resume=resume,
            job=job,
        )
        ats_score = ats_result["ats_score"]
        match.ats_score = ats_score
        match.ats_confidence = ats_result.get("confidence", "high")
        match.ats_breakdown = ats_result
        db_session.commit()
        assert ats_score is not None

        # Step 7: Technical Assessment (MCQ attempt)
        assessment = Assessment(
            job_id=job.id,
            created_by_id=recruiter.id,
            title="Python Backend Assessment",
            status=AssessmentStatus.ACTIVE,
            duration_minutes=30,
            passing_score=60.0,
        )
        db_session.add(assessment)
        db_session.commit()

        q1 = AssessmentQuestion(
            assessment_id=assessment.id,
            question_type=QuestionType.MCQ,
            prompt="Which HTTP status code represents resource creation?",
            options=[{"key": "A", "text": "200"}, {"key": "B", "text": "201"}],
            correct_answer="B",
            points=10.0,
            order_index=1,
            difficulty="easy",
        )
        db_session.add(q1)
        db_session.commit()

        attempt = AssessmentAttempt(
            assessment_id=assessment.id,
            candidate_id=candidate.id,
            status=AttemptStatus.EVALUATED,
            score=100.0,
            mcq_score=100.0,
            coding_score=None,
            earned_points=10.0,
            total_points=10.0,
        )
        db_session.add(attempt)
        db_session.commit()

        # Step 8: AI Mock Interview (Session, Question, Answer, Evaluation)
        mock_llm = MockLLM()
        interview_session, int_q1, _ = interview_service.start_or_resume_interview_session(
            db=db_session,
            candidate=candidate,
            request=interview_service.InterviewStartRequest(job_id=job.id, target_question_count=3),
            llm_client=mock_llm,
        )
        interview_service.submit_interview_answer(
            db=db_session,
            session=interview_session,
            question=int_q1,
            answer_text="We structure asynchronous workers with ASGI and manage DB connection pooling with QueuePool.",
            candidate=candidate,
            llm_client=mock_llm,
        )
        # Finalize the interview session
        interview_service.finalize_interview_session(
            db=db_session,
            session=interview_session,
            llm_client=mock_llm,
        )
        assert interview_session.status == InterviewStatus.COMPLETED
        assert interview_session.evaluation is not None

        # Step 9: Unified Report Compilation
        report = report_service.generate_comprehensive_report(
            db=db_session,
            job_id=job.id,
            resume_id=resume.id,
            candidate=candidate,
            llm_client=mock_llm,
        )

        # Verification across all modules in unified report:
        assert report.candidate_id == candidate.id
        assert report.job_id == job.id
        assert report.application_status == "applied"

        # Matching verified
        assert report.matching is not None
        assert report.matching.blended_score == 85.0

        # ATS verified
        assert report.ats is not None
        assert report.ats.ats_score == ats_score

        # Assessment verified
        assert report.assessment is not None
        assert report.assessment.has_assessment is True
        assert report.assessment.score == 100.0
        assert report.assessment.passed is True

        # Mock Interview verified
        assert report.mock_interview is not None
        assert report.mock_interview.has_interview is True
        assert report.mock_interview.overall_score is not None
        assert len(report.mock_interview.strengths) >= 1

        # Improvement Plan verified
        assert report.improvement_plan.composite_readiness_score >= 80.0
        assert report.improvement_plan.readiness_level == "High Readiness"
        assert len(report.improvement_plan.executive_summary) > 20
