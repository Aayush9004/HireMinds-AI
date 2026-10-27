# HireMinds AI — AI-Powered Recruitment & Candidate Assessment Platform

> **B.Tech Major Project** | Modular Monolithic Architecture | Backend-First Development

---

## 1. Project Overview

**HireMinds AI** is an intelligent candidate evaluation and recruitment decision-support system. It is designed to:
- Help candidates understand how their resumes align with job descriptions.
- Extract skills, experience, and educational qualifications transparently using NLP and rule-based pipelines.
- Match candidates with jobs using both **TF-IDF** (lexical baseline) and **Sentence Transformers** (semantic similarity).
- Calculate ATS scores via a transparent, multi-factor weighted scoring rubric.
- Deliver personalized technical assessments and AI-driven mock interviews using **Google Gemini**.
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
│   │   │       │   └── health.py
│   │   │       └── api.py    # Router Aggregator
│   │   ├── core/             # Configuration & Security
│   │   │   └── config.py     # Pydantic Settings & CORS
│   │   ├── models/           # SQLAlchemy DB Models (Phase 2+)
│   │   ├── schemas/          # Pydantic Request/Response DTOs
│   │   │   └── health.py
│   │   ├── services/         # Business Logic, ML, NLP & LLM Services (Phases 4-9)
│   │   └── main.py           # FastAPI entrypoint, middleware, routes
│   ├── tests/                # Pytest unit & integration test suites
│   │   └── test_health.py
│   ├── requirements.txt      # Phase-specific pinned dependencies
│   ├── .env.example          # Template environment file
│   └── venv/                 # Isolated Python 3.13 virtual environment
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
| Phase 6 | Matching Algorithms: TF-IDF vs Sentence Transformers Comparison | Upcoming |
| Phase 7 | ATS Multi-Factor Weighted Scoring & Explainable Candidate Ranking | Upcoming |
| Phase 8 | Personalized Technical Assessments & MCQ / Code Evaluation | Upcoming |
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

3. Set `PYTHONPATH` and launch the development server with hot-reload:
   ```powershell
   $env:PYTHONPATH=".\backend"
   .\backend\venv\Scripts\uvicorn.exe app.main:app --reload --host 127.0.0.1 --port 8000
   ```

4. Access the backend endpoints:
   - **Health Check API**: [http://127.0.0.1:8000/api/v1/health](http://127.0.0.1:8000/api/v1/health)
   - **Interactive Swagger Documentation**: [http://127.0.0.1:8000/api/v1/docs](http://127.0.0.1:8000/api/v1/docs)
   - **ReDoc Documentation**: [http://127.0.0.1:8000/api/v1/redoc](http://127.0.0.1:8000/api/v1/redoc)

### B. Running Backend Tests (Pytest)

Run the test suite from the project root:
```powershell
$env:PYTHONPATH=".\backend"
.\backend\venv\Scripts\pytest .\backend\tests -v
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
