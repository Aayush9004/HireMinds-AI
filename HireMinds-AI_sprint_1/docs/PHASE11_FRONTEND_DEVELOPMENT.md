# HireMinds AI — Phase 11: Complete Frontend Development

## Executive Overview
Phase 11 delivers the complete, production-grade frontend interface for **HireMinds AI**. Built with modern React 19, TypeScript, Vite, Tailwind CSS v4, React Router v7, Axios, and Recharts, it connects directly to the FastAPI backend API (`/api/v1`) without any mocked or simulated production data.

---

## Technical Stack & Architecture

- **Framework**: React 19 + TypeScript (Strict typing enabled)
- **Bundler & Dev Server**: Vite with `@tailwindcss/vite` plugin and `/api` proxy forwarding to `http://127.0.0.1:8000`
- **Routing**: React Router v7 (`BrowserRouter`, `Routes`, `Route`, `Navigate`)
- **State & Context**: `AuthContext` managing JWT token persistence in `localStorage`, user session state, and role claims (`candidate`, `recruiter`, `admin`)
- **Route Guards**:
  - `ProtectedRoute`: Ensures session authentication and redirects unauthenticated users to `/login`.
  - `RoleRoute`: Enforces role-based access control and automatically redirects users accessing unauthorized views to their role-appropriate dashboard.
- **HTTP Client**: Axios with Bearer token injection interceptors, automatic 401 token expiration handling, and unified FastAPI/Pydantic error message parsing.
- **Data Visualization**: Recharts (`BarChart`, `Bar`, `XAxis`, `YAxis`, `Tooltip`, `Cell`) for visual multi-signal readiness comparison.
- **Styling**: Tailwind CSS v4 dark-mode theme (`slate-950`, `slate-900`, `indigo-600`, `violet-500`, `emerald-500`).

---

## Frontend Routes & Interfaces

### 1. Public Pages
| Route | Component | Purpose |
|---|---|---|
| `/` | `LandingPage.tsx` | Hero section, feature highlights, and authentication call-to-actions. |
| `/login` | `LoginPage.tsx` | Authenticate candidate or recruiter, parse JWT token, redirect to role dashboard. |
| `/register` | `RegisterPage.tsx` | Account registration with full name, email, password, and role selection. |
| `/jobs` | `JobBrowsePage.tsx` | Public or authenticated browsing of open active job requisitions. |

### 2. Candidate Portal
| Route | Component | Key Capabilities |
|---|---|---|
| `/candidate/dashboard` | `CandidateDashboard.tsx` | High-level overview: uploaded resumes, active applications, mock interview history, and quick action cards. |
| `/candidate/resumes` | `ResumeManagementPage.tsx` | Drag-and-drop PDF/DOCX resume upload, resume listing, and verification status indicators. |
| `/candidate/resumes/:resumeId` | `ResumeDetailPage.tsx` | Section-by-section breakdown (skills, experience, education, projects), completeness diagnostic, and "Verify / Edit Skills" candidate correction modal. |
| `/candidate/jobs` | `JobBrowsePage.tsx` | Multi-filter search (title, company, skills, location, employment type) with quick ATS alignment checks. |
| `/candidate/jobs/:jobId` | `JobDetailPage.tsx` | Full job posting description, requirements, and interactive modal to apply with existing verified resumes. |
| `/candidate/jobs/:jobId/match` | `MatchAtsDetailPage.tsx` | Multi-signal match fit (TF-IDF lexical overlap, semantic embeddings, skill Venn), component scores (skills, experience, education, projects, semantic), extracted evidence quotes, missing data callouts, and non-rejection transparency notice. |
| `/candidate/assessments/:assessmentId` | `AssessmentRunnerPage.tsx` | Timed technical assessment interface for Multiple Choice (radio selections) and Coding Challenges (code editor with starter templates and test cases), auto-evaluation results review. |
| `/candidate/interviews` | `MockInterviewListPage.tsx` | Past and active AI mock interview sessions, "Start Practice Interview" modal (configurable difficulty, question count 3-10, focus areas). |
| `/candidate/interviews/:sessionId` | `MockInterviewRunnerPage.tsx` | Interactive one-question-at-a-time AI interview, contextual follow-up question generation, immediate rubric scoring (Correctness, Relevance, Clarity, Reasoning, Feedback), and full post-interview diagnostic evaluation report. |
| `/candidate/reports/:jobId/:resumeId` | `CandidateReportPage.tsx` | Comprehensive candidate readiness dossier combining all 5 pillars: resume completeness, ATS fit, matching, assessment performance, mock interview rubric, and actionable study plan. |

### 3. Recruiter Portal
| Route | Component | Key Capabilities |
|---|---|---|
| `/recruiter/dashboard` | `RecruiterDashboard.tsx` | Metrics summary (total jobs, applicants, generated assessments), job pipeline table, and applicant review shortcuts. |
| `/recruiter/jobs` | `JobListPage.tsx` | Requisition management, active/closed toggling, applicant count inspection, and job deletion. |
| `/recruiter/jobs/new` & `/:jobId/edit` | `JobCreateEditPage.tsx` | Requisition creation and editing with interactive skill chip tags, education criteria, and employment parameters. |
| `/recruiter/jobs/:jobId/applicants` | `ApplicantRankingPage.tsx` | Explainable ATS applicant ranking leaderboard (`#1, #2, #3...`), application stage dropdown updates (`applied` to `shortlisted`, `rejected`, etc.), recruiter feedback notes modal, and dossier links. |
| `/recruiter/assessments` | `AssessmentManagementPage.tsx` | Recruiter assessment studio, AI test generation modal specifying duration, MCQ count, coding challenges, difficulty, and passing score. |
| `/recruiter/assessments/:assessmentId` | `AssessmentDetailPage.tsx` | Inspection of assessment questions with correct answer keys, solutions, and candidate attempt submissions. |
| `/recruiter/reports/jobs/:jobId/candidates/:candidateId` | `RecruiterCandidateReportPage.tsx` | Authorized applicant dossier showing verified candidate resume data, ATS explainability breakdown, coding attempt results, and interview rubric evaluations. |

---

## Verification & Compilation Results

- **Frontend Compilation**: `npm run build` completed with **0 errors**:
  ```bash
  vite v8.3.5 building client environment for production...
  ✓ 2636 modules transformed.
  dist/index.html                   0.43 kB │ gzip:   0.29 kB
  dist/assets/index-C7NB1aF-.css   55.35 kB │ gzip:   9.13 kB
  dist/assets/index-BS8-1VUS.js   871.52 kB │ gzip: 246.97 kB
  ✓ built in 799ms
  ```
- **Backend Test Suite**: `venv/bin/pytest tests -k "not test_gemini_live"`
  ```bash
  ================ 184 passed, 2 deselected, 6 warnings in 10.60s ================
  ```
- **Zero Mock Data**: All pages communicate with `/api/v1` backend endpoints.
- **Transparent Decision-Support Disclaimers**: Displayed prominently across ATS scores, mock interview reports, and applicant rankings to maintain ethical AI alignment.
