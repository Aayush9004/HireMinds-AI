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
import { jobService } from '../../services/jobService';
import { assessmentService } from '../../services/assessmentService';
import { Job, Assessment } from '../../types';
import { getErrorMessage } from '../../services/api';
import {
  Briefcase,
  Users,
  Layers,
  Plus,
  ArrowRight,
  TrendingUp,
  MapPin,
  Clock,
  Sparkles,
} from 'lucide-react';

export const RecruiterDashboard: React.FC = () => {
  const { user } = useAuth();
  const navigate = useNavigate();

  const [jobs, setJobs] = useState<Job[]>([]);
  const [assessments, setAssessments] = useState<Assessment[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const fetchDashboardData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [jobsData, assessmentsData] = await Promise.all([
        jobService.getMyJobs(),
        assessmentService.getMyAssessments().catch(() => ({ items: [], total: 0 })),
      ]);
      setJobs(jobsData);
      setAssessments(assessmentsData.items || []);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  const activeJobs = jobs.filter((j) => j.is_active);
  const totalApplicants = jobs.reduce((sum, j) => sum + (j.application_count || 0), 0);

  if (loading) {
    return (
      <AppLayout>
        <LoadingSpinner fullPage label="Loading recruiter portal..." />
      </AppLayout>
    );
  }

  return (
    <AppLayout>
      <div className="space-y-6">
        {/* Welcome Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-white">
              Recruiter Command Center 🎯
            </h1>
            <p className="text-xs text-slate-400 mt-1">
              Welcome back, {user?.full_name}. Manage openings, rank applicants with explainable ATS, and inspect AI assessments.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <Button
              variant="secondary"
              size="sm"
              onClick={() => navigate('/recruiter/assessments')}
              leftIcon={<Layers className="w-4 h-4 text-indigo-400" />}
            >
              Assessments
            </Button>
            <Button
              variant="primary"
              size="sm"
              onClick={() => navigate('/recruiter/jobs/new')}
              leftIcon={<Plus className="w-4 h-4" />}
            >
              Post New Position
            </Button>
          </div>
        </div>

        {error && (
          <Alert variant="danger" onClose={() => setError(null)}>
            {error}
          </Alert>
        )}

        {/* Key Metrics */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard
            title="Total Job Postings"
            value={jobs.length}
            icon={Briefcase}
            description={`${activeJobs.length} active positions`}
          />
          <StatCard
            title="Total Applicants"
            value={totalApplicants}
            icon={Users}
            description="Across all published positions"
          />
          <StatCard
            title="AI Technical Assessments"
            value={assessments.length}
            icon={Layers}
            description="Generated job tests"
          />
          <StatCard
            title="ATS Explainability"
            value="100%"
            icon={Sparkles}
            description="Transparent multi-signal ranking"
          />
        </div>

        {/* Jobs Overview */}
        <Card>
          <CardHeader
            title="Your Job Postings & Candidate Pipelines"
            subtitle="Click on any position to view ranked candidates and update hiring stages"
            action={
              <Button
                variant="ghost"
                size="sm"
                onClick={() => navigate('/recruiter/jobs')}
                rightIcon={<ArrowRight className="w-3.5 h-3.5" />}
              >
                Manage All Jobs
              </Button>
            }
          />

          {jobs.length === 0 ? (
            <EmptyState
              icon={Briefcase}
              title="No jobs published yet"
              description="Post your first job opening to start receiving and ranking candidates."
              action={
                <Button
                  variant="primary"
                  onClick={() => navigate('/recruiter/jobs/new')}
                  leftIcon={<Plus className="w-4 h-4" />}
                >
                  Create First Job
                </Button>
              }
            />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="border-b border-slate-800 text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                    <th className="py-3 px-3">Position Title</th>
                    <th className="py-3 px-3">Location & Type</th>
                    <th className="py-3 px-3">Applicants</th>
                    <th className="py-3 px-3">Status</th>
                    <th className="py-3 px-3 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60 text-xs">
                  {jobs.slice(0, 5).map((job) => (
                    <tr key={job.id} className="hover:bg-slate-800/40 transition-colors">
                      <td className="py-3 px-3 font-medium text-slate-100">
                        <Link
                          to={`/recruiter/jobs/${job.id}/applicants`}
                          className="hover:text-indigo-400 transition-colors"
                        >
                          {job.title}
                        </Link>
                        <div className="text-[11px] text-slate-400 mt-0.5">
                          {job.company_name}
                        </div>
                      </td>
                      <td className="py-3 px-3 text-slate-300">
                        <div className="flex items-center gap-1.5">
                          <MapPin className="w-3 h-3 text-slate-500" />
                          <span>{job.location}</span>
                        </div>
                        <div className="text-[10px] text-slate-500 capitalize mt-0.5">
                          {job.job_type}
                        </div>
                      </td>
                      <td className="py-3 px-3 text-slate-200">
                        <span className="font-semibold text-indigo-300">
                          {job.application_count ?? 0}
                        </span>{' '}
                        candidates
                      </td>
                      <td className="py-3 px-3">
                        <Badge variant={job.is_active ? 'success' : 'neutral'}>
                          {job.is_active ? 'Active' : 'Closed'}
                        </Badge>
                      </td>
                      <td className="py-3 px-3 text-right">
                        <Button
                          variant="secondary"
                          size="sm"
                          onClick={() => navigate(`/recruiter/jobs/${job.id}/applicants`)}
                          rightIcon={<Users className="w-3.5 h-3.5" />}
                        >
                          View Ranked Applicants
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      </div>
    </AppLayout>
  );
};
