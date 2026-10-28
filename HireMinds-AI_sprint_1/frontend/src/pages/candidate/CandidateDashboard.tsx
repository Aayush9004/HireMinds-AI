import React, { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { AppLayout } from '../../components/layout/AppLayout';
import { StatCard } from '../../components/ui/StatCard';
import { Card, CardHeader } from '../../components/ui/Card';
import { Badge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';
import { Alert } from '../../components/ui/Alert';
import { LoadingSpinner } from '../../components/ui/LoadingSpinner';
import { EmptyState } from '../../components/ui/EmptyState';
import { resumeService } from '../../services/resumeService';
import { jobService } from '../../services/jobService';
import { interviewService } from '../../services/interviewService';
import { Job, JobApplication, Resume, InterviewSession } from '../../types';
import {
  FileText,
  Briefcase,
  Sparkles,
  ArrowRight,
  Upload,
  Layers,
  Clock,
  CheckCircle2,
} from 'lucide-react';
import { getErrorMessage } from '../../services/api';

export const CandidateDashboard: React.FC = () => {
  const { user } = useAuth();
  const navigate = useNavigate();

  const [resumes, setResumes] = useState<Resume[]>([]);
  const [applications, setApplications] = useState<JobApplication[]>([]);
  const [interviews, setInterviews] = useState<InterviewSession[]>([]);
  const [availableJobs, setAvailableJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchDashboardData = async () => {
      setLoading(true);
      setError(null);
      try {
        const [resumesData, appsData, interviewsData, jobsData] = await Promise.all([
          resumeService.getMyResumes(),
          jobService.getMyApplications(),
          interviewService.getSessions(),
          jobService.getJobs(),
        ]);
        setResumes(resumesData);
        setApplications(appsData);
        setInterviews(interviewsData.items || []);
        setAvailableJobs(jobsData);
      } catch (err) {
        setError(getErrorMessage(err));
      } finally {
        setLoading(false);
      }
    };

    fetchDashboardData();
  }, []);

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'accepted':
      case 'shortlisted':
        return <Badge variant="success">{status.replace('_', ' ')}</Badge>;
      case 'rejected':
        return <Badge variant="danger">{status}</Badge>;
      case 'under_review':
      case 'interview_scheduled':
        return <Badge variant="primary">{status.replace('_', ' ')}</Badge>;
      default:
        return <Badge variant="neutral">{status.replace('_', ' ')}</Badge>;
    }
  };

  if (loading) {
    return (
      <AppLayout>
        <LoadingSpinner fullPage label="Loading candidate dashboard..." />
      </AppLayout>
    );
  }

  return (
    <AppLayout>
      {/* Welcome Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-8">
        <div>
          <h1 className="text-2xl font-bold text-white">
            Hello, {user?.full_name || 'Candidate'} 👋
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Track your resumes, applications, ATS alignments, and AI mock interview progress.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Button
            variant="secondary"
            size="sm"
            onClick={() => navigate('/candidate/jobs')}
            leftIcon={<Briefcase className="w-3.5 h-3.5" />}
          >
            Find Jobs
          </Button>
          <Button
            variant="primary"
            size="sm"
            onClick={() => navigate('/candidate/resumes')}
            leftIcon={<Upload className="w-3.5 h-3.5" />}
          >
            Upload Resume
          </Button>
        </div>
      </div>

      {error && (
        <Alert type="error" className="mb-6" onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {/* Stat Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <StatCard
          title="Uploaded Resumes"
          value={resumes.length}
          subtitle={resumes.length ? 'Primary resume active' : 'None uploaded yet'}
          icon={<FileText className="w-5 h-5" />}
          onClick={() => navigate('/candidate/resumes')}
        />
        <StatCard
          title="Job Applications"
          value={applications.length}
          subtitle="Submitted applications"
          icon={<Briefcase className="w-5 h-5" />}
          onClick={() => navigate('/candidate/jobs')}
        />
        <StatCard
          title="Mock Interviews"
          value={interviews.length}
          subtitle={
            interviews.filter((i) => i.status === 'completed').length + ' completed'
          }
          icon={<Sparkles className="w-5 h-5 text-violet-400" />}
          onClick={() => navigate('/candidate/interviews')}
        />
        <StatCard
          title="Active Openings"
          value={availableJobs.length}
          subtitle="Ready for matching"
          icon={<Layers className="w-5 h-5 text-cyan-400" />}
          onClick={() => navigate('/candidate/jobs')}
        />
      </div>

      {/* Main Sections */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left 2 Cols: Recent Applications */}
        <div className="lg:col-span-2 space-y-6">
          <Card>
            <CardHeader
              title="My Job Applications"
              subtitle="Current status of your candidate submissions"
              action={
                <Link
                  to="/candidate/jobs"
                  className="text-xs text-indigo-400 hover:text-indigo-300 font-medium flex items-center gap-1"
                >
                  Browse more <ArrowRight className="w-3 h-3" />
                </Link>
              }
            />

            {applications.length === 0 ? (
              <EmptyState
                icon={<Briefcase className="w-6 h-6" />}
                title="No applications yet"
                description="Browse available job vacancies and apply with your parsed resume to track matching and ATS scores."
                actionText="Explore Jobs"
                onAction={() => navigate('/candidate/jobs')}
              />
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs text-slate-300">
                  <thead className="text-[11px] uppercase tracking-wider text-slate-500 border-b border-slate-800">
                    <tr>
                      <th className="py-2.5 px-3">Position</th>
                      <th className="py-2.5 px-3">Company</th>
                      <th className="py-2.5 px-3">Applied</th>
                      <th className="py-2.5 px-3">Status</th>
                      <th className="py-2.5 px-3 text-right">Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60">
                    {applications.slice(0, 5).map((app) => (
                      <tr key={app.id} className="hover:bg-slate-850/40 transition-colors">
                        <td className="py-3 px-3 font-medium text-slate-200">
                          {app.job?.title || `Job #${app.job_id}`}
                        </td>
                        <td className="py-3 px-3 text-slate-400">
                          {app.job?.company_name || 'Company'}
                        </td>
                        <td className="py-3 px-3 text-slate-400">
                          {new Date(app.created_at).toLocaleDateString()}
                        </td>
                        <td className="py-3 px-3">{getStatusBadge(app.status)}</td>
                        <td className="py-3 px-3 text-right">
                          <Link
                            to={`/candidate/reports/${app.job_id}/${app.resume_id}`}
                            className="text-indigo-400 hover:text-indigo-300 font-medium"
                          >
                            View Report
                          </Link>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Card>

          {/* Quick Match & Mock Interview Callout */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="p-5 rounded-xl border border-indigo-500/20 bg-gradient-to-br from-indigo-950/30 to-slate-900 flex flex-col justify-between">
              <div>
                <Badge variant="purple" size="sm" className="mb-2">
                  Explainable ATS
                </Badge>
                <h4 className="text-sm font-semibold text-white mb-1">
                  Evaluate Job Fit & ATS Scores
                </h4>
                <p className="text-xs text-slate-400 leading-relaxed">
                  Compare your resume against any job using TF-IDF lexical and Sentence Transformer
                  semantic similarity with full rationale and evidence.
                </p>
              </div>
              <div className="mt-4">
                <Button
                  size="sm"
                  variant="primary"
                  onClick={() => navigate('/candidate/jobs')}
                  rightIcon={<ArrowRight className="w-3.5 h-3.5" />}
                >
                  Test Fit Against a Job
                </Button>
              </div>
            </div>

            <div className="p-5 rounded-xl border border-violet-500/20 bg-gradient-to-br from-violet-950/30 to-slate-900 flex flex-col justify-between">
              <div>
                <Badge variant="cyan" size="sm" className="mb-2">
                  Gemini Powered
                </Badge>
                <h4 className="text-sm font-semibold text-white mb-1">
                  AI Technical Mock Interviews
                </h4>
                <p className="text-xs text-slate-400 leading-relaxed">
                  Practice role-specific interview questions one-at-a-time with adaptive follow-ups
                  and objective 4-dimension rubric scoring.
                </p>
              </div>
              <div className="mt-4">
                <Button
                  size="sm"
                  variant="secondary"
                  onClick={() => navigate('/candidate/interviews')}
                  rightIcon={<Sparkles className="w-3.5 h-3.5" />}
                >
                  Start Practice Session
                </Button>
              </div>
            </div>
          </div>
        </div>

        {/* Right 1 Col: Resume Status & Recent Mock Interviews */}
        <div className="space-y-6">
          {/* Active Resumes Card */}
          <Card>
            <CardHeader
              title="My Resumes"
              subtitle={`${resumes.length} uploaded`}
              action={
                <Link
                  to="/candidate/resumes"
                  className="text-xs text-indigo-400 hover:text-indigo-300 font-medium"
                >
                  Manage
                </Link>
              }
            />

            {resumes.length === 0 ? (
              <EmptyState
                icon={<FileText className="w-5 h-5" />}
                title="No resume uploaded"
                description="Upload a PDF resume to enable skill extraction and matching."
                actionText="Upload PDF"
                onAction={() => navigate('/candidate/resumes')}
              />
            ) : (
              <div className="space-y-3">
                {resumes.slice(0, 3).map((r) => (
                  <div
                    key={r.id}
                    onClick={() => navigate(`/candidate/resumes/${r.id}`)}
                    className="p-3 rounded-lg border border-slate-800 bg-slate-950/40 hover:border-slate-700 transition-colors cursor-pointer"
                  >
                    <div className="flex items-center justify-between mb-1.5">
                      <span className="text-xs font-semibold text-slate-200 truncate max-w-[180px]">
                        {r.filename}
                      </span>
                      {r.is_reviewed_by_candidate ? (
                        <Badge size="sm" variant="success">
                          Verified
                        </Badge>
                      ) : (
                        <Badge size="sm" variant="warning">
                          Unreviewed
                        </Badge>
                      )}
                    </div>
                    <div className="flex items-center gap-2 text-[11px] text-slate-400">
                      <span>{r.extracted_skills?.length || 0} skills extracted</span>
                      <span>•</span>
                      <span>{new Date(r.created_at).toLocaleDateString()}</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Card>

          {/* Recent Mock Interviews */}
          <Card>
            <CardHeader
              title="Recent Mock Interviews"
              subtitle="Adaptive practice transcripts"
              action={
                <Link
                  to="/candidate/interviews"
                  className="text-xs text-indigo-400 hover:text-indigo-300 font-medium"
                >
                  All
                </Link>
              }
            />

            {interviews.length === 0 ? (
              <div className="text-center py-6 text-xs text-slate-500">
                No mock interviews yet. Start one to practice role-specific technical questions.
              </div>
            ) : (
              <div className="space-y-2.5">
                {interviews.slice(0, 3).map((s) => (
                  <div
                    key={s.id}
                    onClick={() => navigate(`/candidate/interviews/${s.id}`)}
                    className="p-3 rounded-lg border border-slate-800 bg-slate-950/40 hover:border-slate-700 transition-colors cursor-pointer flex items-center justify-between"
                  >
                    <div>
                      <p className="text-xs font-medium text-slate-200 truncate max-w-[160px]">
                        {s.title}
                      </p>
                      <p className="text-[11px] text-slate-400 mt-0.5">
                        {s.status === 'completed'
                          ? `Score: ${s.evaluation?.overall_score || 0}%`
                          : 'In progress'}
                      </p>
                    </div>
                    <Badge size="sm" variant={s.status === 'completed' ? 'success' : 'purple'}>
                      {s.status}
                    </Badge>
                  </div>
                ))}
              </div>
            )}
          </Card>
        </div>
      </div>
    </AppLayout>
  );
};
