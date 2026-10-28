import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { RoleRoute } from './components/guards/RoleRoute';

// Common pages
import { LandingPage } from './pages/common/LandingPage';
import { LoginPage } from './pages/common/LoginPage';
import { RegisterPage } from './pages/common/RegisterPage';
import { NotFoundPage } from './pages/common/NotFoundPage';

// Candidate pages
import { CandidateDashboard } from './pages/candidate/CandidateDashboard';
import { ResumeManagementPage } from './pages/candidate/ResumeManagementPage';
import { ResumeDetailPage } from './pages/candidate/ResumeDetailPage';
import { JobBrowsePage } from './pages/candidate/JobBrowsePage';
import { JobDetailPage } from './pages/candidate/JobDetailPage';
import { MatchAtsDetailPage } from './pages/candidate/MatchAtsDetailPage';
import { AssessmentRunnerPage } from './pages/candidate/AssessmentRunnerPage';
import { MockInterviewListPage } from './pages/candidate/MockInterviewListPage';
import { MockInterviewRunnerPage } from './pages/candidate/MockInterviewRunnerPage';
import { CandidateReportPage } from './pages/candidate/CandidateReportPage';

// Recruiter pages
import { RecruiterDashboard } from './pages/recruiter/RecruiterDashboard';
import { JobListPage } from './pages/recruiter/JobListPage';
import { JobCreateEditPage } from './pages/recruiter/JobCreateEditPage';
import { ApplicantRankingPage } from './pages/recruiter/ApplicantRankingPage';
import { AssessmentManagementPage } from './pages/recruiter/AssessmentManagementPage';
import { AssessmentDetailPage } from './pages/recruiter/AssessmentDetailPage';
import { RecruiterCandidateReportPage } from './pages/recruiter/RecruiterCandidateReportPage';

export function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          {/* Public Routes */}
          <Route path="/" element={<LandingPage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route path="/jobs" element={<JobBrowsePage />} />
          <Route path="/jobs/:jobId" element={<JobDetailPage />} />

          {/* Candidate Protected Routes */}
          <Route
            path="/candidate/dashboard"
            element={
              <RoleRoute allowedRoles={['candidate', 'admin']}>
                <CandidateDashboard />
              </RoleRoute>
            }
          />
          <Route
            path="/candidate/resumes"
            element={
              <RoleRoute allowedRoles={['candidate', 'admin']}>
                <ResumeManagementPage />
              </RoleRoute>
            }
          />
          <Route
            path="/candidate/resumes/:resumeId"
            element={
              <RoleRoute allowedRoles={['candidate', 'admin']}>
                <ResumeDetailPage />
              </RoleRoute>
            }
          />
          <Route
            path="/candidate/jobs"
            element={
              <RoleRoute allowedRoles={['candidate', 'recruiter', 'admin']}>
                <JobBrowsePage />
              </RoleRoute>
            }
          />
          <Route
            path="/candidate/jobs/:jobId"
            element={
              <RoleRoute allowedRoles={['candidate', 'recruiter', 'admin']}>
                <JobDetailPage />
              </RoleRoute>
            }
          />
          <Route
            path="/candidate/jobs/:jobId/match"
            element={
              <RoleRoute allowedRoles={['candidate', 'admin']}>
                <MatchAtsDetailPage />
              </RoleRoute>
            }
          />
          <Route
            path="/candidate/assessments/:assessmentId"
            element={
              <RoleRoute allowedRoles={['candidate', 'admin']}>
                <AssessmentRunnerPage />
              </RoleRoute>
            }
          />
          <Route
            path="/candidate/interviews"
            element={
              <RoleRoute allowedRoles={['candidate', 'admin']}>
                <MockInterviewListPage />
              </RoleRoute>
            }
          />
          <Route
            path="/candidate/interviews/:sessionId"
            element={
              <RoleRoute allowedRoles={['candidate', 'admin']}>
                <MockInterviewRunnerPage />
              </RoleRoute>
            }
          />
          <Route
            path="/candidate/reports/:jobId/:resumeId"
            element={
              <RoleRoute allowedRoles={['candidate', 'admin']}>
                <CandidateReportPage />
              </RoleRoute>
            }
          />

          {/* Recruiter Protected Routes */}
          <Route
            path="/recruiter/dashboard"
            element={
              <RoleRoute allowedRoles={['recruiter', 'admin']}>
                <RecruiterDashboard />
              </RoleRoute>
            }
          />
          <Route
            path="/recruiter/jobs"
            element={
              <RoleRoute allowedRoles={['recruiter', 'admin']}>
                <JobListPage />
              </RoleRoute>
            }
          />
          <Route
            path="/recruiter/jobs/new"
            element={
              <RoleRoute allowedRoles={['recruiter', 'admin']}>
                <JobCreateEditPage />
              </RoleRoute>
            }
          />
          <Route
            path="/recruiter/jobs/create"
            element={
              <RoleRoute allowedRoles={['recruiter', 'admin']}>
                <JobCreateEditPage />
              </RoleRoute>
            }
          />
          <Route
            path="/recruiter/jobs/:jobId/edit"
            element={
              <RoleRoute allowedRoles={['recruiter', 'admin']}>
                <JobCreateEditPage />
              </RoleRoute>
            }
          />
          <Route
            path="/recruiter/jobs/:jobId/applicants"
            element={
              <RoleRoute allowedRoles={['recruiter', 'admin']}>
                <ApplicantRankingPage />
              </RoleRoute>
            }
          />
          <Route
            path="/recruiter/assessments"
            element={
              <RoleRoute allowedRoles={['recruiter', 'admin']}>
                <AssessmentManagementPage />
              </RoleRoute>
            }
          />
          <Route
            path="/recruiter/assessments/:assessmentId"
            element={
              <RoleRoute allowedRoles={['recruiter', 'admin']}>
                <AssessmentDetailPage />
              </RoleRoute>
            }
          />
          <Route
            path="/recruiter/reports/jobs/:jobId/candidates/:candidateId"
            element={
              <RoleRoute allowedRoles={['recruiter', 'admin']}>
                <RecruiterCandidateReportPage />
              </RoleRoute>
            }
          />

          {/* Fallback 404 Route */}
          <Route path="*" element={<NotFoundPage />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}

export default App;
