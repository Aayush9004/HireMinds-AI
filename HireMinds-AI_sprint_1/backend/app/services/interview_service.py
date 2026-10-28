"""
Phase 9: AI Mock Interview service.

Responsibilities
----------------
* Generates open-ended, realistic technical interview questions grounded in job
  requirements and candidate profile.
* Manages sequential, one-at-a-time question delivery.
* Generates contextual follow-up questions when answers invite deeper exploration.
* Evaluates answers using a predefined 4-dimension rubric (Technical Correctness,
  Relevance, Clarity, Reasoning) scaled to 0-100.
* Generates session-level feedback (strengths, weaknesses, suggestions, recommended topics).
* Ensures zero interaction with ATS scoring or match results.
* Handles LLM errors, timeouts, rate limits, and fallback deterministic summaries.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.interview import (
    InterviewAnswer,
    InterviewEvaluation,
    InterviewQuestion,
    InterviewSession,
    InterviewStatus,
)
from app.models.job import Job
from app.models.resume import Resume
from app.models.user import User, UserRole
from app.schemas.interview import InterviewStartRequest
from app.services.llm_client import (
    BaseLLMClient,
    LLMAPIError,
    LLMConfigurationError,
    LLMError,
    LLMResponseError,
    LLMTimeoutError,
    get_llm_client,
)

logger = logging.getLogger(__name__)

DISCLAIMER_TEXT = (
    "This AI-generated evaluation is provided for interview practice and preparation guidance only. "
    "It is not an objective hiring decision, does not guarantee or predict actual employment outcomes, "
    "and must be reviewed alongside comprehensive human evaluation."
)

_ALLOWED_DIFFICULTIES = {"easy", "medium", "hard"}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _as_text(val: Any) -> str:
    if val is None:
        return ""
    return str(val).strip()


def _clamp_score(val: Any, min_val: float = 1.0, max_val: float = 5.0, default: float = 3.0) -> float:
    try:
        num = float(val)
        return round(max(min_val, min(max_val, num)), 2)
    except (TypeError, ValueError):
        return default


def _candidate_skills(resume: Optional[Resume]) -> List[str]:
    if resume is None:
        return []
    skills = list(getattr(resume, "extracted_skills", None) or [])
    if getattr(resume, "is_reviewed_by_candidate", False):
        corrected = getattr(resume, "candidate_corrected_data", None) or {}
        if isinstance(corrected, dict) and corrected.get("skills"):
            skills = list(corrected["skills"])
    return [str(s).strip() for s in skills if str(s).strip()]


def _job_skills(job: Job) -> List[str]:
    req = list(getattr(job, "required_skills", None) or [])
    pref = list(getattr(job, "preferred_skills", None) or [])
    all_skills = [str(s).strip() for s in (req + pref) if str(s).strip()]
    return list(dict.fromkeys(all_skills))


# --------------------------------------------------------------------------- #
# Question Generation Prompts & Helpers                                        #
# --------------------------------------------------------------------------- #

def generate_initial_question(
    job: Job,
    candidate_skills: List[str],
    difficulty: str,
    focus_areas: List[str],
    llm_client: BaseLLMClient,
) -> Dict[str, Any]:
    """Call LLM to generate the first technical question for the interview."""
    req_skills = ", ".join(job.required_skills or []) or "General Software Engineering"
    cand_skills_str = ", ".join(candidate_skills) or "Not specified"
    focus_str = ", ".join(focus_areas) or "Core Technical Skills"

    prompt = f"""You are an expert technical interviewer conducting a structured technical interview.
Generate the FIRST interview question for the following role:

Position: {job.title}
Job Description: {job.description or 'N/A'}
Required Technical Skills: {req_skills}
Candidate's Known Skills: {cand_skills_str}
Focus Areas: {focus_str}
Requested Difficulty: {difficulty}

Instructions:
1. Ask an open-ended, realistic, technical interview question relevant to this role.
2. The question should assess technical competence, problem-solving, architectural design, or core conceptual depth.
3. Keep the prompt professional, direct, and concise (1-3 sentences).
4. Do NOT output markdown formatting outside the JSON. Return strictly a JSON object.

JSON Schema:
{{
  "prompt": "Question text to ask candidate",
  "skill_tag": "Primary skill or concept tested (e.g. Python, SQL, Distributed Systems)",
  "difficulty": "easy|medium|hard",
  "rationale": "Brief note on why this question is relevant to the job"
}}
"""
    raw = llm_client.generate_json(prompt)
    if not isinstance(raw, dict):
        raise LLMResponseError("LLM response for initial question is not a JSON object.")

    q_prompt = _as_text(raw.get("prompt"))
    if len(q_prompt) < 10:
        raise LLMResponseError("LLM returned an empty or invalid question prompt.")

    skill_tag = _as_text(raw.get("skill_tag")) or (job.required_skills[0] if job.required_skills else "General")
    diff = _as_text(raw.get("difficulty")).lower()
    if diff not in _ALLOWED_DIFFICULTIES:
        diff = difficulty if difficulty in _ALLOWED_DIFFICULTIES else "medium"
    rationale = _as_text(raw.get("rationale")) or "Evaluates core role requirements."

    return {
        "prompt": q_prompt,
        "skill_tag": skill_tag[:120],
        "difficulty": diff,
        "rationale": rationale,
    }


def evaluate_answer_with_rubric(
    question: InterviewQuestion,
    answer_text: str,
    job: Job,
    llm_client: BaseLLMClient,
) -> Dict[str, Any]:
    """
    Evaluate a candidate's answer using the predefined 4-dimension rubric (1.0 to 5.0):
    - Technical Correctness
    - Relevance
    - Clarity
    - Reasoning
    """
    prompt = f"""You are an expert technical interviewer evaluating a candidate's response to an interview question.

Role: {job.title}
Question Asked: {question.prompt}
Topic / Skill Tag: {question.skill_tag or 'Technical'}
Difficulty: {question.difficulty}

Candidate's Answer:
\"\"\"{answer_text}\"\"\"

Evaluate the answer strictly using this 4-dimension rubric on a 1.0 to 5.0 scale (decimal increments allowed):
1. technical_correctness (1.0 - 5.0): Accuracy of facts, concepts, algorithms, frameworks, and syntax.
   - 1.0: Factually incorrect or major misunderstandings
   - 3.0: Partially correct, minor gaps
   - 5.0: Thoroughly accurate, demonstrates deep expertise
2. relevance (1.0 - 5.0): How directly and completely the candidate addressed what was asked.
   - 1.0: Off-topic or ignores the question
   - 3.0: Addresses main point but misses key aspects
   - 5.0: Directly and fully addresses all facets of the prompt
3. clarity (1.0 - 5.0): Structure, conciseness, coherence, and professional communication.
   - 1.0: Disorganized, rambling, or confusing
   - 3.0: Understandable but lacks structure
   - 5.0: Exceptionally well-structured, precise, and articulate
4. reasoning (1.0 - 5.0): Justification of decisions, edge cases considered, trade-off analysis, and problem-solving depth.
   - 1.0: No justification or shallow regurgitation
   - 3.0: Basic reasoning without exploring trade-offs
   - 5.0: Thoughtful architectural trade-offs, edge cases, and rationale

Provide specific, constructive feedback (2-4 sentences) explaining what was done well and what was missing or could be improved.
Return strictly a JSON object:
{{
  "technical_correctness": 4.0,
  "relevance": 4.5,
  "clarity": 4.0,
  "reasoning": 3.5,
  "feedback": "Constructive feedback text...",
  "strengths": ["Strong point 1"],
  "improvements": ["Area for improvement 1"]
}}
"""
    raw = llm_client.generate_json(prompt)
    if not isinstance(raw, dict):
        raise LLMResponseError("LLM response for answer evaluation is not a JSON object.")

    tech = _clamp_score(raw.get("technical_correctness"))
    rel = _clamp_score(raw.get("relevance"))
    clar = _clamp_score(raw.get("clarity"))
    reas = _clamp_score(raw.get("reasoning"))

    # Overall score 0-100 derived from the 4 rubric dimensions
    overall = round(((tech + rel + clar + reas) / 20.0) * 100.0, 2)

    feedback = _as_text(raw.get("feedback"))
    if not feedback:
        feedback = f"Answer evaluated with technical correctness {tech}/5 and relevance {rel}/5."

    details = {
        "strengths": raw.get("strengths") if isinstance(raw.get("strengths"), list) else [],
        "improvements": raw.get("improvements") if isinstance(raw.get("improvements"), list) else [],
    }

    return {
        "technical_correctness": tech,
        "relevance": rel,
        "clarity": clar,
        "reasoning": reas,
        "overall_score": overall,
        "feedback": feedback,
        "evaluation_details": details,
    }


def generate_next_or_follow_up_question(
    session: InterviewSession,
    previous_question: InterviewQuestion,
    previous_answer_text: str,
    can_follow_up: bool,
    llm_client: BaseLLMClient,
) -> Dict[str, Any]:
    """
    Generate the next question. If can_follow_up is True and the candidate's answer
    invites further technical inquiry or clarification, generate a contextual follow-up.
    Otherwise, move to a new topic from the job requirements.
    """
    job = session.job
    all_job_skills = _job_skills(job)
    covered_skills = [q.skill_tag for q in session.questions if q.skill_tag]

    prompt = f"""You are an expert technical interviewer in an ongoing technical interview.

Job Title: {job.title}
Job Description: {job.description or 'N/A'}
Required Skills: {', '.join(all_job_skills) or 'Technical skills'}
Already Covered Skills/Topics: {', '.join(covered_skills) or 'None'}

Most Recent Question Asked:
\"{previous_question.prompt}\" (Skill: {previous_question.skill_tag})

Candidate's Answer:
\"{previous_answer_text}\"

Can follow up on this answer: {'YES' if can_follow_up else 'NO (Max follow-ups reached, must switch topic)'}

Instructions:
1. If 'Can follow up' is YES and the candidate's answer mentions a specific architecture, trade-off, tool, or edge case worth probing deeper (or had a misconception to clarify), generate a contextual FOLLOW-UP question (set "is_follow_up": true).
2. Otherwise (or if 'Can follow up' is NO), generate a NEW question covering a different required skill or domain for this job that has NOT been thoroughly tested yet (set "is_follow_up": false).
3. The question must be open-ended, realistic, and professional (1-3 sentences).
4. Return strictly a JSON object:
{{
  "is_follow_up": true,
  "prompt": "Question text...",
  "skill_tag": "Skill or topic tested",
  "difficulty": "easy|medium|hard",
  "rationale": "Why this question was chosen"
}}
"""
    raw = llm_client.generate_json(prompt)
    if not isinstance(raw, dict):
        raise LLMResponseError("LLM response for next question is not a JSON object.")

    is_follow_up = bool(raw.get("is_follow_up")) and can_follow_up
    q_prompt = _as_text(raw.get("prompt"))
    if len(q_prompt) < 10:
        raise LLMResponseError("LLM returned an invalid next question prompt.")

    skill_tag = _as_text(raw.get("skill_tag")) or previous_question.skill_tag or "General"
    diff = _as_text(raw.get("difficulty")).lower()
    if diff not in _ALLOWED_DIFFICULTIES:
        diff = session.difficulty if session.difficulty in _ALLOWED_DIFFICULTIES else "medium"
    rationale = _as_text(raw.get("rationale")) or ("Follow-up question" if is_follow_up else "Next skill assessment")

    return {
        "is_follow_up": is_follow_up,
        "prompt": q_prompt,
        "skill_tag": skill_tag[:120],
        "difficulty": diff,
        "rationale": rationale,
    }


def generate_session_qualitative_feedback(
    session: InterviewSession,
    answers: List[InterviewAnswer],
    llm_client: BaseLLMClient,
) -> Dict[str, Any]:
    """Generate overall summary, strengths, weaknesses, and recommended topics."""
    job = session.job
    qa_pairs = []
    for a in answers:
        q = a.question
        qa_pairs.append(
            f"Q: {q.prompt} [{q.skill_tag}]\n"
            f"A: {a.answer_text[:300]}...\n"
            f"Scores: Correctness={a.technical_correctness}/5, Relevance={a.relevance}/5, "
            f"Clarity={a.clarity}/5, Reasoning={a.reasoning}/5\n"
            f"Feedback: {a.feedback}\n"
        )
    qa_summary = "\n".join(qa_pairs)

    prompt = f"""You are a senior hiring manager compiling the post-interview evaluation report for a candidate.

Role: {job.title}
Job Description: {job.description or 'N/A'}

Interview Transcript and Question-by-Question Evaluations:
{qa_summary}

Instructions:
Synthesize the candidate's overall performance into a constructive, objective evaluation report:
1. overall_summary: A comprehensive paragraph (3-5 sentences) summarizing their performance, depth of knowledge, and communication style.
2. strengths: A list of 2 to 5 specific technical or problem-solving strengths evidenced in their answers.
3. weaknesses: A list of 2 to 5 specific gaps, misconceptions, or areas needing improvement.
4. improvement_suggestions: A list of 2 to 5 actionable suggestions for interview preparation.
5. recommended_topics: A list of 2 to 5 specific technical subjects, architectures, or tools the candidate should study.

Return strictly a JSON object:
{{
  "overall_summary": "Summary paragraph...",
  "strengths": ["Strength 1", "Strength 2"],
  "weaknesses": ["Weakness 1", "Weakness 2"],
  "improvement_suggestions": ["Suggestion 1", "Suggestion 2"],
  "recommended_topics": ["Topic 1", "Topic 2"]
}}
"""
    raw = llm_client.generate_json(prompt)
    if not isinstance(raw, dict):
        raise LLMResponseError("LLM response for qualitative feedback is not a JSON object.")

    summary = _as_text(raw.get("overall_summary"))
    if not summary:
        raise LLMResponseError("LLM returned empty overall summary.")

    strengths = [_as_text(s) for s in raw.get("strengths", []) if _as_text(s)]
    weaknesses = [_as_text(w) for w in raw.get("weaknesses", []) if _as_text(w)]
    suggestions = [_as_text(i) for i in raw.get("improvement_suggestions", []) if _as_text(i)]
    topics = [_as_text(t) for t in raw.get("recommended_topics", []) if _as_text(t)]

    return {
        "overall_summary": summary,
        "strengths": strengths or ["Clear communication on core concepts"],
        "weaknesses": weaknesses or ["Could provide deeper trade-off analysis"],
        "improvement_suggestions": suggestions or ["Practice end-to-end system design scenarios"],
        "recommended_topics": topics or [job.required_skills[0] if job.required_skills else "System Design"],
    }


def _deterministic_fallback_feedback(
    job: Job,
    answers: List[InterviewAnswer],
) -> Dict[str, Any]:
    """Fallback when LLM is unavailable to complete session feedback without failing."""
    skills = _job_skills(job)
    return {
        "overall_summary": (
            f"Candidate completed the mock interview for {job.title} across {len(answers)} questions. "
            "Evaluations reflect structured rubric ratings on technical correctness, relevance, clarity, and reasoning."
        ),
        "strengths": [
            "Demonstrated relevant technical context for the position",
            "Followed question prompts with coherent explanations",
        ],
        "weaknesses": [
            "Certain architectural and trade-off considerations could be expanded with more depth",
        ],
        "improvement_suggestions": [
            "Review edge cases and performance trade-offs for core interview topics",
            "Structure answers with the STAR or problem-solution-impact method",
        ],
        "recommended_topics": skills[:4] if skills else ["System Architecture", "Data Structures"],
    }


# --------------------------------------------------------------------------- #
# Core Service Functions                                                       #
# --------------------------------------------------------------------------- #

def get_current_unanswered_question(session: InterviewSession) -> Optional[InterviewQuestion]:
    """Return the current active question that has not been answered yet, or None."""
    for question in sorted(session.questions, key=lambda q: q.order_index):
        if question.answer is None:
            return question
    return None


def start_or_resume_interview_session(
    db: Session,
    candidate: User,
    request: InterviewStartRequest,
    llm_client: Optional[BaseLLMClient] = None,
) -> Tuple[InterviewSession, Optional[InterviewQuestion], bool]:
    """
    Start a new mock interview session or resume an active one.

    Returns:
        (session, current_question, is_resumed)
    """
    # 1. Check for active in-progress session for this candidate and job
    existing_session = (
        db.query(InterviewSession)
        .filter(
            InterviewSession.candidate_id == candidate.id,
            InterviewSession.job_id == request.job_id,
            InterviewSession.status == InterviewStatus.IN_PROGRESS,
        )
        .first()
    )

    if existing_session is not None:
        current_q = get_current_unanswered_question(existing_session)
        # If all existing questions are answered, check if session target reached
        if current_q is None and len(existing_session.answers) >= existing_session.target_question_count:
            finalize_interview_session(db, existing_session, llm_client)
            return existing_session, None, True
        return existing_session, current_q, True

    # 2. Validate Job exists
    job = db.query(Job).filter(Job.id == request.job_id).first()
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found.",
        )

    # 3. Validate optional Resume belongs to candidate
    candidate_skills: List[str] = []
    resume = None
    if request.resume_id:
        resume = db.query(Resume).filter(Resume.id == request.resume_id).first()
        if resume is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Resume not found.",
            )
        if resume.user_id != candidate.id and candidate.role != UserRole.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You cannot use a resume that does not belong to you.",
            )
        candidate_skills = _candidate_skills(resume)

    client = llm_client or get_llm_client()
    diff = request.difficulty or "mixed"
    focus = request.focus_areas or []

    # 4. Generate first question via LLM
    q_data = generate_initial_question(
        job=job,
        candidate_skills=candidate_skills,
        difficulty=diff,
        focus_areas=focus,
        llm_client=client,
    )

    title = request.title or f"{job.title} Mock Interview"

    session = InterviewSession(
        job_id=job.id,
        candidate_id=candidate.id,
        resume_id=resume.id if resume else None,
        status=InterviewStatus.IN_PROGRESS,
        title=title,
        description=f"AI mock interview session for {job.title} at {getattr(job, 'company_name', 'Company')}.",
        difficulty=diff,
        focus_areas=focus,
        target_question_count=request.target_question_count,
        max_follow_ups=request.max_follow_ups,
        generation_model=getattr(client, "model", "gemini"),
        generation_prompt_version=settings.INTERVIEW_PROMPT_VERSION,
        started_at=_now(),
    )
    db.add(session)
    db.flush()

    first_question = InterviewQuestion(
        session_id=session.id,
        order_index=1,
        is_follow_up=False,
        prompt=q_data["prompt"],
        skill_tag=q_data["skill_tag"],
        difficulty=q_data["difficulty"],
        rationale=q_data["rationale"],
    )
    db.add(first_question)
    db.commit()
    db.refresh(session)
    db.refresh(first_question)

    return session, first_question, False


def submit_interview_answer(
    db: Session,
    session: InterviewSession,
    question: InterviewQuestion,
    answer_text: str,
    candidate: User,
    llm_client: Optional[BaseLLMClient] = None,
) -> Dict[str, Any]:
    """
    Candidate submits an answer to the current question:
    1. Evaluates answer with predefined 4-dimension rubric.
    2. Stores answer and derived 0-100 score.
    3. If question target reached, completes session & generates evaluation.
    4. Otherwise, generates next question (follow-up or new topic).
    """
    if session.candidate_id != candidate.id and candidate.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only submit answers to your own interview sessions.",
        )

    if session.status != InterviewStatus.IN_PROGRESS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Interview session is already completed.",
        )

    if question.session_id != session.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Question does not belong to this interview session.",
        )

    if question.answer is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This question has already been answered.",
        )

    client = llm_client or get_llm_client()
    job = session.job

    # 1. Evaluate answer using rubric
    eval_result = evaluate_answer_with_rubric(
        question=question,
        answer_text=answer_text,
        job=job,
        llm_client=client,
    )

    answer = InterviewAnswer(
        session_id=session.id,
        question_id=question.id,
        answer_text=answer_text,
        technical_correctness=eval_result["technical_correctness"],
        relevance=eval_result["relevance"],
        clarity=eval_result["clarity"],
        reasoning=eval_result["reasoning"],
        overall_score=eval_result["overall_score"],
        feedback=eval_result["feedback"],
        evaluation_details=eval_result["evaluation_details"],
        evaluated_at=_now(),
    )
    db.add(answer)
    db.flush()

    total_answered = len(session.answers)
    is_completed = False
    has_next_question = False
    next_question: Optional[InterviewQuestion] = None

    # 2. Check if target questions completed or max total questions reached
    if (
        total_answered >= session.target_question_count
        or len(session.questions) >= settings.INTERVIEW_MAX_TOTAL_QUESTIONS
    ):
        finalize_interview_session(db, session, client)
        is_completed = True
        message = "Interview completed! Your session evaluation has been generated."
    else:
        # 3. Determine if next question is a follow-up or new topic
        follow_ups_so_far = sum(1 for q in session.questions if q.is_follow_up)
        can_follow_up = follow_ups_so_far < session.max_follow_ups

        next_q_data = generate_next_or_follow_up_question(
            session=session,
            previous_question=question,
            previous_answer_text=answer_text,
            can_follow_up=can_follow_up,
            llm_client=client,
        )

        next_question = InterviewQuestion(
            session_id=session.id,
            order_index=len(session.questions) + 1,
            is_follow_up=next_q_data["is_follow_up"],
            parent_question_id=question.id if next_q_data["is_follow_up"] else None,
            prompt=next_q_data["prompt"],
            skill_tag=next_q_data["skill_tag"],
            difficulty=next_q_data["difficulty"],
            rationale=next_q_data["rationale"],
        )
        db.add(next_question)
        has_next_question = True
        message = "Answer recorded and evaluated. Next question ready."

    db.commit()
    db.refresh(answer)
    if next_question is not None:
        db.refresh(next_question)
    db.refresh(session)

    return {
        "answer": answer,
        "session_status": session.status,
        "has_next_question": has_next_question,
        "next_question": next_question,
        "is_completed": is_completed,
        "message": message,
    }


def finalize_interview_session(
    db: Session,
    session: InterviewSession,
    llm_client: Optional[BaseLLMClient] = None,
) -> InterviewEvaluation:
    """
    Finalize an interview session:
    - Computes deterministic rubric averages across all submitted answers.
    - Generates qualitative session summary, strengths, weaknesses, and study topics.
    - Marks session as COMPLETED.
    """
    if session.evaluation is not None:
        return session.evaluation

    answers = list(session.answers)
    if not answers:
        avg_score = 0.0
        avg_tech = 1.0
        avg_rel = 1.0
        avg_clar = 1.0
        avg_reas = 1.0
    else:
        n = len(answers)
        avg_score = round(sum(a.overall_score for a in answers) / n, 2)
        avg_tech = round(sum(a.technical_correctness for a in answers) / n, 2)
        avg_rel = round(sum(a.relevance for a in answers) / n, 2)
        avg_clar = round(sum(a.clarity for a in answers) / n, 2)
        avg_reas = round(sum(a.reasoning for a in answers) / n, 2)

    client = llm_client or get_llm_client()
    gen_status = "llm"
    gen_model = getattr(client, "model", "gemini")

    try:
        feedback_data = generate_session_qualitative_feedback(
            session=session,
            answers=answers,
            llm_client=client,
        )
    except Exception as exc:
        logger.warning(
            "LLM feedback generation failed; using deterministic fallback feedback: %s",
            exc,
        )
        feedback_data = _deterministic_fallback_feedback(session.job, answers)
        gen_status = "fallback"

    session.status = InterviewStatus.COMPLETED
    session.completed_at = _now()

    evaluation = InterviewEvaluation(
        session_id=session.id,
        overall_score=avg_score,
        technical_correctness=avg_tech,
        relevance=avg_rel,
        clarity=avg_clar,
        reasoning=avg_reas,
        overall_summary=feedback_data["overall_summary"],
        strengths=feedback_data["strengths"],
        weaknesses=feedback_data["weaknesses"],
        improvement_suggestions=feedback_data["improvement_suggestions"],
        recommended_topics=feedback_data["recommended_topics"],
        disclaimer=DISCLAIMER_TEXT,
        rubric_version=settings.INTERVIEW_RUBRIC_VERSION,
        generation_model=gen_model,
        generation_status=gen_status,
        created_at=_now(),
    )
    db.add(evaluation)
    db.commit()
    db.refresh(evaluation)
    db.refresh(session)

    return evaluation
