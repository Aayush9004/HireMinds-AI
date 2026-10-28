import React, { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { AppLayout } from '../../components/layout/AppLayout';
import { Card } from '../../components/ui/Card';
import { Button } from '../../components/ui/Button';
import { Badge } from '../../components/ui/Badge';
import { Input } from '../../components/ui/Input';
import { LoadingSpinner } from '../../components/ui/LoadingSpinner';
import { EmptyState } from '../../components/ui/EmptyState';
import { Alert } from '../../components/ui/Alert';
import { jobService } from '../../services/jobService';
import { resumeService } from '../../services/resumeService';
import { Job, Resume } from '../../types';
import { getErrorMessage } from '../../services/api';
import {
  Briefcase,
  Search,
  MapPin,
  Clock,
  Sparkles,
  ArrowRight,
  GraduationCap,
  SlidersHorizontal,
  Building,
} from 'lucide-react';

export const JobBrowsePage: React.FC = () => {
  const navigate = useNavigate();
  const { isAuthenticated, isCandidate } = useAuth();
  const [jobs, setJobs] = useState<Job[]>([]);
  const [resumes, setResumes] = useState<Resume[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedType, setSelectedType] = useState<string>('all');
  const [selectedLocation, setSelectedLocation] = useState<string>('');

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [jobsData, resumesData] = await Promise.all([
        jobService.getJobs(),
        resumeService.getMyResumes().catch(() => []),
      ]);
      setJobs(Array.isArray(jobsData) ? jobsData : []);
      setResumes(Array.isArray(resumesData) ? resumesData : []);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  const filteredJobs = jobs.filter((job) => {
    if (!job || !job.is_active) return false;
    const title = (job.title || '').toLowerCase();
    const company = (job.company_name || '').toLowerCase();
    const desc = (job.description || '').toLowerCase();
    const skills = Array.isArray(job.required_skills) ? job.required_skills : [];
    const jobType = (job.job_type || '').toLowerCase();
    const location = (job.location || '').toLowerCase();
    const sTerm = (searchTerm || '').trim().toLowerCase();

    const matchesSearch =
      !sTerm ||
      title.includes(sTerm) ||
      company.includes(sTerm) ||
      desc.includes(sTerm) ||
      skills.some((s) => (s || '').toLowerCase().includes(sTerm));

    const matchesType =
      selectedType === 'all' ||
      jobType.includes(selectedType.toLowerCase());

    const matchesLocation =
      !selectedLocation ||
      location.includes(selectedLocation.toLowerCase());

    return matchesSearch && matchesType && matchesLocation;
  });

  const hasResume = resumes.length > 0;

  return (
    <AppLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-white flex items-center gap-2.5">
              <Briefcase className="w-6 h-6 text-indigo-400" />
              Explore Open Positions
            </h1>
            <p className="text-sm text-slate-400 mt-1">
              Find positions matching your skills, test ATS alignment, and practice tailored AI interviews.
            </p>
          </div>

          {!hasResume && (
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => navigate(isAuthenticated ? '/candidate/resumes' : '/login')}
                leftIcon={<Sparkles className="w-4 h-4 text-indigo-400" />}
              >
                {isAuthenticated ? 'Upload Resume for ATS Matching' : 'Sign In to Match Resumes'}
              </Button>
            </div>
          )}
        </div>

        {error && (
          <Alert variant="danger" title="Failed to load jobs" onClose={() => setError(null)}>
            {error}
          </Alert>
        )}

        {/* Search & Filter Bar */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 shadow-sm space-y-3">
          <div className="grid grid-cols-1 md:grid-cols-12 gap-3">
            <div className="md:col-span-6">
              <Input
                placeholder="Search by job title, company, or skill (e.g. Python, React)..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                leftIcon={<Search className="w-4 h-4 text-slate-400" />}
              />
            </div>
            <div className="md:col-span-3">
              <Input
                placeholder="Location (e.g. Remote, NY)..."
                value={selectedLocation}
                onChange={(e) => setSelectedLocation(e.target.value)}
                leftIcon={<MapPin className="w-4 h-4 text-slate-400" />}
              />
            </div>
            <div className="md:col-span-3">
              <select
                value={selectedType}
                onChange={(e) => setSelectedType(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-indigo-500"
              >
                <option value="all">All Employment Types</option>
                <option value="full-time">Full-time</option>
                <option value="part-time">Part-time</option>
                <option value="contract">Contract</option>
                <option value="remote">Remote</option>
                <option value="internship">Internship</option>
              </select>
            </div>
          </div>

          <div className="flex items-center justify-between text-xs text-slate-400 pt-1">
            <span>
              Showing <strong className="text-slate-200">{filteredJobs.length}</strong> active positions
            </span>
            {(searchTerm || selectedType !== 'all' || selectedLocation) && (
              <button
                onClick={() => {
                  setSearchTerm('');
                  setSelectedType('all');
                  setSelectedLocation('');
                }}
                className="text-indigo-400 hover:text-indigo-300 font-medium cursor-pointer"
              >
                Reset Filters
              </button>
            )}
          </div>
        </div>

        {/* Content */}
        {loading ? (
          <LoadingSpinner label="Fetching available opportunities..." />
        ) : filteredJobs.length === 0 ? (
          <EmptyState
            icon={Briefcase}
            title="No matching positions found"
            description={
              searchTerm || selectedType !== 'all' || selectedLocation
                ? 'Try adjusting your search criteria or clearing filters.'
                : 'There are currently no active job postings published by recruiters.'
            }
            action={
              searchTerm || selectedType !== 'all' || selectedLocation ? (
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => {
                    setSearchTerm('');
                    setSelectedType('all');
                    setSelectedLocation('');
                  }}
                >
                  Clear Filters
                </Button>
              ) : undefined
            }
          />
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {filteredJobs.map((job) => (
              <Card
                key={job.id}
                className="flex flex-col justify-between hover:border-indigo-500/40 transition-colors group"
              >
                <div>
                  <div className="flex items-start justify-between gap-3 mb-2">
                    <div>
                      <h3 className="text-lg font-bold text-white group-hover:text-indigo-400 transition-colors">
                        <Link to={`/jobs/${job.id}`}>{job.title}</Link>
                      </h3>
                      <div className="flex items-center gap-2 text-xs text-slate-300 mt-1">
                        <span className="flex items-center gap-1 font-medium text-slate-200">
                          <Building className="w-3.5 h-3.5 text-slate-400" />
                          {job.company_name}
                        </span>
                        <span className="text-slate-600">•</span>
                        <span className="flex items-center gap-1 text-slate-400">
                          <MapPin className="w-3.5 h-3.5 text-slate-500" />
                          {job.location}
                        </span>
                      </div>
                    </div>
                    <Badge variant="cyan">{job.job_type}</Badge>
                  </div>

                  <p className="text-xs text-slate-400 line-clamp-2 mt-2 leading-relaxed">
                    {job.description}
                  </p>

                  <div className="flex flex-wrap items-center gap-2 mt-4 text-xs text-slate-300">
                    <span className="flex items-center gap-1 bg-slate-800/80 px-2 py-1 rounded border border-slate-700/60 text-slate-300">
                      <Clock className="w-3 h-3 text-slate-400" />
                      {job.min_experience_years === 0
                        ? 'Entry Level'
                        : `${job.min_experience_years}+ yrs exp`}
                    </span>
                    {job.required_education && (
                      <span className="flex items-center gap-1 bg-slate-800/80 px-2 py-1 rounded border border-slate-700/60 text-slate-300">
                        <GraduationCap className="w-3 h-3 text-slate-400" />
                        {job.required_education}
                      </span>
                    )}
                  </div>

                  {/* Skills preview */}
                  <div className="mt-3">
                    <div className="text-[11px] font-medium text-slate-400 mb-1.5 uppercase tracking-wider">
                      Required Skills:
                    </div>
                    <div className="flex flex-wrap gap-1.5">
                      {(job.required_skills || []).slice(0, 5).map((skill, idx) => (
                        <span
                          key={idx}
                          className="px-2 py-0.5 rounded text-[11px] bg-indigo-500/10 text-indigo-300 border border-indigo-500/20"
                        >
                          {skill}
                        </span>
                      ))}
                      {(job.required_skills || []).length > 5 && (
                        <span className="px-1.5 py-0.5 rounded text-[11px] bg-slate-800 text-slate-400">
                          +{job.required_skills.length - 5} more
                        </span>
                      )}
                    </div>
                  </div>
                </div>

                {/* Card footer actions */}
                <div className="flex items-center justify-between gap-2 pt-4 mt-4 border-t border-slate-800/80">
                  {isAuthenticated && isCandidate ? (
                    <Link
                      to={`/candidate/jobs/${job.id}/match`}
                      className="inline-flex items-center gap-1 text-xs font-medium text-indigo-400 hover:text-indigo-300"
                    >
                      <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
                      Check ATS Match Fit
                    </Link>
                  ) : (
                    <Link
                      to={`/jobs/${job.id}`}
                      className="inline-flex items-center gap-1 text-xs font-medium text-slate-400 hover:text-indigo-300"
                    >
                      <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
                      Inspect Competencies
                    </Link>
                  )}

                  <div className="flex items-center gap-2">
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => navigate(`/jobs/${job.id}`)}
                      rightIcon={<ArrowRight className="w-3.5 h-3.5" />}
                    >
                      View & Apply
                    </Button>
                  </div>
                </div>
              </Card>
            ))}
          </div>
        )}
      </div>
    </AppLayout>
  );
};
