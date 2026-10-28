"""
Phase 9 tests: AI Mock Interview generation, answer evaluation, and access control.

Test strategy:
* Uses in-memory SQLite with StaticPool (no running MySQL required).
* Mocks LLM responses deterministically.
* Tests rubric scoring, follow-up question logic, session completion, and fallbacks.
* Tests role-based access control and isolation from ATS scoring.
"""
from __future__ import annotations

from unittest.mock import patch
import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # Registers all ORM models on Base.metadata
from app.api.deps import get_current_user
from app.core.database import Base, get_db
from app.main import app
from app.models.interview import (
    InterviewAnswer,
    InterviewEvaluation,
    InterviewQuestion,
    InterviewSession,
    InterviewStatus,
)
from app.models.job import Job
from app.models.match import MatchResult
from app.models.resume import Resume
from app.models.user import User, UserRole
from app.schemas.interview import InterviewStartRequest
from app.services import interview_service
from app.services.interview_service import DISCLAIMER_TEXT
from app.services.llm_client import (
    BaseLLMClient,
    LLMAPIError,
    LLMConfigurationError,
    LLMResponseError,
    LLMTimeoutError,
)


# =========================================================================== #
# Fixtures and Mock Clients                                                   #
# =========================================================================== #

class MockInterviewLLM(BaseLLMClient):
    """Deterministic mock client for interview generation and evaluation."""

    def __init__(self, responses: list | None = None):
        self.model = "mock-interview-model"
        self.responses = list(responses or [])
        self.calls = []

    def generate_json(self, prompt: str):
        self.calls.append(prompt)
        if not self.responses:
            # Default response based on prompt context
            if "INITIAL" in prompt.upper() or "FIRST" in prompt.upper():
                return {
                    "prompt": "How do you design a high-throughput API with FastAPI and connection pooling?",
                    "skill_tag": "FastAPI",
                    "difficulty": "medium",
                    "rationale": "Evaluates core backend architecture skills.",
                }
            if "RUBRIC" in prompt.upper() or "EVALUATE" in prompt.upper():
                return {
                    "technical_correctness": 4.5,
                    "relevance": 4.0,
                    "clarity": 4.5,
                    "reasoning": 4.0,
                    "feedback": "Clear explanation of async workers and connection pooling limits.",
                    "strengths": ["Clear understanding of ASGI event loops"],
                    "improvements": ["Could mention Redis caching for read-heavy loads"],
                }
            if "FOLLOW-UP" in prompt.upper() or "ONGOING" in prompt.upper():
                return {
                    "is_follow_up": True,
                    "prompt": "How would you handle connection timeouts if the MySQL pool is exhausted?",
                    "skill_tag": "FastAPI & MySQL",
                    "difficulty": "hard",
                    "rationale": "Follows up on candidate's pool exhaustion mitigation.",
                }
            # Session qualitative evaluation
            return {
                "overall_summary": "Candidate demonstrated strong architectural grasp of backend systems.",
                "strengths": ["Deep understanding of concurrency", "Precise terminology"],
                "weaknesses": ["Could explore edge case failure modes in more depth"],
                "improvement_suggestions": ["Practice distributed systems failure recovery scenarios"],
                "recommended_topics": ["FastAPI", "Database Pooling", "Redis"],
            }
        return self.responses.pop(0)


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


def _create_user(email: str, role: UserRole, name: str) -> User:
    return User(
        email=email,
        hashed_password="hashed_password_for_tests",
        full_name=name,
        role=role,
    )


def _seed_test_data(db):
    recruiter = _create_user("recruiter@example.com", UserRole.RECRUITER, "Rob Recruiter")
    other_recruiter = _create_user("other-recruiter@example.com", UserRole.RECRUITER, "Olivia Other")
    candidate = _create_user("candidate@example.com", UserRole.CANDIDATE, "Carol Candidate")
    other_candidate = _create_user("other-candidate@example.com", UserRole.CANDIDATE, "Oscar Other")
    admin = _create_user("admin@example.com", UserRole.ADMIN, "Adam Admin")
    db.add_all([recruiter, other_recruiter, candidate, other_candidate, admin])
    db.commit()

    job = Job(
        recruiter_id=recruiter.id,
        title="Senior Python Developer",
        company_name="TechCorp",
        description="Develop scalable FastAPI microservices with MySQL and Redis.",
        required_skills=["Python", "FastAPI", "MySQL"],
        preferred_skills=["Docker", "Redis"],
        min_experience_years=3,
        required_education="Bachelor's in Computer Science",
    )
    db.add(job)
    db.commit()

    resume = Resume(
        user_id=candidate.id,
        filename="carol_resume.pdf",
        file_path="/tmp/carol_resume.pdf",
        file_size=1024,
        content_hash="mock_hash_12345",
        raw_text="Python and FastAPI developer with 4 years experience.",
        extracted_skills=["Python", "FastAPI", "MySQL", "Docker"],
        is_reviewed_by_candidate=True,
        candidate_corrected_data={"skills": ["Python", "FastAPI", "MySQL", "Docker", "Redis"]},
    )
    db.add(resume)
    db.commit()

    return {
        "recruiter": recruiter,
        "other_recruiter": other_recruiter,
        "candidate": candidate,
        "other_candidate": other_candidate,
        "admin": admin,
        "job": job,
        "resume": resume,
    }


# =========================================================================== #
# Unit Tests: Prompts, Scoring & Helper Logic                                 #
# =========================================================================== #

class TestInterviewPromptsAndHelpers:

    def test_candidate_skills_extraction(self, db_session):
        data = _seed_test_data(db_session)
        skills = interview_service._candidate_skills(data["resume"])
        assert "Redis" in skills
        assert "Python" in skills

    def test_candidate_skills_empty_for_none(self):
        assert interview_service._candidate_skills(None) == []

    def test_clamp_score(self):
        assert interview_service._clamp_score(0.5) == 1.0
        assert interview_service._clamp_score(5.5) == 5.0
        assert interview_service._clamp_score(3.456) == 3.46
        assert interview_service._clamp_score("invalid") == 3.0

    def test_generate_initial_question_validates_prompt(self, db_session):
        data = _seed_test_data(db_session)
        mock_llm = MockInterviewLLM(responses=[{"prompt": "Too short"}])
        with pytest.raises(LLMResponseError, match="empty or invalid"):
            interview_service.generate_initial_question(
                job=data["job"],
                candidate_skills=["Python"],
                difficulty="medium",
                focus_areas=["FastAPI"],
                llm_client=mock_llm,
            )

    def test_evaluate_answer_rubric_calculation(self, db_session):
        data = _seed_test_data(db_session)
        question = InterviewQuestion(
            session_id=1,
            order_index=1,
            prompt="What is dependency injection?",
            skill_tag="FastAPI",
            difficulty="medium",
        )
        mock_llm = MockInterviewLLM(
            responses=[
                {
                    "technical_correctness": 4.0,
                    "relevance": 5.0,
                    "clarity": 4.0,
                    "reasoning": 3.0,
                    "feedback": "Good answer explaining FastAPI's Depends() system.",
                }
            ]
        )
        result = interview_service.evaluate_answer_with_rubric(
            question=question,
            answer_text="FastAPI uses Depends() to inject database sessions and current users.",
            job=data["job"],
            llm_client=mock_llm,
        )

        assert result["technical_correctness"] == 4.0
        assert result["relevance"] == 5.0
        assert result["clarity"] == 4.0
        assert result["reasoning"] == 3.0
        # (4 + 5 + 4 + 3) / 20 * 100 = 16 / 20 * 100 = 80.0
        assert result["overall_score"] == 80.0
        assert "FastAPI" in result["feedback"]

    def test_deterministic_fallback_feedback(self, db_session):
        data = _seed_test_data(db_session)
        feedback = interview_service._deterministic_fallback_feedback(data["job"], [])
        assert "Senior Python Developer" in feedback["overall_summary"]
        assert len(feedback["strengths"]) >= 1
        assert len(feedback["recommended_topics"]) >= 1


# =========================================================================== #
# Core Service Tests                                                          #
# =========================================================================== #

class TestInterviewServiceCore:

    def test_start_interview_creates_session_and_first_question(self, db_session):
        data = _seed_test_data(db_session)
        mock_llm = MockInterviewLLM()
        req = InterviewStartRequest(
            job_id=data["job"].id,
            resume_id=data["resume"].id,
            target_question_count=3,
            difficulty="medium",
        )

        session, question, is_resumed = interview_service.start_or_resume_interview_session(
            db=db_session,
            candidate=data["candidate"],
            request=req,
            llm_client=mock_llm,
        )

        assert is_resumed is False
        assert session.status == InterviewStatus.IN_PROGRESS
        assert session.target_question_count == 3
        assert question.order_index == 1
        assert question.is_follow_up is False
        assert len(question.prompt) > 10

    def test_resume_interview_session(self, db_session):
        data = _seed_test_data(db_session)
        mock_llm = MockInterviewLLM()
        req = InterviewStartRequest(job_id=data["job"].id, target_question_count=3)

        # First call: creates session
        s1, q1, is_resumed_1 = interview_service.start_or_resume_interview_session(
            db=db_session, candidate=data["candidate"], request=req, llm_client=mock_llm
        )
        assert is_resumed_1 is False

        # Second call: resumes same session
        s2, q2, is_resumed_2 = interview_service.start_or_resume_interview_session(
            db=db_session, candidate=data["candidate"], request=req, llm_client=mock_llm
        )
        assert is_resumed_2 is True
        assert s1.id == s2.id
        assert q1.id == q2.id

    def test_cannot_use_another_candidates_resume(self, db_session):
        data = _seed_test_data(db_session)
        mock_llm = MockInterviewLLM()
        req = InterviewStartRequest(
            job_id=data["job"].id,
            resume_id=data["resume"].id,  # Carol's resume
        )

        # Oscar attempts to use Carol's resume
        with pytest.raises(Exception) as exc_info:
            interview_service.start_or_resume_interview_session(
                db=db_session,
                candidate=data["other_candidate"],
                request=req,
                llm_client=mock_llm,
            )
        assert "does not belong to you" in str(exc_info.value.detail)

    def test_submit_answer_stores_and_generates_follow_up(self, db_session):
        data = _seed_test_data(db_session)
        mock_llm = MockInterviewLLM()
        req = InterviewStartRequest(job_id=data["job"].id, target_question_count=3)
        session, question, _ = interview_service.start_or_resume_interview_session(
            db=db_session, candidate=data["candidate"], request=req, llm_client=mock_llm
        )

        res = interview_service.submit_interview_answer(
            db=db_session,
            session=session,
            question=question,
            answer_text="We configure connection pools in SQLAlchemy using QueuePool with max_overflow limits.",
            candidate=data["candidate"],
            llm_client=mock_llm,
        )

        assert res["is_completed"] is False
        assert res["has_next_question"] is True
        assert res["answer"].overall_score > 0
        assert res["next_question"].order_index == 2
        assert res["next_question"].parent_question_id == question.id
        assert res["next_question"].is_follow_up is True

    def test_submit_answer_duplicate_prevention(self, db_session):
        data = _seed_test_data(db_session)
        mock_llm = MockInterviewLLM()
        req = InterviewStartRequest(job_id=data["job"].id, target_question_count=3)
        session, question, _ = interview_service.start_or_resume_interview_session(
            db=db_session, candidate=data["candidate"], request=req, llm_client=mock_llm
        )

        # First answer
        interview_service.submit_interview_answer(
            db=db_session,
            session=session,
            question=question,
            answer_text="Answer 1",
            candidate=data["candidate"],
            llm_client=mock_llm,
        )

        # Second attempt on same question
        with pytest.raises(Exception) as exc_info:
            interview_service.submit_interview_answer(
                db=db_session,
                session=session,
                question=question,
                answer_text="Answer 1 again",
                candidate=data["candidate"],
                llm_client=mock_llm,
            )
        assert exc_info.value.status_code == status.HTTP_409_CONFLICT

    def test_submit_answer_completes_session_at_target(self, db_session):
        data = _seed_test_data(db_session)
        mock_llm = MockInterviewLLM()
        # Set target question count to 1 for quick completion test
        req = InterviewStartRequest(job_id=data["job"].id, target_question_count=3)
        session, q1, _ = interview_service.start_or_resume_interview_session(
            db=db_session, candidate=data["candidate"], request=req, llm_client=mock_llm
        )
        session.target_question_count = 1
        db_session.commit()

        res = interview_service.submit_interview_answer(
            db=db_session,
            session=session,
            question=q1,
            answer_text="My comprehensive technical answer to the first question.",
            candidate=data["candidate"],
            llm_client=mock_llm,
        )

        assert res["is_completed"] is True
        assert res["has_next_question"] is False
        assert session.status == InterviewStatus.COMPLETED
        assert session.completed_at is not None
        assert session.evaluation is not None
        assert session.evaluation.overall_score > 0
        assert DISCLAIMER_TEXT in session.evaluation.disclaimer

    def test_cannot_answer_completed_session(self, db_session):
        data = _seed_test_data(db_session)
        mock_llm = MockInterviewLLM()
        req = InterviewStartRequest(job_id=data["job"].id, target_question_count=3)
        session, q1, _ = interview_service.start_or_resume_interview_session(
            db=db_session, candidate=data["candidate"], request=req, llm_client=mock_llm
        )
        interview_service.finalize_interview_session(db_session, session, mock_llm)

        with pytest.raises(Exception) as exc_info:
            interview_service.submit_interview_answer(
                db=db_session,
                session=session,
                question=q1,
                answer_text="Late answer",
                candidate=data["candidate"],
                llm_client=mock_llm,
            )
        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST

    def test_finalize_fallback_on_llm_error(self, db_session):
        data = _seed_test_data(db_session)
        mock_llm = MockInterviewLLM()
        session, q1, _ = interview_service.start_or_resume_interview_session(
            db=db_session,
            candidate=data["candidate"],
            request=InterviewStartRequest(job_id=data["job"].id, target_question_count=3),
            llm_client=mock_llm,
        )

        # Broken LLM that raises an exception on session feedback
        class FailingLLM(BaseLLMClient):
            model = "failing-llm"

            def generate_json(self, prompt: str):
                raise LLMAPIError("API rate limit exceeded")

        evaluation = interview_service.finalize_interview_session(
            db=db_session,
            session=session,
            llm_client=FailingLLM(),
        )

        assert evaluation.generation_status == "fallback"
        assert len(evaluation.strengths) >= 1
        assert len(evaluation.recommended_topics) >= 1
        assert DISCLAIMER_TEXT in evaluation.disclaimer

    def test_interview_evaluation_separated_from_ats(self, db_session):
        """Verify interview workflow does not touch or affect MatchResult table."""
        data = _seed_test_data(db_session)
        mock_llm = MockInterviewLLM()

        # Check existing match results before
        count_before = db_session.query(MatchResult).count()

        session, q1, _ = interview_service.start_or_resume_interview_session(
            db=db_session,
            candidate=data["candidate"],
            request=InterviewStartRequest(job_id=data["job"].id, target_question_count=3),
            llm_client=mock_llm,
        )
        interview_service.submit_interview_answer(
            db=db_session,
            session=session,
            question=q1,
            answer_text="Some answer",
            candidate=data["candidate"],
            llm_client=mock_llm,
        )

        count_after = db_session.query(MatchResult).count()
        assert count_before == count_after == 0


# =========================================================================== #
# API Endpoint Integration Tests                                              #
# =========================================================================== #

class TestInterviewAPI:

    def test_start_interview_endpoint(self, api_context):
        client, db, set_user = api_context
        data = _seed_test_data(db)
        set_user(data["candidate"])

        with patch("app.services.interview_service.get_llm_client", return_value=MockInterviewLLM()):
            resp = client.post(
                "/api/v1/interviews/start",
                json={
                    "job_id": data["job"].id,
                    "target_question_count": 3,
                    "difficulty": "medium",
                },
            )
            assert resp.status_code == status.HTTP_201_CREATED
            body = resp.json()
            assert body["job_id"] == data["job"].id
            assert body["candidate_id"] == data["candidate"].id
            assert body["status"] == "in_progress"
            assert body["current_question"] is not None
            assert len(body["questions"]) == 1

    def test_start_interview_unauthorized_for_recruiter(self, api_context):
        client, db, set_user = api_context
        data = _seed_test_data(db)
        # Recruiter tries to start interview as candidate
        set_user(data["recruiter"])

        resp = client.post(
            "/api/v1/interviews/start",
            json={"job_id": data["job"].id},
        )
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_get_current_question_endpoint(self, api_context):
        client, db, set_user = api_context
        data = _seed_test_data(db)
        set_user(data["candidate"])

        with patch("app.services.interview_service.get_llm_client", return_value=MockInterviewLLM()):
            start_resp = client.post(
                "/api/v1/interviews/start",
                json={"job_id": data["job"].id, "target_question_count": 3},
            )
            session_id = start_resp.json()["id"]

            curr_resp = client.get(f"/api/v1/interviews/{session_id}/current-question")
            assert curr_resp.status_code == status.HTTP_200_OK
            body = curr_resp.json()
            assert body["session_id"] == session_id
            assert body["current_question"]["order_index"] == 1
            assert body["answered_count"] == 0
            assert body["is_completed"] is False

    def test_submit_answer_endpoint(self, api_context):
        client, db, set_user = api_context
        data = _seed_test_data(db)
        set_user(data["candidate"])

        with patch("app.services.interview_service.get_llm_client", return_value=MockInterviewLLM()):
            start_resp = client.post(
                "/api/v1/interviews/start",
                json={"job_id": data["job"].id, "target_question_count": 3},
            )
            session_id = start_resp.json()["id"]
            question_id = start_resp.json()["current_question"]["id"]

            ans_resp = client.post(
                f"/api/v1/interviews/{session_id}/questions/{question_id}/answer",
                json={"answer_text": "We handle connection pooling using SQLAlchemy QueuePool."},
            )
            assert ans_resp.status_code == status.HTTP_200_OK
            ans_body = ans_resp.json()
            assert ans_body["has_next_question"] is True
            assert ans_body["answer"]["overall_score"] > 0
            assert ans_body["answer"]["technical_correctness"] >= 1.0

    def test_submit_answer_ownership_enforcement(self, api_context):
        client, db, set_user = api_context
        data = _seed_test_data(db)
        set_user(data["candidate"])

        with patch("app.services.interview_service.get_llm_client", return_value=MockInterviewLLM()):
            start_resp = client.post(
                "/api/v1/interviews/start",
                json={"job_id": data["job"].id, "target_question_count": 3},
            )
            session_id = start_resp.json()["id"]
            question_id = start_resp.json()["current_question"]["id"]

        # Switch user to Oscar
        set_user(data["other_candidate"])
        ans_resp = client.post(
            f"/api/v1/interviews/{session_id}/questions/{question_id}/answer",
            json={"answer_text": "Intruder answer."},
        )
        assert ans_resp.status_code == status.HTTP_403_FORBIDDEN

    def test_complete_and_get_evaluation_endpoint(self, api_context):
        client, db, set_user = api_context
        data = _seed_test_data(db)
        set_user(data["candidate"])

        with patch("app.services.interview_service.get_llm_client", return_value=MockInterviewLLM()):
            start_resp = client.post(
                "/api/v1/interviews/start",
                json={"job_id": data["job"].id, "target_question_count": 3},
            )
            session_id = start_resp.json()["id"]

            # Complete session manually
            comp_resp = client.post(f"/api/v1/interviews/{session_id}/complete")
            assert comp_resp.status_code == status.HTTP_200_OK
            assert comp_resp.json()["status"] == "completed"

            # Retrieve evaluation
            eval_resp = client.get(f"/api/v1/interviews/{session_id}/evaluation")
            assert eval_resp.status_code == status.HTTP_200_OK
            eval_body = eval_resp.json()
            assert "overall_summary" in eval_body
            assert len(eval_body["strengths"]) >= 1
            assert DISCLAIMER_TEXT in eval_body["disclaimer"]

    def test_recruiter_access_to_interview(self, api_context):
        client, db, set_user = api_context
        data = _seed_test_data(db)
        set_user(data["candidate"])

        with patch("app.services.interview_service.get_llm_client", return_value=MockInterviewLLM()):
            start_resp = client.post(
                "/api/v1/interviews/start",
                json={"job_id": data["job"].id, "target_question_count": 3},
            )
            session_id = start_resp.json()["id"]

        # 1. Job owner recruiter can view the session
        set_user(data["recruiter"])
        rec_resp = client.get(f"/api/v1/interviews/{session_id}")
        assert rec_resp.status_code == status.HTTP_200_OK

        # 2. Other recruiter CANNOT view the session
        set_user(data["other_recruiter"])
        other_resp = client.get(f"/api/v1/interviews/{session_id}")
        assert other_resp.status_code == status.HTTP_403_FORBIDDEN

    def test_list_interviews_endpoint(self, api_context):
        client, db, set_user = api_context
        data = _seed_test_data(db)
        set_user(data["candidate"])

        with patch("app.services.interview_service.get_llm_client", return_value=MockInterviewLLM()):
            client.post(
                "/api/v1/interviews/start",
                json={"job_id": data["job"].id, "target_question_count": 3},
            )

        # Candidate lists sessions
        list_resp = client.get("/api/v1/interviews/")
        assert list_resp.status_code == status.HTTP_200_OK
        assert list_resp.json()["total"] == 1

        # Other candidate has 0 sessions
        set_user(data["other_candidate"])
        other_list_resp = client.get("/api/v1/interviews/")
        assert other_list_resp.status_code == status.HTTP_200_OK
        assert other_list_resp.json()["total"] == 0

    def test_llm_configuration_error_returns_503(self, api_context):
        client, db, set_user = api_context
        data = _seed_test_data(db)
        set_user(data["candidate"])

        class UnconfiguredLLM(BaseLLMClient):
            model = "unconfigured"

            def generate_json(self, prompt: str):
                raise LLMConfigurationError("GEMINI_API_KEY is not configured.")

        with patch("app.services.interview_service.get_llm_client", return_value=UnconfiguredLLM()):
            resp = client.post(
                "/api/v1/interviews/start",
                json={"job_id": data["job"].id},
            )
            assert resp.status_code == status.HTTP_503_SERVICE_UNAVAILABLE

    def test_llm_timeout_returns_504(self, api_context):
        client, db, set_user = api_context
        data = _seed_test_data(db)
        set_user(data["candidate"])

        class TimeoutLLM(BaseLLMClient):
            model = "timeout"

            def generate_json(self, prompt: str):
                raise LLMTimeoutError("Gemini request timed out.")

        with patch("app.services.interview_service.get_llm_client", return_value=TimeoutLLM()):
            resp = client.post(
                "/api/v1/interviews/start",
                json={"job_id": data["job"].id},
            )
            assert resp.status_code == status.HTTP_504_GATEWAY_TIMEOUT
