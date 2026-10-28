import React, { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { AppLayout } from '../../components/layout/AppLayout';
import { Card, CardHeader } from '../../components/ui/Card';
import { Button } from '../../components/ui/Button';
import { Badge } from '../../components/ui/Badge';
import { Input } from '../../components/ui/Input';
import { Alert } from '../../components/ui/Alert';
import { LoadingSpinner } from '../../components/ui/LoadingSpinner';
import { EmptyState } from '../../components/ui/EmptyState';
import { jobService } from '../../services/jobService';
import { Job } from '../../types';
import { getErrorMessage } from '../../services/api';
import {
  Briefcase,
  Plus,
  Search,
  Users,
  Edit,
  Trash2,
  MapPin,
  Clock,
  Sparkles,
  ToggleLeft,
  ToggleRight,
} from 'lucide-react';

export const JobListPage: React.FC = () => {
  const navigate = useNavigate();

  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState<'all' | 'active' | 'closed'>('all');

  useEffect(() => {
    loadJobs();
  }, []);

  const loadJobs = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await jobService.getMyJobs();
      setJobs(data);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  const handleToggleActive = async (job: Job) => {
    try {
      const updated = await jobService.updateJob(job.id, {
        is_active: !job.is_active,
      });
      setJobs((prev) => prev.map((j) => (j.id === job.id ? updated : j)));
    } catch (err) {
      setError(getErrorMessage(err));
    }
  };

  const handleDeleteJob = async (jobId: number) => {
    if (!window.confirm('Are you sure you want to delete this job posting? This action cannot be undone.')) {
      return;
    }

    try {
      await jobService.deleteJob(jobId);
      setJobs((prev) => prev.filter((j) => j.id !== jobId));
    } catch (err) {
      setError(getErrorMessage(err));
    }
  };

  const filteredJobs = jobs.filter((j) => {
    const matchesSearch =
      !searchTerm ||
      j.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
      j.company_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      j.location.toLowerCase().includes(searchTerm.toLowerCase());

    const matchesStatus =
      statusFilter === 'all' ||
      (statusFilter === 'active' && j.is_active) ||
      (statusFilter === 'closed' && !j.is_active);

    return matchesSearch && matchesStatus;
  });

  return (
    <AppLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-white flex items-center gap-2.5">
              <Briefcase className="w-6 h-6 text-indigo-400" />
              Job Postings Management
            </h1>
            <p className="text-sm text-slate-400 mt-1">
              Create and oversee your open requisitions, view ATS candidate rankings, and update job criteria.
            </p>
          </div>

          <Button
            variant="primary"
            onClick={() => navigate('/recruiter/jobs/new')}
            leftIcon={<Plus className="w-4 h-4" />}
          >
            Create New Job
          </Button>
        </div>

        {error && (
          <Alert variant="danger" onClose={() => setError(null)}>
            {error}
          </Alert>
        )}

        {/* Filter & Search Bar */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 flex flex-col sm:flex-row gap-3 items-center justify-between">
          <div className="w-full sm:w-80">
            <Input
              placeholder="Search by title or location..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              leftIcon={<Search className="w-4 h-4 text-slate-400" />}
            />
          </div>

          <div className="flex items-center gap-2 w-full sm:w-auto">
            <span className="text-xs text-slate-400">Filter:</span>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value as any)}
              className="bg-slate-950 border border-slate-800 rounded-lg px-3 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-indigo-500"
            >
              <option value="all">All Jobs ({jobs.length})</option>
              <option value="active">Active Only ({jobs.filter((j) => j.is_active).length})</option>
              <option value="closed">Closed Only ({jobs.filter((j) => !j.is_active).length})</option>
            </select>
          </div>
        </div>

        {/* Jobs List */}
        {loading ? (
          <LoadingSpinner label="Loading your job postings..." />
        ) : filteredJobs.length === 0 ? (
          <EmptyState
            icon={Briefcase}
            title="No job postings found"
            description={
              searchTerm || statusFilter !== 'all'
                ? 'Try adjusting your search criteria.'
                : 'You have not posted any jobs yet. Create one to begin sourcing candidates.'
            }
            action={
              searchTerm || statusFilter !== 'all' ? (
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => {
                    setSearchTerm('');
                    setStatusFilter('all');
                  }}
                >
                  Clear Filters
                </Button>
              ) : (
                <Button
                  variant="primary"
                  onClick={() => navigate('/recruiter/jobs/new')}
                  leftIcon={<Plus className="w-4 h-4" />}
                >
                  Post Your First Job
                </Button>
              )
            }
          />
        ) : (
          <div className="space-y-3">
            {filteredJobs.map((job) => (
              <Card
                key={job.id}
                className="hover:border-slate-700 transition-colors flex flex-col md:flex-row md:items-center justify-between gap-4"
              >
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <h3 className="text-base font-bold text-white hover:text-indigo-400 transition-colors">
                      <Link to={`/recruiter/jobs/${job.id}/applicants`}>{job.title}</Link>
                    </h3>
                    <Badge variant={job.is_active ? 'success' : 'neutral'}>
                      {job.is_active ? 'Active' : 'Closed'}
                    </Badge>
                    <Badge variant="cyan">{job.job_type}</Badge>
                  </div>

                  <div className="flex flex-wrap items-center gap-3 text-xs text-slate-400">
                    <span className="text-slate-300 font-medium">{job.company_name}</span>
                    <span>•</span>
                    <span className="flex items-center gap-1">
                      <MapPin className="w-3 h-3 text-slate-500" />
                      {job.location}
                    </span>
                    <span>•</span>
                    <span>
                      {job.min_experience_years === 0
                        ? 'Entry Level'
                        : `${job.min_experience_years}+ yrs exp`}
                    </span>
                    <span>•</span>
                    <span>Posted {new Date(job.created_at).toLocaleDateString()}</span>
                  </div>

                  <div className="flex flex-wrap gap-1 mt-2">
                    {job.required_skills.slice(0, 4).map((s, idx) => (
                      <span
                        key={idx}
                        className="px-2 py-0.5 rounded text-[10px] bg-slate-800 text-slate-300 border border-slate-700"
                      >
                        {s}
                      </span>
                    ))}
                    {job.required_skills.length > 4 && (
                      <span className="px-1.5 py-0.5 rounded text-[10px] bg-slate-900 text-slate-400">
                        +{job.required_skills.length - 4}
                      </span>
                    )}
                  </div>
                </div>

                {/* Right side actions */}
                <div className="flex items-center gap-2 shrink-0 pt-3 md:pt-0 border-t md:border-t-0 border-slate-800">
                  <Button
                    variant="primary"
                    size="sm"
                    onClick={() => navigate(`/recruiter/jobs/${job.id}/applicants`)}
                    leftIcon={<Users className="w-4 h-4" />}
                  >
                    Applicants ({job.application_count ?? 0})
                  </Button>

                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() => handleToggleActive(job)}
                    title={job.is_active ? 'Close job' : 'Reactivate job'}
                  >
                    {job.is_active ? (
                      <ToggleRight className="w-4 h-4 text-emerald-400" />
                    ) : (
                      <ToggleLeft className="w-4 h-4 text-slate-500" />
                    )}
                  </Button>

                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() => navigate(`/recruiter/jobs/${job.id}/edit`)}
                    title="Edit job"
                  >
                    <Edit className="w-4 h-4 text-slate-300" />
                  </Button>

                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleDeleteJob(job.id)}
                    className="text-slate-400 hover:text-rose-400"
                    title="Delete job"
                  >
                    <Trash2 className="w-4 h-4" />
                  </Button>
                </div>
              </Card>
            ))}
          </div>
        )}
      </div>
    </AppLayout>
  );
};
