"""
Skill-based matching service.

How it works (student explanation):
-------------------------------------
While TF-IDF and semantic matching look at the ENTIRE text, this module
focuses specifically on the SKILLS listed in:
  • The job's `required_skills` and `preferred_skills` fields
  • The candidate's `extracted_skills` from their resume

Steps:
1. Normalise all skill names to lowercase and strip whitespace.
2. Build a skill-→-aliases mapping (e.g. "js" → "javascript").
3. For every required job skill, check whether a matching skill
   (direct or via alias) exists in the resume skills.
4. Calculate:
     skill_match_score = matched_required / total_required
5. Return a detailed breakdown with evidence.

Skill normalisation is important because:
  • A resume may say "JS" but the job lists "JavaScript"
  • "ML" and "Machine Learning" should be treated as the same skill

Strengths:
  ✔ Very precise – direct comparison at the skills level
  ✔ Provides clear explainability ("missing: Kubernetes, Docker")

Limitations:
  ✗ Only as good as the extracted skills list
  ✗ Cannot discover skills mentioned in prose text
"""
from __future__ import annotations

from typing import Dict, List, Set, Tuple, Any

# ---------------------------------------------------------------------------
# Skill alias table
# Each entry maps a canonical name → set of alternative spellings.
# The canonical name must be lowercase.
# ---------------------------------------------------------------------------
SKILL_ALIASES: Dict[str, Set[str]] = {
    "javascript": {"js", "javascript", "ecmascript", "es6", "es2015"},
    "typescript": {"ts", "typescript"},
    "python": {"python", "python3", "py"},
    "machine learning": {"ml", "machine learning", "machine-learning"},
    "deep learning": {"dl", "deep learning", "deep-learning"},
    "natural language processing": {"nlp", "natural language processing", "natural-language-processing"},
    "artificial intelligence": {"ai", "artificial intelligence"},
    "react": {"react", "reactjs", "react.js"},
    "node.js": {"node", "nodejs", "node.js"},
    "vue.js": {"vue", "vuejs", "vue.js"},
    "angular": {"angular", "angularjs", "angular.js"},
    "postgresql": {"postgres", "postgresql", "pgsql"},
    "mysql": {"mysql", "mariadb"},
    "mongodb": {"mongodb", "mongo"},
    "docker": {"docker", "dockerfile"},
    "kubernetes": {"k8s", "kubernetes"},
    "amazon web services": {"aws", "amazon web services", "amazon aws"},
    "google cloud platform": {"gcp", "google cloud", "google cloud platform"},
    "microsoft azure": {"azure", "microsoft azure"},
    "continuous integration": {"ci", "ci/cd", "continuous integration"},
    "c++": {"c++", "cpp", "c plus plus"},
    "scikit-learn": {"sklearn", "scikit-learn", "scikit learn"},
    "tensorflow": {"tensorflow", "tf"},
    "pytorch": {"pytorch", "torch"},
    "fastapi": {"fastapi", "fast api"},
    "django": {"django"},
    "flask": {"flask"},
    "rest api": {"rest", "rest api", "restful", "restful api"},
    "graphql": {"graphql", "gql"},
    "git": {"git", "github", "gitlab"},
    "linux": {"linux", "unix"},
    "sql": {"sql", "structured query language"},
    "nosql": {"nosql", "no-sql", "no sql"},
    "redis": {"redis"},
    "elasticsearch": {"elasticsearch", "elastic search", "elk"},
    "spark": {"apache spark", "pyspark", "spark"},
    "hadoop": {"hadoop", "hdfs"},
    "pandas": {"pandas"},
    "numpy": {"numpy", "np"},
    "java": {"java"},
    "spring": {"spring", "spring boot", "springboot"},
    "kotlin": {"kotlin"},
    "swift": {"swift"},
    "go": {"go", "golang"},
    "rust": {"rust"},
    "php": {"php"},
    "laravel": {"laravel"},
    "ruby": {"ruby", "ruby on rails", "rails"},
    "html": {"html", "html5"},
    "css": {"css", "css3", "scss", "sass"},
    "data structures": {"data structures", "dsa", "algorithms"},
    "agile": {"agile", "scrum", "kanban"},
}


def _build_canonical_lookup() -> Dict[str, str]:
    """
    Invert the SKILL_ALIASES table to get: alias → canonical_name.
    This lets us normalise any skill name in O(1) time.
    """
    lookup: Dict[str, str] = {}
    for canonical, aliases in SKILL_ALIASES.items():
        for alias in aliases:
            lookup[alias.lower().strip()] = canonical
    return lookup


# Build once at module load time
_ALIAS_LOOKUP: Dict[str, str] = _build_canonical_lookup()


def _normalise(skill: str) -> str:
    """
    Normalise a skill string:
    1. Lowercase + strip
    2. Map via alias table to canonical form
    """
    normalised = skill.lower().strip()
    return _ALIAS_LOOKUP.get(normalised, normalised)


def _normalise_list(skills: List[str]) -> Set[str]:
    """Return a set of normalised skill strings from a list."""
    return {_normalise(s) for s in skills if s and s.strip()}


def compute_skill_match(
    resume_skills: List[str],
    required_skills: List[str],
    preferred_skills: List[str],
    resume_raw_text: str = "",
) -> Dict[str, Any]:
    """
    Compare resume skills against job requirements.

    Parameters
    ----------
    resume_skills : list of str
        Skills extracted from the resume.
    required_skills : list of str
        Skills marked as required in the job listing.
    preferred_skills : list of str
        Skills marked as preferred/nice-to-have in the job listing.
    resume_raw_text : str
        Full resume text for evidence lookup (searches for skill mentions).

    Returns
    -------
    dict with keys:
        skill_match_score      float  0–1
        matched_required       list of str
        missing_required       list of str
        matched_preferred      list of str
        missing_preferred      list of str
        evidence               dict {skill: str} – sentence from resume
        total_required         int
        total_preferred        int
    """
    # Normalise all skill lists
    resume_norm = _normalise_list(resume_skills)
    required_norm = [_normalise(s) for s in required_skills if s and s.strip()]
    preferred_norm = [_normalise(s) for s in preferred_skills if s and s.strip()]

    # Unique required / preferred (preserve original casing for display)
    req_map: Dict[str, str] = {
        _normalise(s): s for s in required_skills if s and s.strip()
    }
    pref_map: Dict[str, str] = {
        _normalise(s): s for s in preferred_skills if s and s.strip()
    }

    # Matching logic
    matched_req_norm: List[str] = [sk for sk in req_map if sk in resume_norm]
    missing_req_norm: List[str] = [sk for sk in req_map if sk not in resume_norm]
    matched_pref_norm: List[str] = [sk for sk in pref_map if sk in resume_norm]
    missing_pref_norm: List[str] = [sk for sk in pref_map if sk not in resume_norm]

    # Skill match score: fraction of required skills found
    total_required = len(req_map)
    skill_match_score = (
        round(len(matched_req_norm) / total_required, 4) if total_required > 0 else 1.0
    )

    # Build evidence from resume text (first sentence containing the skill)
    evidence: Dict[str, str] = {}
    if resume_raw_text:
        sentences = [s.strip() for s in resume_raw_text.replace("\n", " ").split(".") if s.strip()]
        for sk in matched_req_norm + matched_pref_norm:
            original_label = req_map.get(sk) or pref_map.get(sk, sk)
            for sentence in sentences:
                if sk in sentence.lower():
                    evidence[original_label] = sentence[:200]  # cap length
                    break

    return {
        "skill_match_score": skill_match_score,
        "matched_required": [req_map[sk] for sk in matched_req_norm],
        "missing_required": [req_map[sk] for sk in missing_req_norm],
        "matched_preferred": [pref_map[sk] for sk in matched_pref_norm],
        "missing_preferred": [pref_map[sk] for sk in missing_pref_norm],
        "evidence": evidence,
        "total_required": total_required,
        "total_preferred": len(pref_map),
        "total_resume_skills": len(resume_skills),
    }
