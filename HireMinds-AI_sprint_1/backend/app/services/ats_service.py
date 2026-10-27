"""
Explainable ATS scoring service (Phase 7).

Formula
-------
    ATS = w_skill * K + w_experience * E + w_education * D
          + w_projects * P + w_semantic * M

Every component is normalised to 0-100. The default weights are:

    K (skills)      40%
    E (experience)  25%
    D (education)   15%
    P (projects)    10%
    M (semantic)    10%

Important design rules
----------------------
1. Weights come from application settings and are snapshotted with every score.
2. Missing information is represented as ``None`` + ``insufficient_data`` and is
   excluded from the weighted sum. Remaining weights are renormalised. Missing
   information is NEVER silently converted into a zero score.
3. Automatically extracted resume data is marked as unverified until the
   candidate reviews it. Unverified data lowers confidence but is not treated
   as false.
4. Every component carries a rationale, evidence, missing-information notes and
   a data-quality label so the score can be explained.
5. Scores are decision-support only. No candidate is rejected automatically and
   no protected/sensitive personal characteristics are explicit scoring inputs.

The weights are initial assumptions, not scientifically validated hiring
criteria. See ``LIMITATIONS`` below.
"""
from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from app.core.config import settings
from app.models.job import Job
from app.models.match import MatchResult
from app.models.resume import Resume
from app.services.semantic_matcher import compute_semantic_similarity_optional
from app.services.skill_extractor import extract_skills_from_text
from app.services.skill_matcher import compute_skill_match
from app.services.tfidf_matcher import compute_tfidf_similarity

logger = logging.getLogger(__name__)

_UNSET = object()

COMPONENT_LABELS: Dict[str, str] = {
    "skills": "Skill Match",
    "experience": "Experience Relevance",
    "education": "Education Match",
    "projects": "Project Relevance",
    "semantic": "Semantic Similarity",
}

COMPONENT_ORDER = ("skills", "experience", "education", "projects", "semantic")

LIMITATIONS: List[str] = [
    "The initial weights are assumptions chosen for this project, not scientifically validated hiring criteria.",
    "ATS scores are decision-support signals, not hiring decisions. A human must review the evidence and context.",
    "Automatically extracted resume data can contain parsing errors; candidates should review and correct it.",
    "Experience and education extraction rely on heuristics and may miss non-standard formats.",
    "Semantic models can encode societal biases and may be influenced by resume writing style or length.",
    "No protected or sensitive personal characteristics are explicit scoring inputs, but unstructured resume text may contain proxies; human review is required.",
    "When information is missing, the component is excluded and remaining weights are renormalised. This lowers confidence and makes scores less comparable between candidates.",
    "Scores are comparable only within the same job, scoring version and weight configuration.",
]

DISCLAIMER = (
    "ATS scores are explainable decision-support signals, not hiring decisions. "
    "HireMinds AI does not automatically reject candidates based on score. "
    "A human recruiter must review the evidence and consider context. "
    "Protected or sensitive personal characteristics are not used as scoring inputs."
)

MISSING_DATA_POLICY = (
    "If a component cannot be assessed, its score is null and it is excluded from the "
    "weighted sum; the remaining weights are renormalised. Missing information is never "
    "converted into a zero score. This reduces confidence and is reported explicitly."
)

# --------------------------------------------------------------------------- #
# Text sanitisation for fairness                                               #
# --------------------------------------------------------------------------- #
_EMAIL_RE = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")
_PHONE_RE = re.compile(r"(?<!\d)(?:\+\d{1,3}[\s-]?)?(?:\d[\s-]?){9,14}\d(?!\d)")
_URL_RE = re.compile(r"https?://\S+|www\.\S+", re.IGNORECASE)
_PROTECTED_LINE_RE = re.compile(
    r"\b(gender|sex|date of birth|dob|age|marital status|nationality|religion|caste|race|ethnicity)\b",
    re.IGNORECASE,
)


def sanitize_text_for_scoring(text: str) -> str:
    """
    Remove obvious identifiers and explicit protected-characteristic lines from
    text used for similarity scoring. This is a best-effort safeguard, not a
    guarantee: names and implicit proxies can remain in free text.
    """
    if not text:
        return ""
    lines = [line for line in text.splitlines() if not _PROTECTED_LINE_RE.search(line)]
    cleaned = "\n".join(lines)
    cleaned = _EMAIL_RE.sub(" ", cleaned)
    cleaned = _PHONE_RE.sub(" ", cleaned)
    cleaned = _URL_RE.sub(" ", cleaned)
    return cleaned


# --------------------------------------------------------------------------- #
# Component helpers                                                            #
# --------------------------------------------------------------------------- #
def _component_confidence(status: str, data_quality: str) -> str:
    if status in ("insufficient_data", "not_applicable"):
        return "none"
    if status == "partial":
        return "low"
    return "high" if data_quality == "candidate_reviewed" else "medium"


def _make_component(
    key: str,
    weight: float,
    score: Optional[float],
    status: str,
    rationale: str,
    *,
    evidence: Optional[List[Dict[str, Any]]] = None,
    missing: Optional[List[str]] = None,
    details: Optional[Dict[str, Any]] = None,
    data_quality: str = "auto_extracted_unverified",
) -> Dict[str, Any]:
    """Build a normalised component result with all explanation fields."""
    normalised_score = None
    if score is not None:
        normalised_score = round(min(100.0, max(0.0, float(score))), 2)

    return {
        "key": key,
        "label": COMPONENT_LABELS[key],
        "weight": round(float(weight), 4),
        "effective_weight": 0.0,
        "score": normalised_score,
        "weighted_contribution": 0.0,
        "status": status,
        "confidence": _component_confidence(status, data_quality),
        "rationale": rationale,
        "evidence": evidence or [],
        "missing_information": missing or [],
        "data_quality": data_quality,
        "details": details or {},
    }


def _resume_data_quality(resume: Resume) -> str:
    return (
        "candidate_reviewed"
        if getattr(resume, "is_reviewed_by_candidate", False)
        else "auto_extracted_unverified"
    )


def _resume_skills(resume: Resume) -> List[str]:
    skills = list(getattr(resume, "extracted_skills", None) or [])
    if getattr(resume, "is_reviewed_by_candidate", False):
        corrected = getattr(resume, "candidate_corrected_data", None) or {}
        corrected_skills = corrected.get("skills") if isinstance(corrected, dict) else None
        if corrected_skills:
            skills = list(corrected_skills)
    return [s.strip() for s in skills if isinstance(s, str) and s.strip()]


def _job_text(job: Job) -> str:
    parts = [
        getattr(job, "title", "") or "",
        getattr(job, "company_name", "") or "",
        getattr(job, "description", "") or "",
        " ".join(getattr(job, "required_skills", None) or []),
        " ".join(getattr(job, "preferred_skills", None) or []),
        getattr(job, "required_education", "") or "",
        f"{getattr(job, 'min_experience_years', 0) or 0} years experience",
    ]
    return " ".join(str(p) for p in parts if p)


def _split_sentences(text: str) -> List[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n+", text or "") if s.strip()]


def _clamp(value: float) -> float:
    return max(0.0, min(100.0, float(value)))


# --------------------------------------------------------------------------- #
# Component 1: Skills (K)                                                      #
# --------------------------------------------------------------------------- #
def score_skill_component(
    resume: Resume,
    job: Job,
    weight: float,
    data_quality: Optional[str] = None,
) -> Dict[str, Any]:
    """
    K = percentage of required job skills present in the resume skills list.

    Preferred skills are reported as supporting evidence but do not increase K,
    because mixing required and optional skills would make the score harder to
    interpret. If only preferred skills exist, they are used and the component is
    marked ``partial``.
    """
    dq = data_quality or _resume_data_quality(resume)
    skills = _resume_skills(resume)
    required = [s.strip() for s in (getattr(job, "required_skills", None) or []) if isinstance(s, str) and s.strip()]
    preferred = [s.strip() for s in (getattr(job, "preferred_skills", None) or []) if isinstance(s, str) and s.strip()]

    if not required and not preferred:
        return _make_component(
            "skills",
            weight,
            None,
            "not_applicable",
            "The job lists no required or preferred skills, so skill match cannot be assessed.",
            missing=[],
            details={"required_skills": [], "preferred_skills": []},
            data_quality=dq,
        )

    if not skills:
        return _make_component(
            "skills",
            weight,
            None,
            "insufficient_data",
            "No skills were extracted from the resume. Skill match is unknown, not zero.",
            missing=["No skills were extracted from the resume; the candidate may still have relevant skills."],
            details={"required_skills": required, "preferred_skills": preferred},
            data_quality=dq,
        )

    skill_details = compute_skill_match(
        resume_skills=skills,
        required_skills=required,
        preferred_skills=preferred,
        resume_raw_text=sanitize_text_for_scoring(getattr(resume, "raw_text", "") or ""),
    )

    evidence = [
        {"skill": skill, "evidence": sentence}
        for skill, sentence in (skill_details.get("evidence") or {}).items()
    ]

    if required:
        score = skill_details["skill_match_score"] * 100.0
        status = "scored"
        rationale = (
            f"Matched {len(skill_details['matched_required'])} of "
            f"{skill_details['total_required']} required skills "
            f"({score:.0f}%). Preferred skills are listed separately as supporting evidence."
        )
        missing: List[str] = []
    else:
        total_preferred = skill_details.get("total_preferred", 0)
        matched_preferred = len(skill_details.get("matched_preferred") or [])
        score = (matched_preferred / total_preferred * 100.0) if total_preferred else None
        status = "partial"
        rationale = (
            f"No required skills were listed. The score uses {matched_preferred} of "
            f"{total_preferred} preferred skills ({score or 0:.0f}%)."
        )
        missing = []

    details = {
        "required_skills": required,
        "preferred_skills": preferred,
        "matched_required": skill_details.get("matched_required", []),
        "missing_required": skill_details.get("missing_required", []),
        "matched_preferred": skill_details.get("matched_preferred", []),
        "missing_preferred": skill_details.get("missing_preferred", []),
        "total_required": skill_details.get("total_required", 0),
        "total_preferred": skill_details.get("total_preferred", 0),
        "total_resume_skills": skill_details.get("total_resume_skills", len(skills)),
    }

    return _make_component(
        "skills",
        weight,
        score,
        status,
        rationale,
        evidence=evidence,
        missing=missing,
        details=details,
        data_quality=dq,
    )


# --------------------------------------------------------------------------- #
# Component 2: Experience (E)                                                  #
# --------------------------------------------------------------------------- #
def _role_relevance(roles: List[str], job: Job) -> Optional[float]:
    if not roles:
        return None
    role_text = sanitize_text_for_scoring(" ".join(roles))
    return compute_tfidf_similarity(role_text, _job_text(job))


def _experience_evidence(raw_text: str, years: Optional[float], roles: List[str]) -> List[Dict[str, Any]]:
    keywords = ["year", "experience", "intern"] + [r.lower() for r in roles]
    evidence: List[Dict[str, Any]] = []
    seen: set[str] = set()
    for sentence in _split_sentences(sanitize_text_for_scoring(raw_text)):
        lower = sentence.lower()
        if any(keyword in lower for keyword in keywords):
            trimmed = sentence[:300]
            if trimmed not in seen:
                seen.add(trimmed)
                evidence.append({"text": trimmed, "source": "resume_text"})
        if len(evidence) >= 4:
            break
    if years is not None:
        evidence.insert(0, {"text": f"Resume states approximately {years:g} years of experience.", "source": "extracted_experience"})
    return evidence[:5]


def score_experience_component(
    resume: Resume,
    job: Job,
    weight: float,
    data_quality: Optional[str] = None,
) -> Dict[str, Any]:
    """
    E combines the years-of-experience ratio (70% sub-weight) with role-title
    relevance (30% sub-weight). A candidate is not penalised for having more
    experience than required (the ratio is capped at 1.0).

    If the job has no minimum experience requirement, E is ``not_applicable``.
    If the resume does not state years, but role titles exist, E is ``partial``
    and uses role relevance only -- never an assumed zero.
    """
    dq = data_quality or _resume_data_quality(resume)
    exp = getattr(resume, "extracted_experience", None) or {}
    years = exp.get("estimated_years") if isinstance(exp, dict) else None
    roles = [
        str(r).strip()
        for r in (exp.get("identified_roles", []) if isinstance(exp, dict) else [])
        if str(r).strip()
    ]
    required_years = float(getattr(job, "min_experience_years", 0) or 0)

    if required_years <= 0:
        return _make_component(
            "experience",
            weight,
            None,
            "not_applicable",
            "The job specifies no minimum experience requirement, so experience was excluded rather than assumed.",
            missing=[],
            details={"required_years": required_years, "estimated_years": years, "identified_roles": roles},
            data_quality=dq,
        )

    if years is None and not roles:
        return _make_component(
            "experience",
            weight,
            None,
            "insufficient_data",
            "The resume does not state years of experience and no roles were identified. Experience is unknown, not zero.",
            missing=[
                "No years of experience were stated in the resume.",
                "No job titles were identified, so role relevance could not be assessed.",
            ],
            details={"required_years": required_years},
            data_quality=dq,
        )

    role_relevance = _role_relevance(roles, job)
    years_ratio: Optional[float] = None
    missing: List[str] = []

    if years is None:
        score = (role_relevance or 0.0) * 100.0
        status = "partial"
        rationale = (
            "Exact years of experience were not stated. The score uses role-title "
            f"relevance only ({score:.0f}%) and is marked partial."
        )
        missing.append("Exact years of experience were not stated in the resume.")
    elif role_relevance is None:
        years_ratio = min(float(years) / required_years, 1.0)
        score = years_ratio * 100.0
        status = "partial"
        rationale = (
            f"Resume states {float(years):g} years against a {required_years:g}-year "
            f"requirement ({years_ratio * 100:.0f}%). No job titles were identified for "
            "role relevance, so only the years ratio is used."
        )
        missing.append("No job titles were identified, so role relevance could not be assessed.")
    else:
        years_ratio = min(float(years) / required_years, 1.0)
        score = 0.70 * years_ratio * 100.0 + 0.30 * role_relevance * 100.0
        status = "scored"
        rationale = (
            f"Experience score combines the years requirement "
            f"({years_ratio * 100:.0f}% of {required_years:g} years, 70% sub-weight) "
            f"and role-title relevance ({role_relevance * 100:.0f}%, 30% sub-weight)."
        )

    details = {
        "estimated_years": years,
        "required_years": required_years,
        "years_ratio": round(years_ratio, 4) if years_ratio is not None else None,
        "role_relevance": round(role_relevance, 4) if role_relevance is not None else None,
        "identified_roles": roles,
        "has_internship": bool(exp.get("has_internship")) if isinstance(exp, dict) else False,
        "sub_weights": {"years": 0.70, "role_relevance": 0.30},
    }

    return _make_component(
        "experience",
        weight,
        score,
        status,
        rationale,
        evidence=_experience_evidence(getattr(resume, "raw_text", "") or "", years, roles),
        missing=missing,
        details=details,
        data_quality=dq,
    )


# --------------------------------------------------------------------------- #
# Component 3: Education (D)                                                   #
# --------------------------------------------------------------------------- #
_DEGREE_PATTERNS: List[Tuple[re.Pattern[str], int, str]] = [
    (re.compile(r"\b(?:ph\.?\s?d|doctorate|doctor of philosophy)\b", re.IGNORECASE), 5, "Doctorate"),
    (re.compile(r"\b(?:m\.?\s?tech|master(?:'s)?|m\.?\s?s\.?\s?c?|mba|m\.?\s?c\.?\s?a)\b", re.IGNORECASE), 4, "Master's"),
    (re.compile(r"\b(?:b\.?\s?tech|b\.?\s?e\.?|bachelor(?:'s)?|b\.?\s?s\.?\s?c?|b\.?\s?c\.?\s?a)\b", re.IGNORECASE), 3, "Bachelor's"),
    (re.compile(r"\b(?:diploma|associate(?:'s)?)\b", re.IGNORECASE), 2, "Diploma/Associate"),
    (re.compile(r"\b(?:high school|12th|senior secondary|hsc)\b", re.IGNORECASE), 1, "High School"),
]

_FIELD_GROUPS: Dict[str, List[str]] = {
    "computer_science": [
        "computer science",
        "information technology",
        "software engineering",
        "computer engineering",
        "information systems",
        "cs",
        "it",
    ],
    "data_science": [
        "data science",
        "data analytics",
        "machine learning",
        "artificial intelligence",
        "ai",
        "ml",
    ],
    "electrical_engineering": ["electrical engineering", "electronics engineering", "electronics"],
    "mechanical_engineering": ["mechanical engineering"],
    "civil_engineering": ["civil engineering"],
    "business": ["business administration", "commerce", "management", "mba", "finance"],
}


def _degree_level(text: str) -> Tuple[Optional[int], Optional[str]]:
    if not text:
        return None, None
    for pattern, level, label in _DEGREE_PATTERNS:
        if pattern.search(text):
            return level, label
    return None, None


def _contains_alias(text: str, alias: str) -> bool:
    pattern = rf"(?<![a-z0-9]){re.escape(alias)}(?![a-z0-9])"
    return re.search(pattern, text, re.IGNORECASE) is not None


def _field_relevance(records: List[Dict[str, Any]], required_text: str) -> Tuple[Optional[float], List[str]]:
    required_lower = (required_text or "").lower()
    required_groups = [
        group
        for group, aliases in _FIELD_GROUPS.items()
        if any(_contains_alias(required_lower, alias) for alias in aliases)
    ]
    if not required_groups:
        return None, []

    candidate_text = " ".join(
        f"{record.get('degree', '')} {record.get('institution_context', '')}"
        for record in records
    ).lower()
    matched_groups = [
        group
        for group in required_groups
        if any(_contains_alias(candidate_text, alias) for alias in _FIELD_GROUPS[group])
    ]
    return len(matched_groups) / len(required_groups), matched_groups


def score_education_component(
    resume: Resume,
    job: Job,
    weight: float,
    data_quality: Optional[str] = None,
) -> Dict[str, Any]:
    """
    D compares the candidate's highest parsed degree level with the job's
    required level (80% sub-weight) and field relevance (20% sub-weight).

    If no education records exist, D is ``insufficient_data`` -- not zero.
    If records exist but the degree level cannot be parsed, D is also left
    unscored so a parsing limitation is not mistaken for a lack of education.
    """
    dq = data_quality or _resume_data_quality(resume)
    records = getattr(resume, "extracted_education", None) or []
    records = [r for r in records if isinstance(r, dict)]
    required_text = (getattr(job, "required_education", "") or "").strip()

    if not required_text:
        return _make_component(
            "education",
            weight,
            None,
            "not_applicable",
            "The job specifies no education requirement, so education was excluded.",
            missing=[],
            details={"required_education": required_text},
            data_quality=dq,
        )

    required_level, required_label = _degree_level(required_text)
    if required_level is None:
        return _make_component(
            "education",
            weight,
            None,
            "not_applicable",
            "The job's education requirement could not be interpreted as a degree level, so education was excluded.",
            missing=[],
            details={"required_education": required_text},
            data_quality=dq,
        )

    if not records:
        return _make_component(
            "education",
            weight,
            None,
            "insufficient_data",
            "No education records were extracted from the resume. Education match is unknown, not zero.",
            missing=["No education records were extracted from the resume."],
            details={"required_education": required_text, "required_level": required_label},
            data_quality=dq,
        )

    candidate_level: Optional[int] = None
    candidate_label: Optional[str] = None
    for record in records:
        level, label = _degree_level(
            f"{record.get('degree', '')} {record.get('institution_context', '')}"
        )
        if level is not None and (candidate_level is None or level > candidate_level):
            candidate_level = level
            candidate_label = label

    if candidate_level is None:
        return _make_component(
            "education",
            weight,
            None,
            "insufficient_data",
            "Education records exist, but no degree level could be parsed. This is a parsing limitation, not evidence that the candidate lacks education.",
            missing=["The degree level could not be determined from the extracted education records."],
            details={"required_education": required_text, "required_level": required_label, "records": records},
            data_quality=dq,
        )

    gap = candidate_level - required_level
    if gap >= 0:
        base_score = 100.0
        level_explanation = "meets or exceeds"
    elif gap == -1:
        base_score = 60.0
        level_explanation = "is one level below"
    elif gap == -2:
        base_score = 30.0
        level_explanation = "is two levels below"
    else:
        base_score = 10.0
        level_explanation = "is more than two levels below"

    field_relevance, matched_fields = _field_relevance(records, required_text)
    field_component = 1.0 if field_relevance is None else field_relevance
    score = 0.80 * base_score + 0.20 * field_component * 100.0

    if field_relevance is None:
        field_explanation = "No specific field of study was required."
    else:
        field_explanation = (
            f"Field relevance is {field_relevance * 100:.0f}% "
            f"(matched: {', '.join(matched_fields) if matched_fields else 'none'})."
        )

    rationale = (
        f"Candidate's highest parsed degree ({candidate_label}) {level_explanation} the "
        f"job's requirement ({required_label}). Level sub-score is {base_score:.0f}% "
        f"(80% sub-weight). {field_explanation} (20% sub-weight)."
    )

    evidence = [
        {
            "degree": record.get("degree"),
            "institution_context": record.get("institution_context"),
            "year": record.get("year"),
            "grade_or_cgpa": record.get("grade_or_cgpa"),
        }
        for record in records[:5]
    ]

    details = {
        "required_education": required_text,
        "required_level": required_label,
        "candidate_level": candidate_label,
        "level_gap": gap,
        "level_base_score": base_score,
        "field_relevance": round(field_relevance, 4) if field_relevance is not None else None,
        "matched_field_groups": matched_fields,
        "sub_weights": {"level": 0.80, "field": 0.20},
    }

    return _make_component(
        "education",
        weight,
        score,
        "scored",
        rationale,
        evidence=evidence,
        missing=[],
        details=details,
        data_quality=dq,
    )


# --------------------------------------------------------------------------- #
# Component 4: Projects (P)                                                    #
# --------------------------------------------------------------------------- #
def _project_texts(projects: List[Any]) -> List[Tuple[str, str]]:
    texts: List[Tuple[str, str]] = []
    for project in projects:
        if not isinstance(project, dict):
            continue
        title = str(project.get("title") or "").strip()
        description = str(project.get("description") or "").strip()
        combined = " ".join(part for part in (title, description) if part)
        if combined:
            texts.append((title or "Untitled project", combined))
    return texts


def score_project_component(
    resume: Resume,
    job: Job,
    weight: float,
    data_quality: Optional[str] = None,
) -> Dict[str, Any]:
    """
    P combines required-skill coverage found in project descriptions (70%
    sub-weight) with lexical similarity between project text and the job (30%
    sub-weight). If no projects exist, P is ``insufficient_data`` -- not zero.
    """
    dq = data_quality or _resume_data_quality(resume)
    projects = getattr(resume, "extracted_projects", None) or []
    project_texts = _project_texts(projects)

    if not project_texts:
        return _make_component(
            "projects",
            weight,
            None,
            "insufficient_data",
            "No projects were extracted from the resume. Project relevance is unknown, not zero.",
            missing=["No projects were extracted from the resume; the candidate may still have relevant projects."],
            details={"project_count": 0},
            data_quality=dq,
        )

    combined_text = " ".join(text for _, text in project_texts)
    lexical_similarity = compute_tfidf_similarity(
        sanitize_text_for_scoring(combined_text),
        _job_text(job),
    )
    required = [
        s.strip()
        for s in (getattr(job, "required_skills", None) or [])
        if isinstance(s, str) and s.strip()
    ]

    if required:
        project_skills = extract_skills_from_text(combined_text)
        project_skill_details = compute_skill_match(
            resume_skills=project_skills,
            required_skills=required,
            preferred_skills=[],
            resume_raw_text="",
        )
        coverage = project_skill_details["skill_match_score"]
        score = 0.70 * coverage * 100.0 + 0.30 * lexical_similarity * 100.0
        status = "scored"
        rationale = (
            f"{len(project_skill_details['matched_required'])} of "
            f"{project_skill_details['total_required']} required skills appear in project "
            f"descriptions ({coverage * 100:.0f}%, 70% sub-weight). Project text similarity "
            f"to the job is {lexical_similarity * 100:.0f}% (30% sub-weight)."
        )
        missing: List[str] = []
        details = {
            "project_count": len(project_texts),
            "required_skills": required,
            "matched_required_skills": project_skill_details.get("matched_required", []),
            "missing_required_skills": project_skill_details.get("missing_required", []),
            "skill_coverage": round(coverage, 4),
            "text_similarity": round(lexical_similarity, 4),
            "sub_weights": {"skill_coverage": 0.70, "text_similarity": 0.30},
        }
    else:
        score = lexical_similarity * 100.0
        status = "partial"
        rationale = (
            "The job lists no required skills, so project relevance uses text similarity "
            f"only ({lexical_similarity * 100:.0f}%) and is marked partial."
        )
        missing = []
        details = {
            "project_count": len(project_texts),
            "required_skills": [],
            "text_similarity": round(lexical_similarity, 4),
        }

    evidence: List[Dict[str, Any]] = []
    for title, text in project_texts[:4]:
        project_skills = extract_skills_from_text(text)
        matched_in_project = (
            compute_skill_match(project_skills, required, [], "")["matched_required"]
            if required
            else []
        )
        evidence.append(
            {
                "title": title,
                "description": text[:300],
                "matched_skills": matched_in_project,
            }
        )

    return _make_component(
        "projects",
        weight,
        score,
        status,
        rationale,
        evidence=evidence,
        missing=missing,
        details=details,
        data_quality=dq,
    )


# --------------------------------------------------------------------------- #
# Component 5: Semantic similarity (M)                                         #
# --------------------------------------------------------------------------- #
def score_semantic_component(
    resume: Resume,
    job: Job,
    weight: float,
    semantic_score: Any = _UNSET,
) -> Dict[str, Any]:
    """
    M is the Sentence Transformer cosine similarity scaled from 0-1 to 0-100.

    ``semantic_score`` can be supplied by the caller to avoid computing the
    embedding twice. Passing ``None`` means the model was requested but could not
    produce a score; the component is then excluded, not treated as zero.
    """
    resume_text = sanitize_text_for_scoring(getattr(resume, "raw_text", "") or "")
    job_text = _job_text(job)

    if not resume_text.strip():
        return _make_component(
            "semantic",
            weight,
            None,
            "insufficient_data",
            "The resume has no usable text for semantic comparison. The component is excluded, not scored as zero.",
            missing=["Resume text is empty or could not be read."],
            data_quality="model_generated",
        )

    if semantic_score is _UNSET:
        semantic_score = compute_semantic_similarity_optional(resume_text, job_text)

    if semantic_score is None:
        return _make_component(
            "semantic",
            weight,
            None,
            "insufficient_data",
            "Semantic similarity could not be computed (for example, the model is unavailable). The component is excluded rather than scored as zero.",
            missing=["Semantic similarity could not be computed for this pair."],
            data_quality="model_generated",
        )

    score = float(semantic_score) * 100.0
    return _make_component(
        "semantic",
        weight,
        score,
        "scored",
        f"Semantic cosine similarity between the resume and job text is {float(semantic_score):.4f} ({score:.0f}/100).",
        evidence=[],
        missing=[],
        details={"cosine_similarity": round(float(semantic_score), 4)},
        data_quality="model_generated",
    )


# --------------------------------------------------------------------------- #
# Aggregation                                                                  #
# --------------------------------------------------------------------------- #
def get_weights() -> Dict[str, float]:
    """Return the configured ATS weights (validated by Settings)."""
    return {
        "skills": float(settings.ATS_WEIGHT_SKILL),
        "experience": float(settings.ATS_WEIGHT_EXPERIENCE),
        "education": float(settings.ATS_WEIGHT_EDUCATION),
        "projects": float(settings.ATS_WEIGHT_PROJECT),
        "semantic": float(settings.ATS_WEIGHT_SEMANTIC),
    }


def get_formula(weights: Optional[Dict[str, float]] = None) -> str:
    w = weights or get_weights()
    return (
        f"ATS = {w['skills']:.2f}K + {w['experience']:.2f}E + "
        f"{w['education']:.2f}D + {w['projects']:.2f}P + "
        f"{w['semantic']:.2f}M"
    )


def _aggregate(components: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Combine component scores using renormalised weights.

    Only components with a numeric score participate. Missing components are
    explicitly excluded; they never contribute a zero.
    """
    available = [c for c in components if c["score"] is not None]
    total_weight = sum(c["weight"] for c in available)
    weight_coverage = round(total_weight, 4)
    renormalized = total_weight < 1.0 - 1e-9

    if total_weight > 0:
        ats_score = round(
            sum((c["weight"] / total_weight) * c["score"] for c in available),
            2,
        )
        for component in components:
            if component["score"] is None:
                component["effective_weight"] = 0.0
                component["weighted_contribution"] = 0.0
            else:
                effective = component["weight"] / total_weight
                component["effective_weight"] = round(effective, 6)
                component["weighted_contribution"] = round(effective * component["score"], 2)
    else:
        ats_score = None
        for component in components:
            component["effective_weight"] = 0.0
            component["weighted_contribution"] = 0.0

    if ats_score is None:
        status = "insufficient_data"
    elif all(c["score"] is not None and c["status"] == "scored" for c in components):
        status = "scored"
    else:
        status = "partial"

    resume_components = [c for c in components if c["key"] != "semantic" and c["score"] is not None]
    all_reviewed = bool(resume_components) and all(
        c["data_quality"] == "candidate_reviewed" for c in resume_components
    )
    if ats_score is None:
        confidence = "none"
    elif status == "scored" and all_reviewed:
        confidence = "high"
    elif weight_coverage >= 0.60:
        confidence = "medium"
    else:
        confidence = "low"

    missing_information = [
        {
            "component": c["key"],
            "label": c["label"],
            "items": c["missing_information"],
        }
        for c in components
        if c["missing_information"]
    ]
    unverified_components = [
        c["key"] for c in components if c["data_quality"] == "auto_extracted_unverified"
    ]

    return {
        "ats_score": ats_score,
        "status": status,
        "confidence": confidence,
        "weight_coverage": weight_coverage,
        "renormalized": renormalized,
        "missing_information": missing_information,
        "unverified_components": unverified_components,
        "component_scores": {c["key"]: c["score"] for c in components},
        "effective_weights": {c["key"]: c["effective_weight"] for c in components},
    }


def compute_ats_score(
    resume: Resume,
    job: Job,
    use_semantic: bool = True,
    semantic_score: Any = _UNSET,
) -> Dict[str, Any]:
    """
    Compute the explainable ATS score for one resume-job pair.

    Returns a dict suitable for storage in ``MatchResult.ats_breakdown`` plus
    top-level fields (``ats_score``, ``status``, ``confidence``, ``weights``,
    ``scoring_version``).
    """
    weights = get_weights()
    data_quality = _resume_data_quality(resume)

    components = [
        score_skill_component(resume, job, weights["skills"], data_quality),
        score_experience_component(resume, job, weights["experience"], data_quality),
        score_education_component(resume, job, weights["education"], data_quality),
        score_project_component(resume, job, weights["projects"], data_quality),
    ]

    if use_semantic:
        components.append(
            score_semantic_component(
                resume,
                job,
                weights["semantic"],
                semantic_score=semantic_score,
            )
        )
    else:
        components.append(
            _make_component(
                "semantic",
                weights["semantic"],
                None,
                "not_applicable",
                "Semantic scoring was disabled for this request, so the component was excluded.",
                missing=[],
                data_quality="model_generated",
            )
        )

    aggregate = _aggregate(components)
    breakdown = {
        "components": components,
        "component_scores": aggregate["component_scores"],
        "effective_weights": aggregate["effective_weights"],
        "weight_coverage": aggregate["weight_coverage"],
        "renormalized": aggregate["renormalized"],
        "missing_information": aggregate["missing_information"],
        "unverified_components": aggregate["unverified_components"],
        "formula": get_formula(weights),
        "disclaimer": DISCLAIMER,
        "limitations": LIMITATIONS,
        "scoring_version": settings.ATS_SCORING_VERSION,
        "computed_at": datetime.now(timezone.utc).isoformat(),
        "data_verification": data_quality,
        "status": aggregate["status"],
        "confidence": aggregate["confidence"],
    }

    return {
        "ats_score": aggregate["ats_score"],
        "status": aggregate["status"],
        "confidence": aggregate["confidence"],
        "weights": weights,
        "effective_weights": aggregate["effective_weights"],
        "weight_coverage": aggregate["weight_coverage"],
        "renormalized": aggregate["renormalized"],
        "breakdown": breakdown,
        "scoring_version": settings.ATS_SCORING_VERSION,
    }


# --------------------------------------------------------------------------- #
# Persistence helpers                                                          #
# --------------------------------------------------------------------------- #
def compute_and_store(
    db,
    resume: Resume,
    job: Job,
    use_semantic: bool = True,
) -> Tuple[MatchResult, Dict[str, Any]]:
    """
    Compute both the Phase 6 matching signals and the Phase 7 ATS score, then
    upsert the combined result into ``match_results``.
    """
    # Imported lazily to avoid a circular import at module load time.
    from app.services import match_service

    match_data = match_service.compute_match(resume=resume, job=job, use_semantic=use_semantic)
    ats_data = compute_ats_score(
        resume=resume,
        job=job,
        use_semantic=use_semantic,
        semantic_score=match_data.get("semantic_score") if use_semantic else _UNSET,
    )
    result = match_service.upsert_match_result(db, resume, job, match_data, ats_data=ats_data)
    return result, ats_data


def get_or_compute_for_ranking(
    db,
    resume: Resume,
    job: Job,
    refresh: bool = False,
    use_semantic: bool = True,
) -> MatchResult:
    """
    Return a cached ATS result when available, otherwise compute and store it.
    A result with a null score but a stored breakdown is a valid
    ``insufficient_data`` result and is reused.
    """
    from app.services import match_service

    existing = match_service.get_match_result(db, resume.id, job.id)
    if existing is not None and existing.ats_breakdown and not refresh:
        return existing
    result, _ = compute_and_store(db, resume, job, use_semantic=use_semantic)
    return result


def build_score_response(result: MatchResult) -> Dict[str, Any]:
    """Convert a stored MatchResult into an API response dict."""
    breakdown = result.ats_breakdown or {}
    return {
        "id": result.id,
        "resume_id": result.resume_id,
        "job_id": result.job_id,
        "candidate_id": result.candidate_id,
        "ats_score": result.ats_score,
        "status": result.ats_status or breakdown.get("status") or "insufficient_data",
        "confidence": result.ats_confidence or breakdown.get("confidence") or "none",
        "scoring_version": result.ats_version or breakdown.get("scoring_version") or settings.ATS_SCORING_VERSION,
        "breakdown": breakdown,
        "created_at": result.created_at,
        "updated_at": result.updated_at,
    }


# --------------------------------------------------------------------------- #
# Ranking                                                                      #
# --------------------------------------------------------------------------- #
def build_ranking_item(application, result: MatchResult) -> Dict[str, Any]:
    """Build one ranked-candidate row from an application and its score."""
    breakdown = result.ats_breakdown or {}
    candidate = getattr(application, "candidate", None)
    return {
        "rank": None,
        "application_id": getattr(application, "id", None),
        "candidate_id": application.candidate_id,
        "candidate_name": getattr(candidate, "full_name", None),
        "resume_id": application.resume_id,
        "ats_score": result.ats_score,
        "status": result.ats_status or breakdown.get("status") or "insufficient_data",
        "confidence": result.ats_confidence or breakdown.get("confidence") or "none",
        "component_scores": breakdown.get("component_scores", {}),
        "missing_information": breakdown.get("missing_information", []),
        "explanation_endpoint": f"/api/v1/ats/{application.resume_id}/{application.job_id}",
    }


def build_unscored_ranking_item(application, reason: str) -> Dict[str, Any]:
    """Build a ranking row for an applicant whose score could not be computed."""
    candidate = getattr(application, "candidate", None)
    return {
        "rank": None,
        "application_id": getattr(application, "id", None),
        "candidate_id": application.candidate_id,
        "candidate_name": getattr(candidate, "full_name", None),
        "resume_id": application.resume_id,
        "ats_score": None,
        "status": "insufficient_data",
        "confidence": "none",
        "component_scores": {},
        "missing_information": [
            {
                "component": "system",
                "label": "Scoring",
                "items": [reason],
            }
        ],
        "explanation_endpoint": f"/api/v1/ats/{application.resume_id}/{application.job_id}",
    }


def rank_candidates(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Sort candidates by ATS score (descending) with deterministic tie-breakers:
    skill score, then candidate_id. Unscored candidates are placed last and get
    ``rank = None`` so a missing score is never presented as a low rank.
    """
    def sort_key(item: Dict[str, Any]):
        score = item.get("ats_score")
        skill = (item.get("component_scores") or {}).get("skills")
        return (
            score is None,
            -(score if score is not None else 0.0),
            -(skill if skill is not None else 0.0),
            item.get("candidate_id") or 0,
        )

    ranked = sorted(items, key=sort_key)
    rank = 0
    for item in ranked:
        if item.get("ats_score") is None:
            item["rank"] = None
        else:
            rank += 1
            item["rank"] = rank
    return ranked
