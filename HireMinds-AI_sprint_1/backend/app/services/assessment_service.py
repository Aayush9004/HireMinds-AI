"""
Phase 8: Technical assessment generation, evaluation and authorization.

Design rules
------------
* LLM output (Gemini or DeepSeek) is treated as untrusted input and validated
  strictly before it is persisted.
* MCQ scoring is deterministic: compare the submitted option key with the
  stored correct answer.
* Coding submissions are evaluated only through ``CodingSandbox``. If no secure
  sandbox is configured, the submission is stored but marked not evaluated; it
  is never executed in the FastAPI process and is not counted as an incorrect
  answer.
* Candidate-facing serializers omit correct answers and hidden test cases.
* Recruiters can access only assessments they created; candidates can access
  only their own attempts. Admins can access everything.
"""
from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence, Tuple

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.assessment import (
    Assessment,
    AssessmentAnswer,
    AssessmentAttempt,
    AssessmentQuestion,
    AssessmentStatus,
    AttemptStatus,
    QuestionType,
)
from app.models.job import Job
from app.models.resume import Resume
from app.models.user import User, UserRole
from app.services.coding_sandbox import CodingSandbox, SandboxResult
from app.services.llm_client import BaseLLMClient, get_llm_client

logger = logging.getLogger(__name__)

_ALLOWED_DIFFICULTIES = {"easy", "medium", "hard"}
_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_OPTION_KEYS = "ABCDEFGHIJ"


class AssessmentGenerationError(Exception):
    """Raised when the LLM output cannot be validated as a usable assessment."""


# --------------------------------------------------------------------------- #
# Small helpers                                                                #
# --------------------------------------------------------------------------- #
def _now() -> datetime:
    return datetime.now(timezone.utc)


def _as_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _as_positive_float(value: Any, default: float, maximum: float = 100.0) -> float:
    if value is None:
        return default
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise AssessmentGenerationError(f"Invalid points value: {value!r}") from exc
    if number <= 0 or number > maximum:
        raise AssessmentGenerationError(
            f"Question points must be between 0 and {maximum:g}; got {number:g}."
        )
    return round(number, 2)


def _as_int_in_range(value: Any, default: int, minimum: int, maximum: int) -> int:
    if value is None:
        return default
    try:
        number = int(value)
    except (TypeError, ValueError) as exc:
        raise AssessmentGenerationError(f"Invalid numeric value: {value!r}") from exc
    return max(minimum, min(maximum, number))


def _normalize_difficulty(value: Any) -> str:
    difficulty = _as_text(value).lower()
    return difficulty if difficulty in _ALLOWED_DIFFICULTIES else "medium"


def _option_key(index: int) -> str:
    return _OPTION_KEYS[index] if index < len(_OPTION_KEYS) else f"OPT{index + 1}"


def _candidate_skills(resume: Optional[Resume]) -> List[str]:
    if resume is None:
        return []
    skills = list(getattr(resume, "extracted_skills", None) or [])
    if getattr(resume, "is_reviewed_by_candidate", False):
        corrected = getattr(resume, "candidate_corrected_data", None) or {}
        corrected_skills = corrected.get("skills") if isinstance(corrected, dict) else None
        if corrected_skills:
            skills = list(corrected_skills)
    return [str(skill).strip() for skill in skills if str(skill).strip()]


def _normalize_options(raw_options: Any) -> List[Dict[str, str]]:
    if isinstance(raw_options, dict):
        items = list(raw_options.items())
        options = []
        for index, (key, value) in enumerate(items):
            options.append(
                {
                    "key": _as_text(key) or _option_key(index),
                    "text": _as_text(value),
                }
            )
    elif isinstance(raw_options, list):
        options = []
        for index, item in enumerate(raw_options):
            if isinstance(item, dict):
                key = (
                    item.get("key")
                    or item.get("id")
                    or item.get("label")
                    or _option_key(index)
                )
                text = (
                    item.get("text")
                    or item.get("value")
                    or item.get("option")
                    or item.get("content")
                )
            else:
                key = _option_key(index)
                text = item
            options.append({"key": _as_text(key), "text": _as_text(text)})
    else:
        raise AssessmentGenerationError("MCQ options must be a list or object.")

    if len(options) < 2 or len(options) > 6:
        raise AssessmentGenerationError("MCQ questions must have between 2 and 6 options.")

    normalized: List[Dict[str, str]] = []
    seen_keys = set()
    for option in options:
        key = option["key"].upper()
        text = option["text"]
        if not key or not text:
            raise AssessmentGenerationError("Every MCQ option needs a key and non-empty text.")
        if key in seen_keys:
            raise AssessmentGenerationError(f"Duplicate MCQ option key: {key}.")
        seen_keys.add(key)
        normalized.append({"key": key, "text": text})
    return normalized


def _normalize_correct_answer(raw_answer: Any, options: List[Dict[str, str]]) -> str:
    if raw_answer is None:
        raise AssessmentGenerationError("MCQ question is missing a correct answer.")

    if isinstance(raw_answer, int) and not isinstance(raw_answer, bool):
        if 0 <= raw_answer < len(options):
            return options[raw_answer]["key"]
        if 1 <= raw_answer <= len(options):
            return options[raw_answer - 1]["key"]
        raise AssessmentGenerationError(
            f"Correct-answer index {raw_answer} is outside the option range."
        )

    answer_text = _as_text(raw_answer)
    if not answer_text:
        raise AssessmentGenerationError("MCQ correct answer is empty.")

    for option in options:
        if answer_text.upper() == option["key"]:
            return option["key"]
    for option in options:
        if answer_text.lower() == option["text"].lower():
            return option["key"]

    raise AssessmentGenerationError(
        f"Correct answer {answer_text!r} does not match any option key or text."
    )


def _normalize_test_cases(raw_cases: Any) -> List[Dict[str, Any]]:
    if not isinstance(raw_cases, list) or not raw_cases:
        raise AssessmentGenerationError("Coding questions need at least one test case.")

    normalized: List[Dict[str, Any]] = []
    for index, raw_case in enumerate(raw_cases[:20]):
        if not isinstance(raw_case, dict):
            raise AssessmentGenerationError(f"Test case {index} must be an object.")
        if "input" not in raw_case:
            raise AssessmentGenerationError(f"Test case {index} is missing 'input'.")
        if "expected" not in raw_case:
            raise AssessmentGenerationError(f"Test case {index} is missing 'expected'.")
        normalized.append(
            {
                "input": raw_case.get("input"),
                "expected": raw_case.get("expected"),
                "hidden": bool(raw_case.get("hidden", False)),
            }
        )
    return normalized


def _validate_mcq(raw: Any, index: int) -> Dict[str, Any]:
    if not isinstance(raw, dict):
        raise AssessmentGenerationError(f"MCQ question {index} must be an object.")

    prompt = _as_text(
        raw.get("prompt") or raw.get("question") or raw.get("text") or raw.get("stem")
    )
    if not prompt:
        raise AssessmentGenerationError(f"MCQ question {index} is missing a prompt.")

    options = _normalize_options(raw.get("options"))
    correct_answer = _normalize_correct_answer(
        raw.get("correct_answer")
        if "correct_answer" in raw
        else raw.get("answer") or raw.get("correct_option"),
        options,
    )

    return {
        "question_type": QuestionType.MCQ,
        "prompt": prompt,
        "options": options,
        "correct_answer": correct_answer,
        "explanation": _as_text(raw.get("explanation")) or None,
        "skill_tag": _as_text(raw.get("skill_tag") or raw.get("skill")) or None,
        "difficulty": _normalize_difficulty(raw.get("difficulty")),
        "points": _as_positive_float(raw.get("points"), default=1.0),
        "language": None,
        "function_name": None,
        "starter_code": None,
        "test_cases": None,
        "time_limit_ms": None,
        "memory_limit_mb": None,
    }


def _validate_coding(raw: Any, index: int) -> Dict[str, Any]:
    if not isinstance(raw, dict):
        raise AssessmentGenerationError(f"Coding question {index} must be an object.")

    prompt = _as_text(
        raw.get("prompt") or raw.get("question") or raw.get("text") or raw.get("description")
    )
    if not prompt:
        raise AssessmentGenerationError(f"Coding question {index} is missing a prompt.")

    language = _as_text(raw.get("language") or "python").lower()
    if language != "python":
        raise AssessmentGenerationError(
            f"Coding question {index} uses unsupported language {language!r}; only Python is supported."
        )

    function_name = _as_text(raw.get("function_name") or raw.get("function"))
    if not function_name or not _IDENTIFIER_RE.match(function_name):
        raise AssessmentGenerationError(
            f"Coding question {index} has an invalid Python function name."
        )

    test_cases = _normalize_test_cases(raw.get("test_cases"))
    starter_code = _as_text(raw.get("starter_code")) or (
        f"def {function_name}(*args):\n    # Write your solution here\n    pass\n"
    )

    return {
        "question_type": QuestionType.CODING,
        "prompt": prompt,
        "options": None,
        "correct_answer": None,
        "explanation": _as_text(raw.get("explanation")) or None,
        "skill_tag": _as_text(raw.get("skill_tag") or raw.get("skill")) or None,
        "difficulty": _normalize_difficulty(raw.get("difficulty")),
        "points": _as_positive_float(raw.get("points"), default=5.0),
        "language": "python",
        "function_name": function_name,
        "starter_code": starter_code,
        "test_cases": test_cases,
        "time_limit_ms": _as_int_in_range(
            raw.get("time_limit_ms"), default=5000, minimum=100, maximum=30000
        ),
        "memory_limit_mb": _as_int_in_range(
            raw.get("memory_limit_mb"), default=256, minimum=64, maximum=2048
        ),
    }


def _split_generated_questions(payload: Any) -> Tuple[List[Any], List[Any]]:
    if isinstance(payload, list):
        combined = payload
        mcq_raw = [
            item
            for item in combined
            if isinstance(item, dict)
            and _as_text(item.get("question_type") or item.get("type")).lower()
            in {"mcq", "multiple_choice", "multiple-choice", "multiple choice"}
        ]
        coding_raw = [
            item
            for item in combined
            if isinstance(item, dict)
            and _as_text(item.get("question_type") or item.get("type")).lower()
            in {"coding", "code", "programming"}
        ]
        if not mcq_raw and not coding_raw:
            mcq_raw = [item for item in combined if isinstance(item, dict) and "options" in item]
            coding_raw = [
                item for item in combined if isinstance(item, dict) and "test_cases" in item
            ]
        return mcq_raw, coding_raw

    if not isinstance(payload, dict):
        raise AssessmentGenerationError("LLM response must be a JSON object or array.")

    mcq_raw = (
        payload.get("mcq_questions")
        or payload.get("mcqs")
        or payload.get("multiple_choice_questions")
        or []
    )
    coding_raw = (
        payload.get("coding_questions")
        or payload.get("coding")
        or payload.get("programming_questions")
        or []
    )

    if not mcq_raw and not coding_raw and isinstance(payload.get("questions"), list):
        return _split_generated_questions(payload["questions"])

    if not isinstance(mcq_raw, list) or not isinstance(coding_raw, list):
        raise AssessmentGenerationError(
            "LLM response must contain lists for mcq_questions and coding_questions."
        )
    return mcq_raw, coding_raw


def validate_generation_payload(
    payload: Any,
    mcq_count: int,
    coding_count: int,
) -> List[Dict[str, Any]]:
    """
    Validate and normalize the LLM's assessment payload.

    Raises ``AssessmentGenerationError`` for any structural, option, answer or
    test-case problem. The returned questions are safe to persist.
    """
    mcq_count = max(0, min(int(mcq_count), settings.ASSESSMENT_MAX_MCQ_QUESTIONS))
    coding_count = max(0, min(int(coding_count), settings.ASSESSMENT_MAX_CODING_QUESTIONS))
    if mcq_count == 0 and coding_count == 0:
        raise AssessmentGenerationError("Request at least one MCQ or coding question.")

    mcq_raw, coding_raw = _split_generated_questions(payload)

    if mcq_count > 0 and not mcq_raw:
        raise AssessmentGenerationError("The LLM did not return any MCQ questions.")
    if coding_count > 0 and not coding_raw:
        raise AssessmentGenerationError("The LLM did not return any coding questions.")

    questions: List[Dict[str, Any]] = []
    for index, raw in enumerate(mcq_raw[:mcq_count]):
        questions.append(_validate_mcq(raw, index))
    for index, raw in enumerate(coding_raw[:coding_count]):
        questions.append(_validate_coding(raw, index))

    if not questions:
        raise AssessmentGenerationError("The LLM returned no usable questions.")
    return questions


# --------------------------------------------------------------------------- #
# Prompt construction                                                          #
# --------------------------------------------------------------------------- #
def build_generation_prompt(
    job: Job,
    candidate_skills: Sequence[str],
    mcq_count: int,
    coding_count: int,
    difficulty: Optional[str] = None,
    additional_instructions: Optional[str] = None,
) -> str:
    """Build a strict JSON-only prompt grounded in the job and candidate skills."""
    required = ", ".join(getattr(job, "required_skills", None) or []) or "Not specified"
    preferred = ", ".join(getattr(job, "preferred_skills", None) or []) or "Not specified"
    candidate_text = ", ".join(candidate_skills) or "No candidate resume provided"
    description = (getattr(job, "description", "") or "")[:6000]
    difficulty_text = difficulty or "mixed"

    instructions = (
        f"\nAdditional recruiter instructions: {additional_instructions.strip()}"
        if additional_instructions and additional_instructions.strip()
        else ""
    )

    return f"""You are an expert technical interviewer creating a fair, job-related assessment.

JOB
Title: {job.title}
Company: {job.company_name}
Required skills: {required}
Preferred skills: {preferred}
Minimum experience: {job.min_experience_years:g} years
Required education: {job.required_education}
Description:
{description}

CANDIDATE SKILLS
{candidate_text}

TASK
Generate exactly {mcq_count} multiple-choice questions and {coding_count} coding questions.
Difficulty: {difficulty_text}.
Questions must test only job-relevant technical knowledge and must not ask about
age, gender, race, religion, caste, nationality, marital status, disability, or
any other protected personal characteristic.
{instructions}

Return ONLY valid JSON with this exact shape (no markdown, no commentary):
{{
  "mcq_questions": [
    {{
      "prompt": "question text",
      "options": [
        {{"key": "A", "text": "option text"}},
        {{"key": "B", "text": "option text"}},
        {{"key": "C", "text": "option text"}},
        {{"key": "D", "text": "option text"}}
      ],
      "correct_answer": "A",
      "explanation": "why the answer is correct",
      "skill_tag": "Python",
      "difficulty": "easy|medium|hard",
      "points": 1
    }}
  ],
  "coding_questions": [
    {{
      "prompt": "coding problem statement",
      "language": "python",
      "function_name": "solve",
      "starter_code": "def solve(*args):\\n    pass",
      "test_cases": [
        {{"input": [1, 2], "expected": 3, "hidden": false}},
        {{"input": [5, 7], "expected": 12, "hidden": true}}
      ],
      "explanation": "approach",
      "skill_tag": "Python",
      "difficulty": "medium",
      "points": 5,
      "time_limit_ms": 5000,
      "memory_limit_mb": 256
    }}
  ]
}}

Rules:
- Every MCQ must have 2-6 unique options and a correct_answer that matches an option key.
- Every coding question must be solvable in Python and include at least one test case.
- Test case "input" is a list of positional arguments; "expected" is the expected return value.
- Do not include any text outside the JSON object.
"""


# --------------------------------------------------------------------------- #
# Generation and persistence                                                   #
# --------------------------------------------------------------------------- #
def generate_assessment(
    db: Session,
    job: Job,
    recruiter: User,
    *,
    resume: Optional[Resume] = None,
    mcq_count: int = 5,
    coding_count: int = 1,
    title: Optional[str] = None,
    duration_minutes: int = 60,
    passing_score: float = 60.0,
    difficulty: Optional[str] = None,
    additional_instructions: Optional[str] = None,
    llm_client: Optional[BaseLLMClient] = None,
    gemini_client: Optional[BaseLLMClient] = None,
) -> Assessment:
    """
    Generate, validate and persist an assessment.

    The provider is selected by ``LLM_PROVIDER`` (Gemini or DeepSeek). A client
    may be injected for tests via ``llm_client`` (or the legacy
    ``gemini_client`` argument). Provider/transport/validation exceptions
    propagate so the endpoint can return an explicit error. No partial
    assessment is committed on failure.
    """
    candidate_skills = _candidate_skills(resume)
    prompt = build_generation_prompt(
        job=job,
        candidate_skills=candidate_skills,
        mcq_count=mcq_count,
        coding_count=coding_count,
        difficulty=difficulty,
        additional_instructions=additional_instructions,
    )
    client = llm_client or gemini_client or get_llm_client()
    payload = client.generate_json(prompt)
    questions = validate_generation_payload(payload, mcq_count, coding_count)

    assessment = Assessment(
        job_id=job.id,
        created_by_id=recruiter.id,
        title=(title or f"{job.title} Technical Assessment").strip()[:200],
        description=(
            f"Generated from the requirements for {job.title} at {job.company_name}."
        ),
        status=AssessmentStatus.ACTIVE,
        duration_minutes=duration_minutes,
        passing_score=passing_score,
        generation_model=client.model,
        generation_prompt_version=settings.ASSESSMENT_PROMPT_VERSION,
    )
    db.add(assessment)
    try:
        db.flush()
        for order_index, question in enumerate(questions):
            db.add(
                AssessmentQuestion(
                    assessment_id=assessment.id,
                    order_index=order_index,
                    **question,
                )
            )
        db.commit()
        db.refresh(assessment)
    except Exception:
        db.rollback()
        raise

    logger.info(
        "Generated assessment id=%s for job=%s with %d questions using %s",
        assessment.id,
        job.id,
        len(questions),
        client.model,
    )
    return assessment


# --------------------------------------------------------------------------- #
# Serialization                                                                #
# --------------------------------------------------------------------------- #
def serialize_question_public(question: AssessmentQuestion) -> Dict[str, Any]:
    """Candidate-safe view. Excludes correct answers and hidden test cases."""
    options: List[Dict[str, str]] = []
    if question.question_type == QuestionType.MCQ and question.options:
        options = [
            {"key": str(option.get("key", "")), "text": str(option.get("text", ""))}
            for option in question.options
            if isinstance(option, dict)
        ]

    sample_test_cases: List[Dict[str, Any]] = []
    if question.question_type == QuestionType.CODING and question.test_cases:
        sample_test_cases = [
            {
                "input": case.get("input"),
                "expected": case.get("expected"),
                "hidden": False,
            }
            for case in question.test_cases
            if isinstance(case, dict) and not case.get("hidden", False)
        ]

    return {
        "id": question.id,
        "question_type": question.question_type,
        "prompt": question.prompt,
        "options": options,
        "points": question.points,
        "skill_tag": question.skill_tag,
        "difficulty": question.difficulty,
        "order_index": question.order_index,
        "language": question.language,
        "function_name": question.function_name,
        "starter_code": question.starter_code,
        "sample_test_cases": sample_test_cases,
        "time_limit_ms": question.time_limit_ms,
        "memory_limit_mb": question.memory_limit_mb,
    }


def serialize_question_admin(question: AssessmentQuestion) -> Dict[str, Any]:
    """Recruiter view. Includes answers, explanations and all test cases."""
    data = serialize_question_public(question)
    data.update(
        {
            "correct_answer": question.correct_answer,
            "explanation": question.explanation,
            "test_cases": [
                {
                    "input": case.get("input"),
                    "expected": case.get("expected"),
                    "hidden": bool(case.get("hidden", False)),
                }
                for case in (question.test_cases or [])
                if isinstance(case, dict)
            ],
        }
    )
    return data


def build_assessment_response(assessment: Assessment) -> Dict[str, Any]:
    questions = [serialize_question_admin(question) for question in assessment.questions]
    return {
        "id": assessment.id,
        "job_id": assessment.job_id,
        "created_by_id": assessment.created_by_id,
        "title": assessment.title,
        "description": assessment.description,
        "status": assessment.status,
        "duration_minutes": assessment.duration_minutes,
        "passing_score": assessment.passing_score,
        "generation_model": assessment.generation_model,
        "generation_prompt_version": assessment.generation_prompt_version,
        "question_count": len(questions),
        "questions": questions,
        "created_at": assessment.created_at,
        "updated_at": assessment.updated_at,
    }


# --------------------------------------------------------------------------- #
# Authorization                                                                #
# --------------------------------------------------------------------------- #
def authorize_assessment_owner(assessment: Assessment, user: User) -> None:
    """Allow the recruiter who created the assessment, or an admin."""
    if user.role == UserRole.ADMIN:
        return
    if user.role == UserRole.RECRUITER and assessment.created_by_id == user.id:
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Access denied: this assessment belongs to another recruiter.",
    )


def authorize_attempt_submit(attempt: AssessmentAttempt, user: User) -> None:
    """Only the candidate who owns the attempt may submit it."""
    if attempt.candidate_id == user.id:
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Access denied: you can submit only your own assessment attempt.",
    )


def authorize_attempt_result(
    attempt: AssessmentAttempt,
    assessment: Assessment,
    user: User,
) -> None:
    """
    Result access: the candidate who owns the attempt, the recruiter who owns
    the assessment, or an admin. No other user may read the result.
    """
    if user.role == UserRole.ADMIN:
        return
    if attempt.candidate_id == user.id:
        return
    if user.role == UserRole.RECRUITER and assessment.created_by_id == user.id:
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Access denied: you are not allowed to view this assessment result.",
    )


# --------------------------------------------------------------------------- #
# Attempt lifecycle                                                            #
# --------------------------------------------------------------------------- #
def start_attempt(
    db: Session,
    assessment: Assessment,
    candidate: User,
) -> AssessmentAttempt:
    """Create (or resume) the candidate's in-progress attempt."""
    if assessment.status != AssessmentStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This assessment is not active.",
        )
    if not assessment.questions:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This assessment has no questions.",
        )

    existing = (
        db.query(AssessmentAttempt)
        .filter(
            AssessmentAttempt.assessment_id == assessment.id,
            AssessmentAttempt.candidate_id == candidate.id,
        )
        .first()
    )
    if existing is not None:
        if existing.status == AttemptStatus.IN_PROGRESS:
            return existing
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You have already submitted this assessment. Only one attempt is allowed.",
        )

    attempt = AssessmentAttempt(
        assessment_id=assessment.id,
        candidate_id=candidate.id,
        status=AttemptStatus.IN_PROGRESS,
    )
    db.add(attempt)
    db.commit()
    db.refresh(attempt)
    return attempt


def build_attempt_start_response(attempt: AssessmentAttempt) -> Dict[str, Any]:
    assessment = attempt.assessment
    return {
        "attempt_id": attempt.id,
        "assessment_id": assessment.id,
        "title": assessment.title,
        "duration_minutes": assessment.duration_minutes,
        "status": attempt.status,
        "started_at": attempt.started_at,
        "questions": [
            serialize_question_public(question)
            for question in assessment.questions
        ],
        "instructions": (
            "Answer all questions and submit once. Coding submissions are stored "
            "and evaluated only when a secure sandbox is configured; they are never "
            "executed inside the API process."
        ),
    }


def _answer_rows(
    attempt: AssessmentAttempt,
    question: AssessmentQuestion,
    *,
    selected_option: Optional[str],
    answer_text: Optional[str],
    is_correct: Optional[bool],
    points_awarded: float,
    evaluation_details: Dict[str, Any],
) -> AssessmentAnswer:
    return AssessmentAnswer(
        attempt_id=attempt.id,
        question_id=question.id,
        selected_option=selected_option,
        answer_text=answer_text,
        is_correct=is_correct,
        points_awarded=points_awarded,
        evaluation_details=evaluation_details,
    )


def _upsert_answer(
    db: Session,
    attempt: AssessmentAttempt,
    question: AssessmentQuestion,
    *,
    selected_option: Optional[str],
    answer_text: Optional[str],
    is_correct: Optional[bool],
    points_awarded: float,
    evaluation_details: Dict[str, Any],
) -> AssessmentAnswer:
    existing = (
        db.query(AssessmentAnswer)
        .filter(
            AssessmentAnswer.attempt_id == attempt.id,
            AssessmentAnswer.question_id == question.id,
        )
        .first()
    )
    if existing is None:
        existing = _answer_rows(
            attempt,
            question,
            selected_option=selected_option,
            answer_text=answer_text,
            is_correct=is_correct,
            points_awarded=points_awarded,
            evaluation_details=evaluation_details,
        )
        db.add(existing)
    else:
        existing.selected_option = selected_option
        existing.answer_text = answer_text
        existing.is_correct = is_correct
        existing.points_awarded = points_awarded
        existing.evaluation_details = evaluation_details
    return existing


def _validate_submission(
    assessment: Assessment,
    answers: Sequence[Any],
) -> Dict[int, Any]:
    question_map = {question.id: question for question in assessment.questions}
    if not question_map:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This assessment has no questions.",
        )

    submitted: Dict[int, Any] = {}
    for answer in answers:
        question_id = int(answer.question_id)
        if question_id not in question_map:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Question {question_id} does not belong to this assessment.",
            )
        if question_id in submitted:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Duplicate answer for question {question_id}.",
            )

        question = question_map[question_id]
        if question.question_type == QuestionType.MCQ:
            if answer.selected_option is not None:
                valid_keys = {
                    str(option.get("key", "")).upper()
                    for option in (question.options or [])
                    if isinstance(option, dict)
                }
                if str(answer.selected_option).upper() not in valid_keys:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=(
                            f"Invalid option {answer.selected_option!r} for question "
                            f"{question_id}."
                        ),
                    )
        else:
            if answer.selected_option is not None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Question {question_id} is a coding question; submit answer_text.",
                )
            if answer.answer_text is not None and len(answer.answer_text) > 100_000:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Code answer for question {question_id} is too long.",
                )

        submitted[question_id] = answer
    return submitted


def submit_attempt(
    db: Session,
    attempt: AssessmentAttempt,
    answers: Sequence[Any],
    *,
    sandbox: Optional[CodingSandbox] = None,
) -> AssessmentAttempt:
    """
    Validate, store and deterministically evaluate all submitted answers.

    MCQ answers are always evaluated. Coding answers are evaluated only through
    the secure sandbox. If the sandbox is unavailable, coding questions are
    excluded from the score denominator and reported as not evaluated.
    """
    if attempt.status != AttemptStatus.IN_PROGRESS:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This attempt has already been submitted.",
        )

    assessment = attempt.assessment
    submitted = _validate_submission(assessment, answers)
    sandbox = sandbox or CodingSandbox()

    questions = sorted(assessment.questions, key=lambda q: (q.order_index, q.id))
    answer_results: List[Dict[str, Any]] = []
    limitations: List[str] = []

    earned_points = 0.0
    evaluated_points = 0.0
    mcq_earned = 0.0
    mcq_total = 0.0
    coding_earned = 0.0
    coding_total = 0.0
    coding_evaluated_points = 0.0
    coding_evaluated = False
    sandbox_available = True

    for question in questions:
        submitted_answer = submitted.get(question.id)
        selected_option = (
            submitted_answer.selected_option if submitted_answer is not None else None
        )
        answer_text = (
            submitted_answer.answer_text if submitted_answer is not None else None
        )

        if question.question_type == QuestionType.MCQ:
            mcq_total += question.points
            evaluated_points += question.points
            selected = str(selected_option).strip().upper() if selected_option else None
            correct = selected is not None and selected == question.correct_answer
            points_awarded = question.points if correct else 0.0
            if correct:
                mcq_earned += points_awarded
            earned_points += points_awarded
            evaluation_status = (
                "unanswered" if selected is None else ("correct" if correct else "incorrect")
            )
            details = {
                "status": evaluation_status,
                "correct_answer": question.correct_answer,
                "selected_option": selected,
            }
            _upsert_answer(
                db,
                attempt,
                question,
                selected_option=selected,
                answer_text=None,
                is_correct=correct if selected is not None else False,
                points_awarded=points_awarded,
                evaluation_details=details,
            )
            answer_results.append(
                {
                    "question_id": question.id,
                    "question_type": question.question_type.value,
                    "selected_option": selected,
                    "is_correct": correct if selected is not None else False,
                    "points_awarded": round(points_awarded, 2),
                    "max_points": question.points,
                    "evaluation_status": evaluation_status,
                    "details": details,
                }
            )
            continue

        # Coding question
        coding_total += question.points
        if not answer_text or not answer_text.strip():
            evaluated_points += question.points
            coding_evaluated_points += question.points
            coding_evaluated = True
            details = {"status": "unanswered"}
            _upsert_answer(
                db,
                attempt,
                question,
                selected_option=None,
                answer_text=answer_text,
                is_correct=False,
                points_awarded=0.0,
                evaluation_details=details,
            )
            answer_results.append(
                {
                    "question_id": question.id,
                    "question_type": question.question_type.value,
                    "selected_option": None,
                    "is_correct": False,
                    "points_awarded": 0.0,
                    "max_points": question.points,
                    "evaluation_status": "unanswered",
                    "details": details,
                }
            )
            continue

        result: SandboxResult = sandbox.evaluate(
            code=answer_text,
            test_cases=question.test_cases or [],
            function_name=question.function_name or "",
            time_limit_ms=question.time_limit_ms,
            memory_limit_mb=question.memory_limit_mb,
        )

        if result.status == "sandbox_unavailable":
            sandbox_available = False
            limitations.append(
                f"Question {question.id}: {result.message or 'Sandbox unavailable.'}"
            )
            details = result.to_dict()
            _upsert_answer(
                db,
                attempt,
                question,
                selected_option=None,
                answer_text=answer_text,
                is_correct=None,
                points_awarded=0.0,
                evaluation_details=details,
            )
            answer_results.append(
                {
                    "question_id": question.id,
                    "question_type": question.question_type.value,
                    "selected_option": None,
                    "is_correct": None,
                    "points_awarded": 0.0,
                    "max_points": question.points,
                    "evaluation_status": "not_evaluated",
                    "details": details,
                }
            )
            continue

        coding_evaluated = True
        coding_evaluated_points += question.points
        evaluated_points += question.points
        ratio = (
            result.passed_tests / result.total_tests
            if result.total_tests > 0
            else 0.0
        )
        points_awarded = round(question.points * ratio, 2)
        coding_earned += points_awarded
        earned_points += points_awarded
        is_correct = result.status == "passed"
        details = result.to_dict()
        _upsert_answer(
            db,
            attempt,
            question,
            selected_option=None,
            answer_text=answer_text,
            is_correct=is_correct,
            points_awarded=points_awarded,
            evaluation_details=details,
        )
        answer_results.append(
            {
                "question_id": question.id,
                "question_type": question.question_type.value,
                "selected_option": None,
                "is_correct": is_correct,
                "points_awarded": points_awarded,
                "max_points": question.points,
                "evaluation_status": result.status,
                "details": details,
            }
        )

    if not sandbox_available:
        limitations.append(
            "Coding submissions were stored but not executed because no secure "
            "sandbox is configured. Coding questions are excluded from the score "
            "denominator; they are not treated as incorrect answers."
        )

    score = round(earned_points / evaluated_points * 100, 2) if evaluated_points > 0 else None
    mcq_score = round(mcq_earned / mcq_total * 100, 2) if mcq_total > 0 else None
    coding_score = (
        round(coding_earned / coding_evaluated_points * 100, 2)
        if coding_evaluated and coding_evaluated_points > 0 and sandbox_available
        else None
    )
    all_points = round(mcq_total + coding_total, 2)
    evaluation_complete = sandbox_available

    attempt.status = (
        AttemptStatus.EVALUATED if evaluation_complete else AttemptStatus.PARTIALLY_EVALUATED
    )
    attempt.score = score
    attempt.mcq_score = mcq_score
    attempt.coding_score = coding_score
    attempt.earned_points = round(earned_points, 2)
    attempt.total_points = all_points
    attempt.submitted_at = _now()
    attempt.evaluated_at = _now()
    attempt.result_details = {
        "score": score,
        "mcq_score": mcq_score,
        "coding_score": coding_score,
        "earned_points": round(earned_points, 2),
        "total_points": all_points,
        "evaluated_points": round(evaluated_points, 2),
        "evaluation_complete": evaluation_complete,
        "sandbox_available": sandbox_available,
        "score_formula": "score = earned_points / evaluated_points * 100",
        "answers": answer_results,
        "limitations": limitations,
    }

    db.commit()
    db.refresh(attempt)
    return attempt


def _sanitize_answer_result(answer: Dict[str, Any]) -> Dict[str, Any]:
    """
    Remove grading secrets from a candidate-facing answer result.

    MCQ correct answers and hidden coding test details (actual/expected values,
    captured stdout/stderr) must not leak to candidates.
    """
    sanitized = dict(answer)
    details = dict(sanitized.get("details") or {})
    if sanitized.get("question_type") == QuestionType.MCQ.value:
        details.pop("correct_answer", None)
    else:
        # Hidden tests and raw harness output (including any exception repr
        # that could echo hidden inputs) must not reach candidates.
        for key in ("details", "stdout", "stderr", "message"):
            details.pop(key, None)
    sanitized["details"] = details
    return sanitized


def build_attempt_result_response(
    attempt: AssessmentAttempt,
    *,
    include_private_details: bool = False,
) -> Dict[str, Any]:
    details = attempt.result_details or {}
    answers = details.get("answers", [])
    if not include_private_details:
        answers = [_sanitize_answer_result(answer) for answer in answers]
    return {
        "attempt_id": attempt.id,
        "assessment_id": attempt.assessment_id,
        "candidate_id": attempt.candidate_id,
        "status": attempt.status,
        "score": attempt.score,
        "mcq_score": attempt.mcq_score,
        "coding_score": attempt.coding_score,
        "earned_points": attempt.earned_points,
        "total_points": attempt.total_points,
        "evaluated_points": details.get("evaluated_points"),
        "evaluation_complete": bool(details.get("evaluation_complete", False)),
        "sandbox_available": bool(details.get("sandbox_available", False)),
        "submitted_at": attempt.submitted_at,
        "evaluated_at": attempt.evaluated_at,
        "answers": answers,
        "limitations": details.get("limitations", []),
    }


def build_attempt_summary(attempt: AssessmentAttempt) -> Dict[str, Any]:
    candidate = attempt.candidate
    return {
        "attempt_id": attempt.id,
        "candidate_id": attempt.candidate_id,
        "candidate_name": getattr(candidate, "full_name", None),
        "candidate_email": getattr(candidate, "email", None),
        "status": attempt.status,
        "score": attempt.score,
        "started_at": attempt.started_at,
        "submitted_at": attempt.submitted_at,
        "evaluated_at": attempt.evaluated_at,
    }
