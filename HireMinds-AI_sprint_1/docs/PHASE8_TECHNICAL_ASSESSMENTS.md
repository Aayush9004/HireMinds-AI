# Phase 8 — Personalized Technical Assessments

> **Status:** Implemented (backend only; no frontend in this phase)
>
> **Important:** Generated questions are AI-assisted drafts. A recruiter should
> review correctness, job relevance and fairness before using an assessment for
> a real hiring decision. Scores are decision support, never an automatic
> rejection mechanism.

---

## 1. Purpose

Phase 8 adds personalized technical assessments to HireMinds AI:

- Generate job-specific **multiple-choice (MCQ)** and **coding** questions from
  the job requirements and, optionally, an applicant's extracted skills.
- Validate every LLM response strictly before anything is stored.
- Let candidates start and submit assessments exactly once.
- Score MCQ answers deterministically by comparing option keys.
- Evaluate coding submissions only inside a secure, isolated sandbox.
- Store attempts, per-question answers and reproducible result breakdowns.
- Enforce ownership so candidates cannot read other candidates' results and
  recruiters cannot read other recruiters' assessments.

---

## 2. Configuration

All settings are read from environment variables / `backend/.env`
(see `backend/.env.example`).

```env
# LLM provider: gemini | deepseek
LLM_PROVIDER=gemini

# Gemini provider (official google-genai SDK)
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-flash-lite-latest
GEMINI_TIMEOUT_SECONDS=180
GEMINI_MAX_OUTPUT_TOKENS=8192
GEMINI_TEMPERATURE=0.4
# Optional legacy REST base URL; the SDK appends its own API version.
# GEMINI_API_BASE_URL=https://generativelanguage.googleapis.com/v1beta

# DeepSeek provider (OpenAI-compatible chat completions)
DEEPSEEK_API_KEY=your_deepseek_api_key_here
DEEPSEEK_MODEL=deepseek-chat
DEEPSEEK_API_BASE_URL=https://api.deepseek.com
DEEPSEEK_TIMEOUT_SECONDS=60
DEEPSEEK_MAX_OUTPUT_TOKENS=8192
DEEPSEEK_TEMPERATURE=0.4

# Assessment defaults
ASSESSMENT_PROMPT_VERSION=assessment-v1
ASSESSMENT_MAX_MCQ_QUESTIONS=20
ASSESSMENT_MAX_CODING_QUESTIONS=5
ASSESSMENT_DEFAULT_DURATION_MINUTES=60
ASSESSMENT_DEFAULT_PASSING_SCORE=60

# Coding sandbox (DISABLED by default)
CODE_EXECUTION_ENABLED=false
CODE_EXECUTION_BACKEND=disabled
CODE_EXECUTION_DOCKER_BINARY=docker
CODE_EXECUTION_DOCKER_IMAGE=python:3.12-slim
CODE_EXECUTION_TIMEOUT_SECONDS=10
CODE_EXECUTION_STARTUP_GRACE_SECONDS=5
CODE_EXECUTION_MEMORY_MB=256
CODE_EXECUTION_CPU_LIMIT=0.5
CODE_EXECUTION_PIDS_LIMIT=64
CODE_EXECUTION_MAX_OUTPUT_BYTES=10000
```

`LLM_PROVIDER` selects the provider. API keys are intentionally empty by
default; generation returns `503 Service Unavailable` until the selected
provider's key is supplied. Keys are never logged and are never stored in the
database.

---

## 3. LLM integration (Gemini or DeepSeek)

Both providers implement the same small `generate_json(prompt)` interface in
`backend/app/services/llm_client.py`, and the provider is selected by
`LLM_PROVIDER`.

### Gemini

`backend/app/services/gemini_client.py` uses the official
[`google-genai`](https://pypi.org/project/google-genai/) Python SDK.

- The SDK client is built with `genai.Client(api_key=..., http_options=...)`;
  the key comes from `GEMINI_API_KEY` and is never logged.
- **Model verification:** before the first generation request,
  `client.models.get(model=GEMINI_MODEL)` confirms the configured model exists.
  The result is cached per client instance.
- Requests JSON output via `GenerateContentConfig(response_mime_type="application/json")`.
- `GEMINI_TIMEOUT_SECONDS` is passed to the SDK in milliseconds.
- `GEMINI_API_BASE_URL` is a legacy REST setting; if supplied, the trailing
  `/v1beta` (or `/v1`) segment is stripped because the SDK appends its own API
  version.
- A `404 NOT_FOUND` from generation usually means the model was retired or is
  unavailable to the key. The client raises `LLMConfigurationError` with a
  message to update `GEMINI_MODEL` (for example to `gemini-flash-lite-latest`).

### DeepSeek

`backend/app/services/deepseek_client.py` uses DeepSeek's OpenAI-compatible
chat-completions API.

- Endpoint: `POST {DEEPSEEK_API_BASE_URL}/chat/completions`
- Sends `Authorization: Bearer <DEEPSEEK_API_KEY>`.
- Requests JSON output (`response_format: {"type": "json_object"}`).
- Default model: `deepseek-chat` (use `deepseek-reasoner` only if your account
  supports it with JSON mode).

Both clients extract JSON even if the model wraps it in Markdown fences or
prose, and map failures to shared exception types:

| Exception | HTTP status returned by the API |
| :--- | ---: |
| `LLMConfigurationError` (missing key / unsupported provider) | `503` |
| `LLMTimeoutError` | `504` |
| `LLMResponseError` (blocked / empty / non-JSON) | `502` |
| `LLMAPIError` (HTTP/transport failure, 429 rate limits, 5xx) | `502` |

Gemini-specific exception names (`GeminiConfigurationError`, etc.) remain as
aliases for backwards compatibility. A retired or unsupported Gemini model is
reported as `LLMConfigurationError` (`503`) with instructions to update
`GEMINI_MODEL`.

No assessment is persisted when generation fails. The database transaction is
rolled back before the error is returned.

---

## 4. Generation and validation

`backend/app/services/assessment_service.py` builds a strict JSON-only prompt
grounded in:

- job title, company, description, required/preferred skills, experience and
  education requirements,
- the candidate's skills (reviewed/corrected skills take precedence over
  auto-extracted skills),
- requested counts, difficulty and optional recruiter instructions,
- an explicit instruction to avoid protected personal characteristics.

The LLM response is treated as **untrusted input** and validated:

### MCQ validation

- Question text must be non-empty.
- Options may be a list, a dict, or a list of strings; they are normalised to
  `{key, text}`.
- Between 2 and 6 options are required.
- Option keys must be unique and non-empty.
- `correct_answer` must match an option key **or** an option's exact text.
  Numeric indices are also accepted and mapped to the corresponding key.
- Points must be greater than 0.
- Difficulty is normalised to `easy`, `medium` or `hard` (default `medium`).

### Coding validation

- Only **Python** is supported.
- `function_name` must be a valid Python identifier.
- At least one test case is required; each test case must contain `input` and
  `expected`.
- `time_limit_ms` is clamped to 100–30000 ms (default 5000).
- `memory_limit_mb` is clamped to 64–2048 MB (default 256).
- A starter template is generated when the model omits `starter_code`.

### Response shapes accepted

The validator accepts a top-level object with `mcq_questions` /
`coding_questions` (and common aliases), or a flat `questions` array whose items
are typed by `question_type`. Extra questions beyond the requested count are
truncated.

Invalid output raises `AssessmentGenerationError`, which the API returns as
`422 Unprocessable Entity`.

---

## 5. Data model

Migration: `backend/alembic/versions/8b7d4e2f1a90_add_technical_assessment_tables.py`
(revision `8b7d4e2f1a90`, down-revision `7f3c9a1b2d4e`).

| Table | Purpose |
| :--- | :--- |
| `assessments` | One job-specific assessment owned by a recruiter. |
| `assessment_questions` | MCQ/coding questions, options, correct answers, test cases and limits. |
| `assessment_attempts` | One candidate attempt per assessment (`UNIQUE(assessment_id, candidate_id)`). |
| `assessment_answers` | One answer per question per attempt (`UNIQUE(attempt_id, question_id)`). |

### Assessment lifecycle

- Generated assessments are stored with status `active`.
- `archived` is reserved for future recruiter workflows; archived assessments
  cannot be started.
- `duration_minutes` and `passing_score` are stored for display/reporting. The
  score is informational; nothing is auto-rejected.

### Attempt lifecycle

| Status | Meaning |
| :--- | :--- |
| `in_progress` | Started but not submitted. Starting again resumes this attempt. |
| `evaluated` | All questions (including coding) were evaluated. |
| `partially_evaluated` | Some questions could not be evaluated (for example, no sandbox). |
| `submitted` | Reserved intermediate status; submissions are evaluated immediately. |

Starting an assessment twice returns the same in-progress attempt. Starting
after a submission returns `409 Conflict` — only one attempt is allowed per
candidate per assessment.

---

## 6. API reference

Base path: `/api/v1/assessments`

| Method | Endpoint | Role | Purpose |
| :--- | :--- | :--- | :--- |
| `POST` | `/generate` | Recruiter | Generate and store a validated assessment |
| `GET` | `/` | Recruiter | List assessments created by the caller (admin: all) |
| `GET` | `/{assessment_id}` | Recruiter | Full assessment including answers and hidden tests |
| `GET` | `/{assessment_id}/attempts` | Recruiter | Attempt summaries for an owned assessment |
| `POST` | `/{assessment_id}/start` | Candidate | Start or resume an attempt |
| `POST` | `/attempts/{attempt_id}/submit` | Candidate | Submit answers and receive the result |
| `GET` | `/attempts/{attempt_id}/result` | Candidate / Recruiter / Admin | Read a stored result |

### Generation request example

```json
{
  "job_id": 12,
  "resume_id": 34,
  "mcq_count": 5,
  "coding_count": 1,
  "title": "Backend Engineer Technical Assessment",
  "duration_minutes": 60,
  "passing_score": 60,
  "difficulty": "mixed",
  "additional_instructions": "Focus on REST API design and SQL."
}
```

`resume_id` is optional. When supplied, the resume must belong to a candidate
who applied to the selected job; otherwise the API returns `403`.

### Submission request example

```json
{
  "answers": [
    {"question_id": 101, "selected_option": "A"},
    {"question_id": 102, "selected_option": "C"},
    {"question_id": 103, "answer_text": "def add(a, b):\n    return a + b\n"}
  ]
}
```

- `question_id` must belong to the assessment; foreign questions return `400`.
- Duplicate answers for the same question return `400`.
- MCQ option keys are validated against the stored options.
- Coding questions accept only `answer_text`; MCQ questions accept only
  `selected_option`.

---

## 7. Deterministic scoring

### MCQ

```
question_points = points            if selected_option == correct_answer
                  0                 otherwise (including unanswered)
```

MCQ answers are always evaluated. Unanswered MCQs count as incorrect.

### Coding

```
question_points = points * passed_test_cases / total_test_cases
```

Partial credit is proportional. A coding question is only evaluated when the
sandbox actually runs. If the sandbox is unavailable, the answer is stored with
`is_correct = null`, `points_awarded = 0`, and the question is **excluded from
the denominator** rather than treated as incorrect.

### Overall score

```
score = earned_points / evaluated_points * 100
```

- `mcq_score = mcq_earned / mcq_total * 100` when MCQs exist.
- `coding_score = coding_earned / coding_evaluated_points * 100` only when at
  least one coding answer was actually evaluated by the sandbox.
- If nothing could be evaluated, `score` is `null` — never `0` for missing data.
- The result payload stores `score_formula`, per-question details, limitations
  and `evaluation_complete`.

### Example

Two MCQs worth 1 point each (one correct) and one coding question worth 5 points
with 2 test cases (1 passed):

```
earned_points    = 1 + 2.5 = 3.5
evaluated_points = 1 + 1 + 5 = 7
score            = 3.5 / 7 * 100 = 50.0
mcq_score        = 1 / 2 * 100   = 50.0
coding_score     = 2.5 / 5 * 100 = 50.0
```

---

## 8. Coding sandbox security

`backend/app/services/coding_sandbox.py` **never executes candidate code inside
the FastAPI process**. It writes a harness file to a temporary directory and
asks an external Docker daemon to run it.

Default state is **disabled**:

```env
CODE_EXECUTION_ENABLED=false
CODE_EXECUTION_BACKEND=disabled
```

When disabled, submissions are stored, marked `not_evaluated`, and excluded from
the score denominator. This is intentional: executing untrusted code without a
real sandbox would be unsafe.

### Docker restrictions

When `CODE_EXECUTION_ENABLED=true` and `CODE_EXECUTION_BACKEND=docker`, the
container is started with:

| Flag | Effect |
| :--- | :--- |
| `--network none` | No network access |
| `--read-only` | Read-only root filesystem |
| `--tmpfs /tmp:rw,noexec,nosuid,size=16m` | Small, non-executable temp filesystem |
| `--memory`, `--memory-swap` | Memory cap; swap disabled |
| `--cpus` | CPU cap |
| `--pids-limit` | Fork-bomb protection |
| `--cap-drop ALL` | Drop all Linux capabilities |
| `--security-opt no-new-privileges` | Prevent privilege escalation |
| `--ulimit nofile=64:64` | Limit open file descriptors |
| `--user 65534:65534` | Run as an unprivileged user |
| `--volume ...:ro` | Candidate code mounted read-only |
| host-side `subprocess` timeout | Final backstop against hangs |

The configured image is never pulled automatically (`--pull never`). Pull it in
advance:

```bash
docker pull python:3.12-slim
```

### Sandbox result statuses

| Status | Meaning |
| :--- | :--- |
| `passed` | All test cases passed. |
| `failed` | Some test cases failed. |
| `timeout` | Host-side timeout was exceeded. |
| `error` | Harness or candidate code raised an error. |
| `sandbox_unavailable` | Execution is disabled, Docker is missing, or the daemon/image is unusable. |

### Limitations (read carefully)

1. **Docker socket access is effectively root-equivalent.** Anyone who can talk
   to the Docker daemon can usually escalate to host root. In production, run
   the API with a restricted Docker context or on a dedicated sandbox host, and
   do not expose the socket to the public internet.
2. **The harness runs in the same process as candidate code.** A malicious
   candidate can influence harness output. The sandbox protects the host; it
   does **not** make the candidate's score tamper-proof. Treat coding scores as
   advisory unless the sandbox is hardened further (for example, gVisor or
   Firecracker).
3. **Only Python is supported.** Other languages are rejected during
   validation.
4. **Output is truncated** to `CODE_EXECUTION_MAX_OUTPUT_BYTES` to avoid log
   flooding.
5. **Resource limits are best-effort.** Docker limits reduce risk but are not a
   formal security boundary against kernel exploits.

---

## 9. Authorization and privacy

| Resource | Allowed |
| :--- | :--- |
| Assessment details | Recruiter who created it, or admin |
| Generate assessment | Recruiter who owns the job, or admin |
| Start attempt | Candidate role only |
| Submit attempt | Candidate who owns the attempt |
| Read result | Attempt owner, assessment owner, or admin |
| List attempts | Assessment owner, or admin |

Candidate-facing serializers omit:

- `correct_answer`,
- `explanation`,
- hidden coding test cases (only `hidden: false` samples are returned).

Recruiters receive full questions, correct answers, explanations and all test
cases for review.

---

## 10. Tests

`backend/tests/test_assessments.py` contains **61 tests** using in-memory
SQLite. LLM providers and Docker are always mocked, so the suite is hermetic.

`backend/tests/test_gemini_live.py` adds **2 opt-in live tests** (model
verification and real JSON generation). They are skipped unless
`RUN_LIVE_LLM_TESTS=1` and `GEMINI_API_KEY` are set.

Coverage:

- Gemini SDK request shape, model verification/caching, unsupported and
  retired models, timeout, rate limit, auth failure, HTTP failure, empty and
  blocked responses, candidate-part fallback, and JSON extraction.
- DeepSeek request shape, bearer auth, timeout, HTTP failure, empty choices,
  invalid JSON and provider selection.
- Generation validation: options, duplicate keys, correct answers, test cases,
  unsupported languages, truncation, zero questions.
- Persistence and rollback on invalid LLM output.
- Candidate-safe serialization (no answers or hidden tests).
- Deterministic MCQ scoring, unanswered questions, repeatability.
- Invalid option and foreign-question rejection.
- Coding scoring: full, partial, unavailable sandbox, coding-only assessment.
- Sandbox defaults, Docker flags, harness output parsing.
- Ownership rules for assessments, submissions and results.
- API integration: start, submit, result access, generation errors, conflicts.

Run:

```bash
cd backend
PYTHONPATH=. ./venv/bin/pytest tests/test_assessments.py -q
```

Run the optional live Gemini tests (uses real API quota):

```bash
cd backend
RUN_LIVE_LLM_TESTS=1 PYTHONPATH=. ./venv/bin/pytest tests/test_gemini_live.py -q
```

---

## 11. Migration and runbook

### Verify the selected LLM provider without MySQL

After setting `LLM_PROVIDER` and the matching API key in `backend/.env`, run:

```bash
cd backend
PYTHONPATH=. ./venv/bin/python - <<'PY'
from app.services.llm_client import get_llm_client

client = get_llm_client()
print(type(client).__name__, client.model)
if hasattr(client, "verify_model"):
    client.verify_model()
    print("model supported")
print(client.generate_json('Return only JSON: {"ok": true}'))
PY
```

For Gemini, `verify_model()` checks the configured model through the SDK
before generation. The script then makes one real provider call and prints the
parsed JSON. It does not touch the database.

### Apply migrations

From `backend/`:

```bash
PYTHONPATH=. ./venv/bin/alembic upgrade head
```

This applies the Phase 7 (`7f3c9a1b2d4e`) and Phase 8 (`8b7d4e2f1a90`)
migrations. Confirm the single head with:

```bash
PYTHONPATH=. ./venv/bin/alembic heads
```

Then start the API:

```bash
PYTHONPATH=. ./venv/bin/uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

OpenAPI: `http://127.0.0.1:8000/api/v1/docs`

---

## 12. Known limitations

- Question quality depends on the LLM; recruiter review is required.
- No human review workflow for AI-generated questions is implemented yet.
- No timed auto-submission: `duration_minutes` is stored but not enforced by a
  scheduler.
- One attempt per candidate per assessment; no retakes or reset endpoint yet.
- Coding evaluation is Python-only and disabled by default.
- `submitted` is a reserved attempt status; evaluation is synchronous.
- Passing score is stored but not used to auto-reject or change application
  status.
- No frontend is included in this phase.
