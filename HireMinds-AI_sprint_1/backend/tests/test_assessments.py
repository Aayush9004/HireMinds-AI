"""
Phase 8 tests: technical assessment generation, evaluation and ownership.

Test strategy
-------------
* Pure validation and scoring tests use in-memory SQLite, so no MySQL is needed.
* Gemini and Docker are always mocked; no network, API key or container is used.
* API tests override the DB and auth dependencies to exercise ownership rules
  through the real FastAPI routes.
"""
from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401 - registers all ORM models on Base.metadata
from app.api.deps import get_current_user
from app.core.database import Base, get_db
from app.main import app
from app.models.assessment import (
    Assessment,
    AssessmentAttempt,
    AssessmentStatus,
    AttemptStatus,
    QuestionType,
)
from app.models.job import Job, JobApplication
from app.models.resume import Resume
from app.models.user import User, UserRole
from app.services import assessment_service
from app.services.coding_sandbox import (
    CodingSandbox,
    SandboxResult,
    _parse_harness_output,
    build_harness,
)
from app.services.gemini_client import (
    GeminiAPIError,
    GeminiClient,
    GeminiConfigurationError,
    GeminiResponseError,
    GeminiTimeoutError,
    extract_json,
)
from app.services.deepseek_client import DeepSeekClient
from app.services.llm_client import (
    LLMAPIError,
    LLMConfigurationError,
    LLMResponseError,
    LLMTimeoutError,
    get_llm_client,
)


# =========================================================================== #
# Fixtures and helpers                                                        #
# =========================================================================== #
@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
    )
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
    TestingSessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
    )
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


def _user(email: str, role: UserRole, name: str | None = None) -> User:
    return User(
        email=email,
        hashed_password="not-used-in-tests",
        full_name=name or email.split("@")[0].title(),
        role=role,
    )


def _setup_entities(db):
    recruiter = _user("recruiter@example.com", UserRole.RECRUITER, "Rita Recruiter")
    other_recruiter = _user("other-recruiter@example.com", UserRole.RECRUITER, "Owen Other")
    candidate = _user("candidate@example.com", UserRole.CANDIDATE, "Cara Candidate")
    other_candidate = _user("other-candidate@example.com", UserRole.CANDIDATE, "Oscar Other")
    admin = _user("admin@example.com", UserRole.ADMIN, "Ada Admin")
    db.add_all([recruiter, other_recruiter, candidate, other_candidate, admin])
    db.commit()

    job = Job(
        recruiter_id=recruiter.id,
        title="Backend Python Engineer",
        company_name="Acme",
        description="Build FastAPI services with Python and MySQL.",
        required_skills=["Python", "FastAPI"],
        preferred_skills=["Docker"],
        min_experience_years=2,
        required_education="Bachelor's Degree",
    )
    db.add(job)
    db.commit()

    resume = Resume(
        user_id=candidate.id,
        filename="candidate.pdf",
        file_path="/tmp/candidate.pdf",
        file_size=1234,
        content_hash="hash-candidate",
        raw_text="Python and FastAPI developer.",
        extracted_skills=["Python", "FastAPI"],
        extracted_education=[],
        extracted_experience={},
        extracted_projects=[],
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

    return SimpleNamespace(
        recruiter=recruiter,
        other_recruiter=other_recruiter,
        candidate=candidate,
        other_candidate=other_candidate,
        admin=admin,
        job=job,
        resume=resume,
        application=application,
    )


def _valid_payload(mcq_count: int = 2, coding_count: int = 1):
    mcqs = [
        {
            "prompt": "Which library does FastAPI use for validation?",
            "options": [
                {"key": "A", "text": "Pydantic"},
                {"key": "B", "text": "NumPy"},
                {"key": "C", "text": "Pandas"},
            ],
            "correct_answer": "A",
            "explanation": "Pydantic validates request and response models.",
            "skill_tag": "FastAPI",
            "difficulty": "easy",
            "points": 1,
        },
        {
            "prompt": "Which keyword defines a function in Python?",
            "options": ["def", "func", "function"],
            "correct_answer": "def",
            "explanation": "Python uses the def keyword.",
            "skill_tag": "Python",
            "difficulty": "easy",
            "points": 1,
        },
        {
            "prompt": "Which HTTP method is conventionally used to create a resource?",
            "options": [
                {"key": "A", "text": "GET"},
                {"key": "B", "text": "POST"},
                {"key": "C", "text": "DELETE"},
            ],
            "correct_answer": "B",
            "explanation": "POST is conventionally used for creation.",
            "skill_tag": "HTTP",
            "difficulty": "medium",
            "points": 1,
        },
    ]
    codings = [
        {
            "prompt": "Return the sum of two integers.",
            "language": "python",
            "function_name": "add",
            "starter_code": "def add(a, b):\n    pass\n",
            "test_cases": [
                {"input": [1, 2], "expected": 3, "hidden": False},
                {"input": [5, 7], "expected": 12, "hidden": True},
            ],
            "explanation": "Return a + b.",
            "skill_tag": "Python",
            "difficulty": "easy",
            "points": 5,
            "time_limit_ms": 5000,
            "memory_limit_mb": 256,
        }
    ]
    return {
        "mcq_questions": mcqs[:mcq_count],
        "coding_questions": codings[:coding_count],
    }


class FakeGemini:
    def __init__(self, payload):
        self.payload = payload
        self.model = "fake-gemini"
        self.prompts = []

    def generate_json(self, prompt):
        self.prompts.append(prompt)
        return self.payload


class FakeSandbox:
    def __init__(self, result: SandboxResult):
        self.result = result
        self.calls = []

    def evaluate(self, **kwargs):
        self.calls.append(kwargs)
        return self.result


def _create_assessment(
    db,
    entities,
    *,
    payload=None,
    mcq_count=2,
    coding_count=1,
    resume=None,
):
    gemini = FakeGemini(payload or _valid_payload(mcq_count, coding_count))
    assessment = assessment_service.generate_assessment(
        db=db,
        job=entities.job,
        recruiter=entities.recruiter,
        resume=resume if resume is not None else entities.resume,
        mcq_count=mcq_count,
        coding_count=coding_count,
        gemini_client=gemini,
    )
    return assessment, gemini


def _answer(question, selected_option=None, answer_text=None):
    return SimpleNamespace(
        question_id=question.id,
        selected_option=selected_option,
        answer_text=answer_text,
    )


# =========================================================================== #
# Gemini client and JSON extraction                                           #
# =========================================================================== #
class TestGeminiClient:
    def test_missing_api_key_is_configuration_error(self):
        client = GeminiClient(api_key="")
        with pytest.raises(GeminiConfigurationError):
            client.generate_json("prompt")

    def test_valid_response_is_parsed(self):
        response = MagicMock()
        response.status_code = 200
        response.json.return_value = {
            "candidates": [
                {"content": {"parts": [{"text": json.dumps({"ok": True})}]}}
            ]
        }
        with patch("app.services.gemini_client.httpx.post", return_value=response) as post:
            result = GeminiClient(api_key="test-key").generate_json("prompt")
        assert result == {"ok": True}
        assert post.call_args.kwargs["params"] == {"key": "test-key"}

    def test_timeout_is_reported(self):
        with patch(
            "app.services.gemini_client.httpx.post",
            side_effect=httpx.TimeoutException("timed out"),
        ):
            with pytest.raises(GeminiTimeoutError):
                GeminiClient(api_key="test-key").generate_json("prompt")

    def test_http_failure_is_reported(self):
        response = MagicMock()
        response.status_code = 429
        with patch("app.services.gemini_client.httpx.post", return_value=response):
            with pytest.raises(GeminiAPIError):
                GeminiClient(api_key="test-key").generate_json("prompt")

    def test_empty_candidates_is_invalid_response(self):
        response = MagicMock()
        response.status_code = 200
        response.json.return_value = {"candidates": []}
        with patch("app.services.gemini_client.httpx.post", return_value=response):
            with pytest.raises(GeminiResponseError):
                GeminiClient(api_key="test-key").generate_json("prompt")

    def test_extract_json_handles_fences_and_prose(self):
        assert extract_json("```json\n{\"a\": 1}\n```") == {"a": 1}
        assert extract_json("Here is the result: {\"b\": 2}") == {"b": 2}

    def test_extract_json_rejects_non_json(self):
        with pytest.raises(GeminiResponseError):
            extract_json("not json at all")


# =========================================================================== #
# DeepSeek client and provider factory                                        #
# =========================================================================== #
class TestDeepSeekClient:
    def test_missing_api_key_is_configuration_error(self):
        client = DeepSeekClient(api_key="")
        with pytest.raises(LLMConfigurationError):
            client.generate_json("prompt")

    def test_valid_response_is_parsed(self):
        response = MagicMock()
        response.status_code = 200
        response.json.return_value = {
            "choices": [
                {"message": {"content": json.dumps({"ok": True})}}
            ]
        }
        with patch(
            "app.services.deepseek_client.httpx.post", return_value=response
        ) as post:
            result = DeepSeekClient(api_key="test-key").generate_json("prompt")
        assert result == {"ok": True}
        headers = post.call_args.kwargs["headers"]
        assert headers["Authorization"] == "Bearer test-key"
        payload = post.call_args.kwargs["json"]
        assert payload["model"] == "deepseek-chat"
        assert payload["response_format"] == {"type": "json_object"}
        assert payload["stream"] is False

    def test_timeout_is_reported(self):
        with patch(
            "app.services.deepseek_client.httpx.post",
            side_effect=httpx.TimeoutException("timed out"),
        ):
            with pytest.raises(LLMTimeoutError):
                DeepSeekClient(api_key="test-key").generate_json("prompt")

    def test_http_failure_is_reported(self):
        response = MagicMock()
        response.status_code = 401
        with patch(
            "app.services.deepseek_client.httpx.post", return_value=response
        ):
            with pytest.raises(LLMAPIError):
                DeepSeekClient(api_key="test-key").generate_json("prompt")

    def test_empty_choices_is_invalid_response(self):
        response = MagicMock()
        response.status_code = 200
        response.json.return_value = {"choices": []}
        with patch(
            "app.services.deepseek_client.httpx.post", return_value=response
        ):
            with pytest.raises(LLMResponseError):
                DeepSeekClient(api_key="test-key").generate_json("prompt")

    def test_invalid_json_content_is_reported(self):
        response = MagicMock()
        response.status_code = 200
        response.json.return_value = {
            "choices": [{"message": {"content": "not json"}}]
        }
        with patch(
            "app.services.deepseek_client.httpx.post", return_value=response
        ):
            with pytest.raises(LLMResponseError):
                DeepSeekClient(api_key="test-key").generate_json("prompt")

    def test_factory_returns_configured_provider(self):
        assert isinstance(
            get_llm_client(provider="gemini", api_key="test-key"), GeminiClient
        )
        assert isinstance(
            get_llm_client(provider="deepseek", api_key="test-key"), DeepSeekClient
        )

    def test_factory_rejects_unknown_provider(self):
        with pytest.raises(LLMConfigurationError):
            get_llm_client(provider="unknown")


# =========================================================================== #
# Generation validation                                                       #
# =========================================================================== #
class TestGenerationValidation:
    def test_valid_payload_is_normalized(self):
        questions = assessment_service.validate_generation_payload(
            _valid_payload(), mcq_count=2, coding_count=1
        )
        assert len(questions) == 3
        assert questions[0]["question_type"] == QuestionType.MCQ
        assert questions[0]["options"][0]["key"] == "A"
        assert questions[1]["options"][0]["key"] == "A"  # string options normalized
        assert questions[1]["correct_answer"] == "A"      # text answer mapped to key
        assert questions[2]["question_type"] == QuestionType.CODING
        assert questions[2]["language"] == "python"

    def test_more_questions_than_requested_are_truncated(self):
        questions = assessment_service.validate_generation_payload(
            _valid_payload(mcq_count=3, coding_count=1),
            mcq_count=2,
            coding_count=0,
        )
        assert len(questions) == 2

    def test_missing_requested_mcq_type_raises(self):
        with pytest.raises(assessment_service.AssessmentGenerationError):
            assessment_service.validate_generation_payload(
                {"mcq_questions": [], "coding_questions": _valid_payload()["coding_questions"]},
                mcq_count=2,
                coding_count=1,
            )

    def test_invalid_correct_answer_raises(self):
        payload = _valid_payload(mcq_count=1, coding_count=0)
        payload["mcq_questions"][0]["correct_answer"] = "Z"
        with pytest.raises(assessment_service.AssessmentGenerationError):
            assessment_service.validate_generation_payload(payload, 1, 0)

    def test_duplicate_option_keys_raise(self):
        payload = _valid_payload(mcq_count=1, coding_count=0)
        payload["mcq_questions"][0]["options"] = [
            {"key": "A", "text": "One"},
            {"key": "a", "text": "Two"},
        ]
        with pytest.raises(assessment_service.AssessmentGenerationError):
            assessment_service.validate_generation_payload(payload, 1, 0)

    def test_coding_requires_test_cases(self):
        payload = _valid_payload(mcq_count=0, coding_count=1)
        payload["coding_questions"][0]["test_cases"] = []
        with pytest.raises(assessment_service.AssessmentGenerationError):
            assessment_service.validate_generation_payload(payload, 0, 1)

    def test_coding_rejects_unsupported_language(self):
        payload = _valid_payload(mcq_count=0, coding_count=1)
        payload["coding_questions"][0]["language"] = "javascript"
        with pytest.raises(assessment_service.AssessmentGenerationError):
            assessment_service.validate_generation_payload(payload, 0, 1)

    def test_zero_requested_questions_raises(self):
        with pytest.raises(assessment_service.AssessmentGenerationError):
            assessment_service.validate_generation_payload({}, 0, 0)


# =========================================================================== #
# Generation persistence                                                      #
# =========================================================================== #
class TestGenerationPersistence:
    def test_assessment_and_questions_are_stored(self, db_session):
        entities = _setup_entities(db_session)
        assessment, gemini = _create_assessment(db_session, entities)

        assert assessment.id is not None
        assert len(assessment.questions) == 3
        assert assessment.generation_model == "fake-gemini"
        assert assessment.generation_prompt_version
        assert "Python" in gemini.prompts[0]
        assert "FastAPI" in gemini.prompts[0]
        assert db_session.query(Assessment).count() == 1

    def test_invalid_llm_output_is_not_persisted(self, db_session):
        entities = _setup_entities(db_session)
        invalid_payload = _valid_payload(mcq_count=1, coding_count=0)
        invalid_payload["mcq_questions"][0]["correct_answer"] = "Z"

        with pytest.raises(assessment_service.AssessmentGenerationError):
            _create_assessment(
                db_session,
                entities,
                payload=invalid_payload,
                mcq_count=1,
                coding_count=0,
            )

        assert db_session.query(Assessment).count() == 0

    def test_public_serializer_hides_answers_and_hidden_tests(self, db_session):
        entities = _setup_entities(db_session)
        assessment, _ = _create_assessment(db_session, entities)
        mcq = assessment.questions[0]
        coding = assessment.questions[2]

        public_mcq = assessment_service.serialize_question_public(mcq)
        public_coding = assessment_service.serialize_question_public(coding)

        assert "correct_answer" not in public_mcq
        assert "explanation" not in public_mcq
        assert len(public_coding["sample_test_cases"]) == 1
        assert public_coding["sample_test_cases"][0]["hidden"] is False
        assert "test_cases" not in public_coding


# =========================================================================== #
# Deterministic MCQ scoring                                                   #
# =========================================================================== #
class TestMcqScoring:
    def test_two_of_three_correct_scores_deterministically(self, db_session):
        entities = _setup_entities(db_session)
        assessment, _ = _create_assessment(
            db_session,
            entities,
            payload=_valid_payload(mcq_count=3, coding_count=0),
            mcq_count=3,
            coding_count=0,
        )
        attempt = assessment_service.start_attempt(db_session, assessment, entities.candidate)
        answers = [
            _answer(assessment.questions[0], "A"),   # correct
            _answer(assessment.questions[1], "B"),   # incorrect
            # question 3 unanswered
        ]
        result = assessment_service.submit_attempt(db_session, attempt, answers)

        assert result.score == pytest.approx(33.33)
        assert result.mcq_score == pytest.approx(33.33)
        assert result.coding_score is None
        assert result.earned_points == pytest.approx(1.0)
        assert result.total_points == pytest.approx(3.0)
        assert result.status == AttemptStatus.EVALUATED
        assert len(result.result_details["answers"]) == 3

    def test_same_answers_produce_same_score(self, db_session):
        entities = _setup_entities(db_session)
        assessment, _ = _create_assessment(
            db_session,
            entities,
            payload=_valid_payload(mcq_count=2, coding_count=0),
            mcq_count=2,
            coding_count=0,
        )
        first = assessment_service.start_attempt(db_session, assessment, entities.candidate)
        assessment_service.submit_attempt(
            db_session,
            first,
            [_answer(assessment.questions[0], "A"), _answer(assessment.questions[1], "A")],
        )

        second = assessment_service.start_attempt(db_session, assessment, entities.other_candidate)
        assessment_service.submit_attempt(
            db_session,
            second,
            [_answer(assessment.questions[0], "A"), _answer(assessment.questions[1], "A")],
        )

        assert first.score == second.score == pytest.approx(100.0)

    def test_invalid_option_is_rejected(self, db_session):
        entities = _setup_entities(db_session)
        assessment, _ = _create_assessment(
            db_session,
            entities,
            payload=_valid_payload(mcq_count=1, coding_count=0),
            mcq_count=1,
            coding_count=0,
        )
        attempt = assessment_service.start_attempt(db_session, assessment, entities.candidate)
        with pytest.raises(Exception) as exc_info:
            assessment_service.submit_attempt(
                db_session,
                attempt,
                [_answer(assessment.questions[0], "Z")],
            )
        assert getattr(exc_info.value, "status_code", None) == 400

    def test_question_from_another_assessment_is_rejected(self, db_session):
        entities = _setup_entities(db_session)
        assessment, _ = _create_assessment(
            db_session,
            entities,
            payload=_valid_payload(mcq_count=1, coding_count=0),
            mcq_count=1,
            coding_count=0,
        )
        other, _ = _create_assessment(
            db_session,
            entities,
            payload=_valid_payload(mcq_count=1, coding_count=0),
            mcq_count=1,
            coding_count=0,
        )
        attempt = assessment_service.start_attempt(db_session, assessment, entities.candidate)
        with pytest.raises(Exception) as exc_info:
            assessment_service.submit_attempt(
                db_session,
                attempt,
                [_answer(other.questions[0], "A")],
            )
        assert getattr(exc_info.value, "status_code", None) == 400


# =========================================================================== #
# Coding evaluation and sandbox behavior                                      #
# =========================================================================== #
class TestCodingScoring:
    def test_passed_coding_tests_are_awarded_full_points(self, db_session):
        entities = _setup_entities(db_session)
        assessment, _ = _create_assessment(db_session, entities)
        attempt = assessment_service.start_attempt(db_session, assessment, entities.candidate)
        sandbox = FakeSandbox(
            SandboxResult(status="passed", passed_tests=2, total_tests=2)
        )
        result = assessment_service.submit_attempt(
            db_session,
            attempt,
            [
                _answer(assessment.questions[0], "A"),
                _answer(assessment.questions[1], "A"),
                _answer(assessment.questions[2], answer_text="def add(a,b): return a+b"),
            ],
            sandbox=sandbox,
        )
        assert result.score == pytest.approx(100.0)
        assert result.coding_score == pytest.approx(100.0)
        assert result.status == AttemptStatus.EVALUATED
        assert sandbox.calls

    def test_partial_coding_tests_are_scored_proportionally(self, db_session):
        entities = _setup_entities(db_session)
        assessment, _ = _create_assessment(db_session, entities)
        attempt = assessment_service.start_attempt(db_session, assessment, entities.candidate)
        sandbox = FakeSandbox(
            SandboxResult(status="failed", passed_tests=1, total_tests=2)
        )
        result = assessment_service.submit_attempt(
            db_session,
            attempt,
            [
                _answer(assessment.questions[0], "A"),
                _answer(assessment.questions[1], "A"),
                _answer(assessment.questions[2], answer_text="def add(a,b): return a+b"),
            ],
            sandbox=sandbox,
        )
        # MCQ 2/2 + coding 2.5/5 => 4.5 / 7 = 64.29
        assert result.score == pytest.approx(64.29)
        assert result.coding_score == pytest.approx(50.0)
        assert result.earned_points == pytest.approx(4.5)

    def test_unavailable_sandbox_excludes_coding_from_score(self, db_session):
        entities = _setup_entities(db_session)
        assessment, _ = _create_assessment(db_session, entities)
        attempt = assessment_service.start_attempt(db_session, assessment, entities.candidate)
        sandbox = FakeSandbox(
            SandboxResult(
                status="sandbox_unavailable",
                total_tests=2,
                message="Sandbox disabled.",
            )
        )
        result = assessment_service.submit_attempt(
            db_session,
            attempt,
            [
                _answer(assessment.questions[0], "A"),
                _answer(assessment.questions[1], "A"),
                _answer(assessment.questions[2], answer_text="def add(a,b): return a+b"),
            ],
            sandbox=sandbox,
        )
        assert result.score == pytest.approx(100.0)  # MCQ only
        assert result.coding_score is None
        assert result.status == AttemptStatus.PARTIALLY_EVALUATED
        assert result.result_details["sandbox_available"] is False
        assert result.result_details["limitations"]
        assert "not treated as incorrect" in result.result_details["limitations"][-1]

    def test_only_coding_and_no_sandbox_returns_no_score(self, db_session):
        entities = _setup_entities(db_session)
        assessment, _ = _create_assessment(
            db_session,
            entities,
            payload=_valid_payload(mcq_count=0, coding_count=1),
            mcq_count=0,
            coding_count=1,
        )
        attempt = assessment_service.start_attempt(db_session, assessment, entities.candidate)
        sandbox = FakeSandbox(
            SandboxResult(status="sandbox_unavailable", total_tests=2, message="Disabled.")
        )
        result = assessment_service.submit_attempt(
            db_session,
            attempt,
            [_answer(assessment.questions[0], answer_text="def add(a,b): return a+b")],
            sandbox=sandbox,
        )
        assert result.score is None
        assert result.coding_score is None
        assert result.status == AttemptStatus.PARTIALLY_EVALUATED

    def test_disabled_sandbox_never_executes_code(self):
        sandbox = CodingSandbox(enabled=False)
        result = sandbox.evaluate(
            code="print('hello')",
            test_cases=[{"input": [], "expected": None}],
            function_name="solve",
        )
        assert result.status == "sandbox_unavailable"
        assert "disabled" in result.message.lower()

    def test_docker_command_uses_restrictive_flags(self):
        completed = MagicMock()
        completed.returncode = 0
        completed.stdout = '__HIREMINDS_RESULT__[{"index": 0, "passed": true}]'
        completed.stderr = ""
        sandbox = CodingSandbox(enabled=True, backend="docker", image="python:3.12-slim")
        with patch("app.services.coding_sandbox.shutil.which", return_value="/usr/bin/docker"), patch(
            "app.services.coding_sandbox.subprocess.run", return_value=completed
        ) as run:
            result = sandbox.evaluate(
                code="def add(a,b): return a+b",
                test_cases=[{"input": [1, 2], "expected": 3}],
                function_name="add",
            )
        command = run.call_args.args[0]
        assert result.status == "passed"
        assert "--network" in command and "none" in command
        assert "--read-only" in command
        assert "--memory" in command
        assert "--pids-limit" in command
        assert "--cap-drop" in command and "ALL" in command
        assert "--security-opt" in command and "no-new-privileges" in command
        assert "--user" in command and "65534:65534" in command
        assert any(":ro" in part for part in command)
        assert command[-3:] == ["-I", "-B", "/workspace/harness.py"]

    def test_harness_contains_code_and_parses_result(self):
        harness = build_harness("def add(a,b): return a+b", [{"input": [1, 2], "expected": 3}], "add")
        assert "def add(a,b): return a+b" in harness
        assert "__HIREMINDS_RESULT__" in harness
        parsed = _parse_harness_output(
            '__HIREMINDS_RESULT__[{"index": 0, "passed": true}]'
        )
        assert parsed == [{"index": 0, "passed": True}]


# =========================================================================== #
# Ownership rules                                                             #
# =========================================================================== #
class TestOwnership:
    def test_assessment_owner_rules(self, db_session):
        entities = _setup_entities(db_session)
        assessment, _ = _create_assessment(db_session, entities)

        assessment_service.authorize_assessment_owner(assessment, entities.recruiter)
        assessment_service.authorize_assessment_owner(assessment, entities.admin)

        with pytest.raises(Exception) as other:
            assessment_service.authorize_assessment_owner(assessment, entities.other_recruiter)
        assert other.value.status_code == 403

        with pytest.raises(Exception) as candidate:
            assessment_service.authorize_assessment_owner(assessment, entities.candidate)
        assert candidate.value.status_code == 403

    def test_attempt_submit_and_result_rules(self, db_session):
        entities = _setup_entities(db_session)
        assessment, _ = _create_assessment(db_session, entities)
        attempt = assessment_service.start_attempt(db_session, assessment, entities.candidate)

        assessment_service.authorize_attempt_submit(attempt, entities.candidate)
        assessment_service.authorize_attempt_result(attempt, assessment, entities.candidate)
        assessment_service.authorize_attempt_result(attempt, assessment, entities.recruiter)
        assessment_service.authorize_attempt_result(attempt, assessment, entities.admin)

        with pytest.raises(Exception) as other_candidate:
            assessment_service.authorize_attempt_submit(attempt, entities.other_candidate)
        assert other_candidate.value.status_code == 403

        with pytest.raises(Exception) as other_recruiter:
            assessment_service.authorize_attempt_result(
                attempt, assessment, entities.other_recruiter
            )
        assert other_recruiter.value.status_code == 403


# =========================================================================== #
# API integration tests                                                       #
# =========================================================================== #
class TestAssessmentApi:
    def _setup(self, api_context):
        client, db, set_user = api_context
        entities = _setup_entities(db)
        assessment, _ = _create_assessment(db, entities)
        return client, db, set_user, entities, assessment

    def test_candidate_start_hides_answers_and_hidden_tests(self, api_context):
        client, db, set_user, entities, assessment = self._setup(api_context)
        set_user(entities.candidate)
        response = client.post(f"/api/v1/assessments/{assessment.id}/start")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "in_progress"
        assert len(data["questions"]) == 3
        serialized = json.dumps(data)
        assert "correct_answer" not in serialized
        assert "explanation" not in serialized
        coding = next(q for q in data["questions"] if q["question_type"] == "coding")
        assert len(coding["sample_test_cases"]) == 1
        assert coding["sample_test_cases"][0]["hidden"] is False

    def test_candidate_cannot_view_recruiter_assessment(self, api_context):
        client, _, set_user, entities, assessment = self._setup(api_context)
        set_user(entities.candidate)
        response = client.get(f"/api/v1/assessments/{assessment.id}")
        assert response.status_code == 403

    def test_recruiter_can_view_full_assessment(self, api_context):
        client, _, set_user, entities, assessment = self._setup(api_context)
        set_user(entities.recruiter)
        response = client.get(f"/api/v1/assessments/{assessment.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["questions"][0]["correct_answer"] == "A"
        coding = next(q for q in data["questions"] if q["question_type"] == "coding")
        assert len(coding["test_cases"]) == 2

    def test_submit_and_view_own_result(self, api_context):
        client, _, set_user, entities, assessment = self._setup(api_context)
        set_user(entities.candidate)
        start = client.post(f"/api/v1/assessments/{assessment.id}/start").json()
        attempt_id = start["attempt_id"]
        mcqs = [q for q in start["questions"] if q["question_type"] == "mcq"]
        coding = next(q for q in start["questions"] if q["question_type"] == "coding")
        answers = [
            {"question_id": mcqs[0]["id"], "selected_option": "A"},
            {"question_id": mcqs[1]["id"], "selected_option": "A"},
            {"question_id": coding["id"], "answer_text": "def add(a,b): return a+b"},
        ]
        with patch.object(
            CodingSandbox,
            "evaluate",
            return_value=SandboxResult(status="passed", passed_tests=2, total_tests=2),
        ):
            response = client.post(
                f"/api/v1/assessments/attempts/{attempt_id}/submit",
                json={"answers": answers},
            )
        assert response.status_code == 200
        result = response.json()
        assert result["score"] == pytest.approx(100.0)
        assert result["status"] == "evaluated"
        # Candidate-facing results must not reveal grading secrets.
        assert "correct_answer" not in json.dumps(result)

        result_response = client.get(f"/api/v1/assessments/attempts/{attempt_id}/result")
        assert result_response.status_code == 200
        assert result_response.json()["score"] == pytest.approx(100.0)
        assert "correct_answer" not in json.dumps(result_response.json())

    def test_other_candidate_cannot_view_result(self, api_context):
        client, db, set_user, entities, assessment = self._setup(api_context)
        set_user(entities.candidate)
        attempt = assessment_service.start_attempt(db, assessment, entities.candidate)
        assessment_service.submit_attempt(
            db,
            attempt,
            [_answer(assessment.questions[0], "A")],
            sandbox=FakeSandbox(
                SandboxResult(status="sandbox_unavailable", total_tests=2, message="Disabled.")
            ),
        )

        set_user(entities.other_candidate)
        response = client.get(f"/api/v1/assessments/attempts/{attempt.id}/result")
        assert response.status_code == 403

    def test_other_recruiter_cannot_view_result(self, api_context):
        client, db, set_user, entities, assessment = self._setup(api_context)
        attempt = assessment_service.start_attempt(db, assessment, entities.candidate)
        assessment_service.submit_attempt(
            db,
            attempt,
            [_answer(assessment.questions[0], "A")],
            sandbox=FakeSandbox(
                SandboxResult(status="sandbox_unavailable", total_tests=2, message="Disabled.")
            ),
        )

        set_user(entities.other_recruiter)
        response = client.get(f"/api/v1/assessments/attempts/{attempt.id}/result")
        assert response.status_code == 403

    def test_recruiter_owner_can_view_result_and_attempts(self, api_context):
        client, db, set_user, entities, assessment = self._setup(api_context)
        attempt = assessment_service.start_attempt(db, assessment, entities.candidate)
        assessment_service.submit_attempt(
            db,
            attempt,
            [_answer(assessment.questions[0], "A")],
            sandbox=FakeSandbox(
                SandboxResult(status="sandbox_unavailable", total_tests=2, message="Disabled.")
            ),
        )

        set_user(entities.recruiter)
        result = client.get(f"/api/v1/assessments/attempts/{attempt.id}/result")
        assert result.status_code == 200
        # Recruiters reviewing an owned assessment may see grading details.
        assert "correct_answer" in json.dumps(result.json())
        listing = client.get(f"/api/v1/assessments/{assessment.id}/attempts")
        assert listing.status_code == 200
        assert listing.json()["total"] == 1

    def test_candidate_cannot_generate_assessment(self, api_context):
        client, _, set_user, entities, _ = self._setup(api_context)
        set_user(entities.candidate)
        response = client.post(
            "/api/v1/assessments/generate",
            json={"job_id": entities.job.id, "mcq_count": 1, "coding_count": 0},
        )
        assert response.status_code == 403

    def test_generate_endpoint_requires_owned_job(self, api_context):
        client, _, set_user, entities, _ = self._setup(api_context)
        set_user(entities.other_recruiter)
        response = client.post(
            "/api/v1/assessments/generate",
            json={"job_id": entities.job.id, "mcq_count": 1, "coding_count": 0},
        )
        assert response.status_code == 403

    def test_generate_endpoint_with_mocked_llm(self, api_context):
        client, _, set_user, entities, _ = self._setup(api_context)
        set_user(entities.recruiter)
        with patch.object(
            assessment_service,
            "get_llm_client",
            return_value=FakeGemini(_valid_payload(mcq_count=1, coding_count=0)),
        ):
            response = client.post(
                "/api/v1/assessments/generate",
                json={
                    "job_id": entities.job.id,
                    "resume_id": entities.resume.id,
                    "mcq_count": 1,
                    "coding_count": 0,
                },
            )
        assert response.status_code == 201
        data = response.json()
        assert data["question_count"] == 1
        assert data["questions"][0]["correct_answer"] == "A"

    def test_generate_endpoint_missing_api_key_returns_503(self, api_context):
        client, _, set_user, entities, _ = self._setup(api_context)
        set_user(entities.recruiter)
        with patch.object(
            assessment_service,
            "get_llm_client",
            side_effect=GeminiConfigurationError("No key"),
        ):
            response = client.post(
                "/api/v1/assessments/generate",
                json={"job_id": entities.job.id, "mcq_count": 1, "coding_count": 0},
            )
        assert response.status_code == 503

    def test_generate_endpoint_invalid_llm_output_returns_422(self, api_context):
        client, _, set_user, entities, _ = self._setup(api_context)
        set_user(entities.recruiter)
        invalid = _valid_payload(mcq_count=1, coding_count=0)
        invalid["mcq_questions"][0]["correct_answer"] = "Z"
        with patch.object(
            assessment_service,
            "get_llm_client",
            return_value=FakeGemini(invalid),
        ):
            response = client.post(
                "/api/v1/assessments/generate",
                json={"job_id": entities.job.id, "mcq_count": 1, "coding_count": 0},
            )
        assert response.status_code == 422

    def test_generate_endpoint_rejects_non_applicant_resume(self, api_context):
        client, db, set_user, entities, _ = self._setup(api_context)
        foreign_resume = Resume(
            user_id=entities.other_candidate.id,
            filename="other.pdf",
            file_path="/tmp/other.pdf",
            file_size=10,
            content_hash="hash-other",
            raw_text="Other candidate",
            extracted_skills=["Python"],
            extracted_education=[],
            extracted_experience={},
            extracted_projects=[],
        )
        db.add(foreign_resume)
        db.commit()

        set_user(entities.recruiter)
        response = client.post(
            "/api/v1/assessments/generate",
            json={
                "job_id": entities.job.id,
                "resume_id": foreign_resume.id,
                "mcq_count": 1,
                "coding_count": 0,
            },
        )
        assert response.status_code == 403

    def test_second_submission_is_conflict(self, api_context):
        client, _, set_user, entities, assessment = self._setup(api_context)
        set_user(entities.candidate)
        start = client.post(f"/api/v1/assessments/{assessment.id}/start").json()
        attempt_id = start["attempt_id"]
        answers = [
            {"question_id": start["questions"][0]["id"], "selected_option": "A"},
        ]
        with patch.object(
            CodingSandbox,
            "evaluate",
            return_value=SandboxResult(
                status="sandbox_unavailable", total_tests=2, message="Disabled."
            ),
        ):
            first = client.post(
                f"/api/v1/assessments/attempts/{attempt_id}/submit",
                json={"answers": answers},
            )
            assert first.status_code == 200
            second = client.post(
                f"/api/v1/assessments/attempts/{attempt_id}/submit",
                json={"answers": answers},
            )
        assert second.status_code == 409
