# Phase 7 — Explainable ATS Scoring & Candidate Ranking

> **Status:** Implemented (backend only; no frontend in this phase)
>
> **Important:** The weights below are initial assumptions for this project.
> They are **not** scientifically validated hiring criteria and must not be
> treated as an objective measure of a person's ability.

---

## 1. Purpose

Phase 7 adds a transparent, explainable ATS-style score to the existing
resume–job matching pipeline. Every score is accompanied by:

- the contribution of each component,
- the configured and effective weights,
- a plain-language rationale,
- supporting evidence,
- explicit notes about missing or unverified information,
- a confidence level and limitations.

The system is **decision support only**. It never automatically rejects a
candidate and never changes an application status.

---

## 2. Formula

```
ATS = w_skill * K + w_experience * E + w_education * D
      + w_projects * P + w_semantic * M
```

| Symbol | Component | Default weight | Scale |
| :--- | :--- | ---: | :--- |
| `K` | Skill match | 0.40 | 0–100 |
| `E` | Experience relevance | 0.25 | 0–100 |
| `D` | Education match | 0.15 | 0–100 |
| `P` | Project relevance | 0.10 | 0–100 |
| `M` | Semantic similarity | 0.10 | 0–100 |

The resulting ATS score is normalised to **0–100**.

### Configurable weights

Weights are environment-configurable and validated at startup to sum to 1.0:

```env
ATS_WEIGHT_SKILL=0.40
ATS_WEIGHT_EXPERIENCE=0.25
ATS_WEIGHT_EDUCATION=0.15
ATS_WEIGHT_PROJECT=0.10
ATS_WEIGHT_SEMANTIC=0.10
ATS_SCORING_VERSION=ats-v1.0
```

Every stored score includes a snapshot of the weights and scoring version used,
so historical scores remain interpretable after configuration changes.

---

## 3. Component definitions

### K — Skill match (40%)

- Compares the job's `required_skills` with the candidate's extracted skills.
- Uses the existing alias table (for example `js` → `javascript`,
  `ml` → `machine learning`).
- `K = matched_required / total_required * 100`.
- Preferred skills are reported as supporting evidence but do not increase `K`.
  If the job has only preferred skills, they are used and the component is
  marked `partial`.
- If no skills could be extracted, `K` is **null** (`insufficient_data`), not 0.
- Evidence: the resume sentence where each matched skill appears.

### E — Experience relevance (25%)

- Combines the years-of-experience ratio (70% sub-weight) with role-title
  relevance (30% sub-weight).
- Years ratio is capped at 1.0, so over-qualification is not penalised.
- Role relevance uses TF-IDF similarity between the identified role titles and
  the job text.
- If the job has no minimum experience requirement, `E` is `not_applicable` and
  excluded.
- If years are missing but role titles exist, `E` is `partial` and uses role
  relevance only — never an assumed zero.
- If both are missing, `E` is `null` (`insufficient_data`).
- Evidence: sentences mentioning years, experience, internships or role titles.

### D — Education match (15%)

- Parses the required education text into a degree level (Doctorate, Master's,
  Bachelor's, Diploma/Associate, High School).
- Compares the candidate's highest parsed degree with the requirement:
  - meets/exceeds → 100 level sub-score
  - one level below → 60
  - two levels below → 30
  - more than two levels below → 10
- 80% sub-weight for level, 20% for field-of-study relevance.
- If no education records exist, `D` is `null` (`insufficient_data`).
- If records exist but the degree level cannot be parsed, `D` is also `null`;
  a parsing limitation is not treated as a lack of education.
- Evidence: degree, institution context, year and grade/CGPA.

### P — Project relevance (10%)

- Uses the extracted project titles and descriptions.
- 70% sub-weight: required-skill coverage found in project descriptions.
- 30% sub-weight: TF-IDF similarity between project text and the job.
- If no projects were extracted, `P` is `null` (`insufficient_data`).
- If the job has no required skills, text similarity alone is used and the
  component is marked `partial`.
- Evidence: project title, description snippet and matched skills.

### M — Semantic similarity (10%)

- Sentence Transformer cosine similarity (`all-MiniLM-L6-v2`) scaled to 0–100.
- If the model is unavailable or cannot produce a score, `M` is `null`
  (`insufficient_data`), not 0.
- Semantic scoring can be disabled per request. It is then `not_applicable`.

---

## 4. Missing and unverified information

This is a core design rule:

> **Missing information is never silently treated as proof of a lack of ability.**

When a component cannot be assessed:

1. Its score is `null`.
2. Its status is `insufficient_data` or `not_applicable`.
3. It contributes 0 to the weighted sum only because it is **excluded**.
4. The remaining component weights are renormalised.
5. `weight_coverage`, `renormalized` and `missing_information` are stored and
   returned so the user can see what happened.
6. Confidence is lowered when coverage or verification is incomplete.

Example: if experience is unknown, the other four components keep their relative
importance and the ATS score is computed from them. The response explicitly says
that experience was excluded.

### Verification status

Resume-derived components are labelled:

- `candidate_reviewed` — the candidate reviewed/corrected the extracted data.
- `auto_extracted_unverified` — parsed automatically and not yet reviewed.

Unverified data is still scored, but confidence is capped at `medium`. The
semantic component is labelled `model_generated`.

---

## 5. Persistence

The score is stored on the existing cached `match_results` row:

| Column | Purpose |
| :--- | :--- |
| `ats_score` | Weighted score 0–100 (nullable) |
| `ats_breakdown` | Full JSON breakdown: components, evidence, rationales, missing data, limitations |
| `ats_weights` | Weight snapshot used for this score |
| `ats_version` | Scoring version |
| `ats_confidence` | `high`, `medium`, `low`, `none` |
| `ats_status` | `scored`, `partial`, `insufficient_data` |

Migration: `7f3c9a1b2d4e_add_ats_scoring_to_match_results.py`.

Run it with:

```bash
cd backend
PYTHONPATH=. ./venv/bin/alembic upgrade head
```

---

## 6. APIs

Base path: `/api/v1/ats`

### `GET /ats/weights`

Public transparency endpoint. Returns current weights, formula, scoring version,
missing-data policy, disclaimer and limitations.

### `POST /ats/compute/{resume_id}/{job_id}`

Computes and stores the Phase 6 matching signals plus the Phase 7 ATS score.

Request body:

```json
{ "use_semantic": true }
```

Access: resume owner, the job's recruiter, or an admin.

### `GET /ats/{resume_id}/{job_id}`

Returns the stored score and full explanation.

Access: resume owner, the job's recruiter, or an admin.

### `GET /ats/rankings/{job_id}`

Returns a paginated ranking of candidates who applied to the job.

Query parameters:

- `page` (default 1)
- `page_size` (default 10, max 100)
- `refresh` (default `false`) — recompute every applicant's score
- `use_semantic` (default `true`) — include semantic similarity when computing
  missing scores

Access: the recruiter who owns the job, or an admin.

Ranking rules:

1. Scored candidates are sorted by `ats_score` descending.
2. Tie-breakers: skill score descending, then `candidate_id` ascending.
3. Unscored candidates appear last with `rank = null`; they are never presented
   as low-ranked.
4. Cached scores are reused. Missing scores are computed on demand.

This endpoint does **not** reject candidates or change application status.

### Example response shape

```json
{
  "id": 12,
  "resume_id": 3,
  "job_id": 7,
  "candidate_id": 5,
  "ats_score": 86.63,
  "status": "partial",
  "confidence": "medium",
  "scoring_version": "ats-v1.0",
  "breakdown": {
    "formula": "ATS = 0.40K + 0.25E + 0.15D + 0.10P + 0.10M",
    "component_scores": {
      "skills": 100.0,
      "experience": 71.92,
      "education": 100.0,
      "projects": 49.84,
      "semantic": null
    },
    "effective_weights": {
      "skills": 0.444444,
      "experience": 0.277778,
      "education": 0.166667,
      "projects": 0.111111,
      "semantic": 0.0
    },
    "weight_coverage": 0.9,
    "renormalized": true,
    "components": [
      {
        "key": "skills",
        "label": "Skill Match",
        "score": 100.0,
        "status": "scored",
        "rationale": "Matched 3 of 3 required skills (100%)...",
        "evidence": [
          { "skill": "Python", "evidence": "Built REST APIs using FastAPI and MySQL." }
        ],
        "missing_information": [],
        "data_quality": "auto_extracted_unverified"
      }
    ],
    "missing_information": [],
    "unverified_components": ["skills", "experience", "education", "projects"],
    "disclaimer": "ATS scores are explainable decision-support signals, not hiring decisions...",
    "limitations": ["..."]
  }
}
```

---

## 7. Fairness safeguards

- No protected or sensitive personal characteristics are explicit scoring
  inputs.
- The database models used for scoring contain no gender, age, religion, caste,
  marital status, disability or nationality fields.
- Text used for similarity scoring is sanitised to remove obvious emails, phone
  numbers, URLs and lines containing explicit protected-characteristic labels.
- This sanitisation is **best-effort only**. Names and implicit proxies can
  remain in free text, and semantic models can encode societal biases.
- Human review is required. Scores are not hiring decisions.
- Scores are comparable only within the same job, scoring version and weight
  configuration.

---

## 8. Limitations

1. The weights are initial assumptions, not scientifically validated criteria.
2. Heuristic parsing can miss non-standard resumes, degrees or role titles.
3. Semantic embeddings may encode bias and are sensitive to writing style.
4. Renormalising weights when data is missing changes the effective rubric and
   reduces comparability between candidates.
5. Education field matching uses a small, project-specific keyword map.
6. Experience role relevance is lexical (TF-IDF), not a deep occupational
   taxonomy.
7. A high score is not proof of competence; a low score is not proof of
   inability.
8. The system does not automatically reject candidates and must not be used as
   the sole basis for a hiring decision.

---

## 9. Tests

`backend/tests/test_ats.py` contains hermetic unit tests covering:

- the weighted formula and 0–100 normalisation,
- renormalisation when components are missing,
- all-missing edge case,
- skill, experience, education, project and semantic components,
- evidence generation,
- missing/unverified information behaviour,
- ranking order, tie-breakers and unscored candidates,
- configurable weight validation,
- text sanitisation,
- the public weights endpoint.

Run only the Phase 7 tests:

```bash
cd backend
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. ./venv/bin/pytest tests/test_ats.py -q -p no:cacheprovider
```
