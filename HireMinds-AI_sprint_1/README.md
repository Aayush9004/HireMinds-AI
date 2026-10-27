# HireMinds AI — AI-Powered Recruitment & Candidate Assessment Platform

> **B.Tech Major Project** | Modular Monolithic Architecture | Backend-First Development

---

## 1. Project Overview

**HireMinds AI** is an intelligent candidate evaluation and recruitment decision-support system. It is designed to:
- Help candidates understand how their resumes align with job descriptions.
- Extract skills, experience, and educational qualifications transparently using NLP and rule-based pipelines.
- Match candidates with jobs using both **TF-IDF** (lexical baseline) and **Sentence Transformers** (semantic similarity).
- Calculate ATS scores via a transparent, multi-factor weighted scoring rubric.
- Deliver personalized technical assessments using **Gemini or DeepSeek**, and AI-driven mock interviews using **Google Gemini**.
- Provide recruiters with explainable rankings and evidence-backed profiles while ensuring zero automated rejections.

---

## 2. System Architecture

```text
HireMinds-AI/
├── backend/                  # FastAPI Application (Python)
│   ├── app/
│   │   ├── api/              # API Route Handlers
│   │   │   └── v1/           # Versioned Endpoints (/api/v1)
│   │   │       ├── endpoints/
│   │   │       │   ├── health.py
│   │   │       │   ├── auth.py
│   │   │       │   ├── resumes.py
│   │   │       │   ├── jobs.py
│   │   │       │   ├── matching.py
│   │   │       │   ├── ats.py
│   │   │       │   └── assessments.py
│   │   │       └── api.py    # Router Aggregator
│   │   ├── core/             # Configuration, Security & Database
│   │   │   ├── config.py     # Pydantic Settings, CORS & ATS weights
│   │   │   ├── database.py
│   │   │   └── security.py
│   │   ├── models/           # SQLAlchemy DB Models (Phase 2+)
│   │   ├── schemas/          # Pydantic Request/Response DTOs
│   │   ├── services/         # Business Logic, ML, NLP & LLM Services
│   │   │   ├── resume_parser.py
│   │   │   ├── skill_extractor.py
│   │   │   ├── tfidf_matcher.py
│   │   │   ├── semantic_matcher.py
│   │   │   ├── skill_matcher.py
│   │   │   ├── match_service.py
│   │   │   ├── ats_service.py
│   │   │   ├── llm_client.py
│   │   │   ├── gemini_client.py
│   │   │   ├── deepseek_client.py
│   │   │   ├── coding_sandbox.py
│   │   │   └── assessment_service.py
│   │   └── main.py           # FastAPI entrypoint, middleware, routes
│   ├── alembic/              # Database migration history
│   ├── tests/                # Pytest unit & integration test suites
│   ├── requirements.txt      # Phase-specific pinned dependencies
│   ├── .env.example          # Template environment file
│   └── venv/                 # Isolated Python 3.13 virtual environment
│
├── docs/
│   ├── PHASE7_ATS_SCORING.md # ATS methodology, API contract & limitations
│   └── PHASE8_TECHNICAL_ASSESSMENTS.md # Assessment generation, scoring & sandbox
│
├── frontend/                 # React Application (TypeScript + Vite)
│   ├── src/
│   │   ├── App.tsx           # Foundation verification UI
│   │   └── main.tsx          # React DOM entrypoint
│   ├── index.html
│   ├── package.json
│   ├── tsconfig.json
│   └── vite.config.ts        # Vite config with backend proxy
│
├── .gitignore                # Repository-wide gitignore rules
└── README.md                 # Project documentation & runbook
```

---

## 3. Environment & Prerequisites

Verified on Windows 11:
- **Python**: `3.13.1`
- **Node.js**: `v22.15.0`
- **npm**: `10.9.2`
- **Git**: `2.45.1`
- **MySQL Server**: `8.0.42` (Service `MySQL80` Running)

---

## 4. Phase-by-Phase Roadmap

| Phase | Description | Status |
| :--- | :--- | :--- |
| **Phase 1** | **Environment Verification, Project Scaffolding & Health Check API** | **Completed** |
| **Phase 2** | **MySQL Database Configuration, SQLAlchemy Models & Alembic Migrations** | **Completed** |
| **Phase 3** | **User Authentication, JWT, Argon2 Hashing & Role-Based Access Control** | **Completed** |
| **Phase 4** | **Resume Processing, PDF Parsing (PyMuPDF) & Skill Extraction (spaCy)** | **Completed** |
| **Phase 5** | **Job Management & Candidate Application Workflows** | **Completed** |
| Phase 6 | Matching Algorithms: TF-IDF vs Sentence Transformers Comparison | Completed |
| Phase 7 | ATS Multi-Factor Weighted Scoring & Explainable Candidate Ranking | Completed |
| Phase 8 | Personalized Technical Assessments & MCQ / Code Evaluation | Completed |
| Phase 9 | AI Mock Interview System (Google Gemini API) with Adaptive Feedback | Upcoming |
| Phase 10 | Comprehensive Reporting & Analytics APIs | Upcoming |
| Phase 11 | Complete React Frontend (Candidate & Recruiter Portals) | Upcoming |
| Phase 12 | End-to-End Testing, Security Review & Project Deployment | Upcoming |

---

## 5. Running the Application (Local Development)

### A. Backend (FastAPI)

1. Open PowerShell and navigate to the project root:
   ```powershell
   cd "C:\Users\Aayush\Desktop\Major Project\HireMinds-AI_sprint_1"
   ```

2. Activate the virtual environment:
   ```powershell
   .\backend\venv\Scripts\Activate.ps1
   ```

3. Apply database migrations (includes the Phase 7 ATS columns and Phase 8 assessment tables):
   ```powershell
   $env:PYTHONPATH=".\backend"
   .\backend\venv\Scripts\alembic.exe upgrade head
   ```

4. Set `PYTHONPATH` and launch the development server with hot-reload:
   ```powershell
   $env:PYTHONPATH=".\backend"
   .\backend\venv\Scripts\uvicorn.exe app.main:app --reload --host 127.0.0.1 --port 8000
   ```

5. Access the backend endpoints:
   - **Health Check API**: [http://127.0.0.1:8000/api/v1/health](http://127.0.0.1:8000/api/v1/health)
   - **Interactive Swagger Documentation**: [http://127.0.0.1:8000/api/v1/docs](http://127.0.0.1:8000/api/v1/docs)
   - **ReDoc Documentation**: [http://127.0.0.1:8000/api/v1/redoc](http://127.0.0.1:8000/api/v1/redoc)

### B. Running Backend Tests (Pytest)

Run the test suite from the project root:
```powershell
$env:PYTHONPATH=".\backend"
.\backend\venv\Scripts\pytest .\backend\tests -v
```

Run only the Phase 7 ATS tests:
```powershell
$env:PYTHONPATH=".\backend"
.\backend\venv\Scripts\pytest .\backend\tests\test_ats.py -v
```

Run only the Phase 8 assessment tests:
```powershell
$env:PYTHONPATH=".\backend"
.\backend\venv\Scripts\pytest .\backend\tests\test_assessments.py -v
```

### C. Frontend (React + Vite)

1. Open a second PowerShell terminal and navigate to `frontend`:
   ```powershell
   cd "C:\Users\Aayush\Desktop\Major Project\HireMinds-AI_sprint_1\frontend"
   ```

2. Start the Vite development server:
   ```powershell
   npm run dev
   ```

3. Open your browser at:
   - [http://127.0.0.1:5173](http://127.0.0.1:5173)

---

## 6. Phase 1 Verification Summary

- **Backend Health Check**: Returns HTTP 200 OK with payload:
  ```json
  {
    "status": "healthy",
    "project": "HireMinds AI",
    "version": "0.1.0",
    "environment": "development",
    "timestamp": "2026-10-26T18:57:43.256340Z",
    "services": {
      "api": "online",
      "phase": "1 - Foundation & Health Check",
      "database": "pending_phase_2"
    }
  }
  ```
- **Automated Tests**: Pytest test suite executed:
  - `test_health_check_endpoint`: PASSED
  - `test_root_redirect_to_docs`: PASSED
- **Frontend Verification**: TypeScript compilation passed (`npm run build`), and Vite development server is active, connecting to the backend `/api/v1/health` endpoint through proxy.

---

## 7. Phase 6 & 7 — Matching and Explainable ATS Scoring

### Matching signals (Phase 6)

- **TF-IDF** lexical similarity for a fast, explainable baseline.
- **Sentence Transformers** (`all-MiniLM-L6-v2`) semantic similarity.
- **Skill matching** with alias handling (`js` → `javascript`, `ml` → `machine learning`).
- Cached results are stored in `match_results`; semantic failures are treated as
  unavailable, not as a zero similarity.

### ATS formula (Phase 7)

```text
ATS = 0.40K + 0.25E + 0.15D + 0.10P + 0.10M
```

| Symbol | Component | Default weight |
| :--- | :--- | ---: |
| `K` | Skill match | 0.40 |
| `E` | Experience relevance | 0.25 |
| `D` | Education match | 0.15 |
| `P` | Project relevance | 0.10 |
| `M` | Semantic similarity | 0.10 |

Each component is normalised to **0–100**, and the weighted ATS score is also
**0–100**.

> **These weights are initial assumptions, not scientifically validated hiring
> criteria.** They are configurable via `ATS_WEIGHT_*` environment variables and
> are validated to sum to `1.0`.

### Explainability and missing data

Every score stores and returns:

- component scores and configured/effective weights,
- a plain-language rationale for each component,
- evidence for matched skills, experience, education and projects,
- explicit `missing_information` notes,
- a `confidence` level and the scoring version,
- a disclaimer and a list of limitations.

If a component cannot be assessed, its score is `null` and it is **excluded**
from the weighted sum; the remaining weights are renormalised. Missing
information is never converted into a zero score. Automatically extracted resume
data is marked `auto_extracted_unverified` until the candidate reviews it.

### ATS APIs

Base path: `/api/v1/ats`

| Method | Endpoint | Purpose |
| :--- | :--- | :--- |
| `GET` | `/weights` | Current weights, formula, missing-data policy and limitations |
| `POST` | `/compute/{resume_id}/{job_id}` | Compute and store an ATS score and explanation |
| `GET` | `/{resume_id}/{job_id}` | Retrieve a stored score and explanation |
| `GET` | `/rankings/{job_id}` | Rank applicants for a recruiter-owned job |

Ranking rules: scored candidates are ordered by ATS score (tie-breakers: skill
score, then `candidate_id`). Unscored candidates appear last with `rank = null`,
so missing data is never presented as a low rank. The API **never rejects a
candidate** or changes an application status based on score.

### Fairness safeguards

- No protected or sensitive personal characteristics are explicit scoring inputs.
- Similarity text is sanitised to remove obvious emails, phone numbers, URLs and
  explicit protected-characteristic lines (best-effort only).
- Semantic models can encode societal biases; human review is required.

Full methodology, response examples and limitations:
[`docs/PHASE7_ATS_SCORING.md`](docs/PHASE7_ATS_SCORING.md).

### Verification

- **Phase 7 tests**: `29 passed` (`backend/tests/test_ats.py`) covering the
  formula, normalisation, missing-data renormalisation, all five components,
  evidence, ranking, weight validation and the public weights endpoint.
- **OpenAPI**: 28 paths, including all four `/api/v1/ats` routes.
- **Database**: apply the Phase 7 migration with
  `PYTHONPATH=. ./venv/bin/alembic upgrade head` from `backend/`.

---

## 8. Phase 8 — Personalized Technical Assessments

Phase 8 generates job-specific MCQ and coding questions with Gemini or
DeepSeek, evaluates answers deterministically, and stores every attempt and
result.

### Generation

- The configured LLM provider (`LLM_PROVIDER=gemini` or `deepseek`) is called
  through a small `httpx` REST client; the API key comes from
  `GEMINI_API_KEY` or `DEEPSEEK_API_KEY` and is never logged or stored.
- Prompts are grounded in the job's requirements and, optionally, the skills of
  a candidate who applied to that job.
- LLM output is treated as untrusted and validated before persistence:
  2–6 unique MCQ options, a correct answer that matches an option, valid Python
  function names, and at least one coding test case.
- Missing API key → `503`; timeout → `504`; invalid/blocked LLM response →
  `502`; validation failure → `422`. Failed generations store nothing.

### LLM provider configuration

Set the provider in `backend/.env`:

```env
# Use Gemini
LLM_PROVIDER=gemini
GEMINI_API_KEY=your-gemini-key

# OR use DeepSeek
LLM_PROVIDER=deepseek
DEEPSEEK_API_KEY=your-deepseek-key
DEEPSEEK_MODEL=deepseek-chat
DEEPSEEK_API_BASE_URL=https://api.deepseek.com
```

Only the selected provider's key is required. Keys are never logged or stored
in the database.

### Deterministic scoring

```text
MCQ:     points if selected_option == correct_answer, else 0
Coding:  points * passed_test_cases / total_test_cases
Overall: earned_points / evaluated_points * 100
```

Unanswered MCQs count as incorrect. If the coding sandbox is unavailable,
coding answers are stored as `not_evaluated` and **excluded** from the score
denominator — they are never treated as wrong or scored as zero.

### Coding sandbox

Candidate code is **never executed inside the FastAPI process**. Execution is
disabled by default (`CODE_EXECUTION_ENABLED=false`). When enabled, only Docker
is supported and containers run with `--network none`, `--read-only`, memory/CPU
and PID limits, all capabilities dropped, `no-new-privileges`, and an
unprivileged user. Access to the Docker socket is effectively root-equivalent;
deploy with a restricted Docker context or dedicated sandbox host.

### Assessment APIs

Base path: `/api/v1/assessments`

| Method | Endpoint | Role | Purpose |
| :--- | :--- | :--- | :--- |
| `POST` | `/generate` | Recruiter | Generate and store an assessment |
| `GET` | `/` | Recruiter | List own assessments |
| `GET` | `/{assessment_id}` | Recruiter | Full assessment with answers/tests |
| `GET` | `/{assessment_id}/attempts` | Recruiter | Attempt summaries |
| `POST` | `/{assessment_id}/start` | Candidate | Start or resume an attempt |
| `POST` | `/attempts/{attempt_id}/submit` | Candidate | Submit and score answers |
| `GET` | `/attempts/{attempt_id}/result` | Owner/Recruiter/Admin | Read a result |

Candidates never receive correct answers, explanations or hidden test cases.
Only the attempt owner, the assessment owner and admins can read a result.
Starting twice resumes an in-progress attempt; submitting twice returns `409`.

Full methodology, sandbox limitations and examples:
[`docs/PHASE8_TECHNICAL_ASSESSMENTS.md`](docs/PHASE8_TECHNICAL_ASSESSMENTS.md).

### Verification

- **Phase 8 tests**: `53 passed` (`backend/tests/test_assessments.py`) covering
  generation validation, Gemini/DeepSeek failures, deterministic MCQ/coding scoring,
  sandbox defaults and Docker flags, ownership and API flows.
- **OpenAPI**: 35 paths, including all seven `/api/v1/assessments` routes.
- **Migration head**: `8b7d4e2f1a90` (single head). Apply with
  `PYTHONPATH=. ./venv/bin/alembic upgrade head` from `backend/`.
- **Known blocker**: the local MySQL server rejects the configured credentials
  (`Access denied for user 'root'@'localhost'`), so the migration and
  DB-backed smoke tests must be re-run once valid credentials are supplied.
  All Phase 8 tests use in-memory SQLite and pass without MySQL.
