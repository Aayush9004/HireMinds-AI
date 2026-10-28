import React, { useEffect, useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { AppLayout } from '../../components/layout/AppLayout';
import { Card, CardHeader } from '../../components/ui/Card';
import { Button } from '../../components/ui/Button';
import { Badge } from '../../components/ui/Badge';
import { Modal } from '../../components/ui/Modal';
import { Alert } from '../../components/ui/Alert';
import { LoadingSpinner } from '../../components/ui/LoadingSpinner';
import { jobService } from '../../services/jobService';
import { resumeService } from '../../services/resumeService';
import { Job, JobApplication, Resume } from '../../types';
import { getErrorMessage } from '../../services/api';
import {
  Briefcase,
  Building,
  MapPin,
  Clock,
  GraduationCap,
  Sparkles,
  ArrowLeft,
  CheckCircle2,
  FileText,
  Send,
  AlertTriangle,
} from 'lucide-react';

export const JobDetailPage: React.FC = () => {
  const { jobId } = useParams<{ jobId: string }>();
  const navigate = useNavigate();
  const { isAuthenticated, isCandidate, isRecruiter } = useAuth();

  const [job, setJob] = useState<Job | null>(null);
  const [resumes, setResumes] = useState<Resume[]>([]);
  const [existingApplication, setExistingApplication] = useState<JobApplication | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Application Modal state
  const [isApplyModalOpen, setIsApplyModalOpen] = useState(false);
  const [selectedResumeId, setSelectedResumeId] = useState<number | ''>('');
  const [coverLetter, setCoverLetter] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [applySuccess, setApplySuccess] = useState<string | null>(null);

  useEffect(() => {
    if (!jobId) return;
    loadJobDetails();
  }, [jobId]);

  const loadJobDetails = async () => {
    setLoading(true);
    setError(null);
    try {
      const id = parseInt(jobId!, 10);
      const [jobData, resumesData, myApps] = await Promise.all([
        jobService.getJob(id),
        resumeService.getMyResumes().catch(() => []),
        jobService.getMyApplications().catch(() => []),
      ]);

      setJob(jobData);
      setResumes(resumesData);
      if (resumesData.length > 0 && selectedResumeId === '') {
        setSelectedResumeId(resumesData[0].id);
      }

      const matchApp = myApps.find((app) => app.job_id === id);
      if (matchApp) {
        setExistingApplication(matchApp);
      }
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  const handleApply = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedResumeId || !job) return;

    setSubmitting(true);
    setError(null);
    try {
      const app = await jobService.applyToJob(
        job.id,
        Number(selectedResumeId),
        coverLetter.trim() || undefined
      );
      setExistingApplication(app);
      setIsApplyModalOpen(false);
      setApplySuccess('Application submitted successfully! Track status here or on your dashboard.');
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <AppLayout>
        <LoadingSpinner fullPage label="Loading job position details..." />
      </AppLayout>
    );
  }

  if (!job) {
    return (
      <AppLayout>
        <div className="text-center py-12">
          <p className="text-slate-400">Position not found or no longer active.</p>
          <Button
            variant="secondary"
            className="mt-4"
            onClick={() => navigate('/jobs')}
          >
            Back to Jobs
          </Button>
        </div>
      </AppLayout>
    );
  }

  return (
    <AppLayout>
      <div className="max-w-4xl mx-auto space-y-6">
        {/* Navigation Breadcrumb */}
        <div>
          <button
            onClick={() => navigate('/jobs')}
            className="inline-flex items-center gap-1.5 text-xs text-slate-400 hover:text-white transition-colors cursor-pointer"
          >
            <ArrowLeft className="w-4 h-4" /> Back to job search
          </button>
        </div>

        {applySuccess && (
          <Alert variant="success" onClose={() => setApplySuccess(null)}>
            {applySuccess}
          </Alert>
        )}

        {error && (
          <Alert variant="danger" onClose={() => setError(null)}>
            {error}
          </Alert>
        )}

        {/* Job Header Card */}
        <Card>
          <div className="flex flex-col md:flex-row md:items-start justify-between gap-4">
            <div>
              <div className="flex items-center gap-2 mb-1.5">
                <Badge variant={job.is_active ? 'success' : 'neutral'}>
                  {job.is_active ? 'Active Opening' : 'Closed'}
                </Badge>
                <Badge variant="cyan">{job.job_type}</Badge>
              </div>
              <h1 className="text-2xl font-bold text-white">{job.title}</h1>
              <div className="flex flex-wrap items-center gap-4 text-xs text-slate-300 mt-2">
                <span className="flex items-center gap-1.5 font-medium text-slate-200">
                  <Building className="w-4 h-4 text-slate-400" />
                  {job.company_name}
                </span>
                <span className="text-slate-600">•</span>
                <span className="flex items-center gap-1.5 text-slate-400">
                  <MapPin className="w-4 h-4 text-slate-500" />
                  {job.location}
                </span>
                <span className="text-slate-600">•</span>
                <span className="flex items-center gap-1.5 text-slate-400">
                  <Clock className="w-4 h-4 text-slate-500" />
                  Posted {new Date(job.created_at).toLocaleDateString()}
                </span>
              </div>
            </div>

            {/* Application action button */}
            <div className="flex flex-col sm:flex-row md:flex-col items-stretch sm:items-center md:items-end gap-2.5 shrink-0">
              {existingApplication ? (
                <div className="bg-emerald-950/40 border border-emerald-500/30 rounded-lg p-3 text-right">
                  <div className="flex items-center gap-1.5 text-emerald-400 text-xs font-semibold justify-end">
                    <CheckCircle2 className="w-4 h-4" /> Application Submitted
                  </div>
                  <div className="text-[11px] text-slate-400 mt-1">
                    Status:{' '}
                    <span className="text-white capitalize font-medium">
                      {existingApplication.status.replace('_', ' ')}
                    </span>
                  </div>
                  <div className="text-[10px] text-slate-500 mt-0.5">
                    Applied {new Date(existingApplication.created_at).toLocaleDateString()}
                  </div>
                </div>
              ) : isRecruiter ? (
                <Button
                  variant="secondary"
                  size="md"
                  onClick={() => navigate('/recruiter/jobs')}
                  leftIcon={<Briefcase className="w-4 h-4" />}
                >
                  Manage in Recruiter Portal
                </Button>
              ) : isAuthenticated ? (
                <Button
                  variant="primary"
                  size="md"
                  onClick={() => setIsApplyModalOpen(true)}
                  disabled={!job.is_active}
                  leftIcon={<Send className="w-4 h-4" />}
                >
                  Apply to Position
                </Button>
              ) : (
                <Button
                  variant="primary"
                  size="md"
                  onClick={() => navigate(`/login?redirect=/jobs/${job.id}`)}
                  leftIcon={<Send className="w-4 h-4" />}
                >
                  Sign In to Apply
                </Button>
              )}

              {isAuthenticated && isCandidate ? (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => navigate(`/candidate/jobs/${job.id}/match`)}
                  leftIcon={<Sparkles className="w-4 h-4 text-indigo-400" />}
                >
                  Inspect ATS Alignment
                </Button>
              ) : (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => navigate('/login')}
                  leftIcon={<Sparkles className="w-4 h-4 text-indigo-400" />}
                >
                  Sign In for ATS Match
                </Button>
              )}
            </div>
          </div>

          {/* Quick Metrics */}
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 mt-6 pt-5 border-t border-slate-800">
            <div className="bg-slate-950/60 rounded-lg p-3 border border-slate-800/80">
              <div className="text-[11px] text-slate-400 uppercase tracking-wider flex items-center gap-1">
                <Clock className="w-3.5 h-3.5 text-indigo-400" /> Experience
              </div>
              <div className="text-sm font-semibold text-slate-100 mt-1">
                {job.min_experience_years === 0 ? 'No minimum' : `${job.min_experience_years}+ years`}
              </div>
            </div>

            <div className="bg-slate-950/60 rounded-lg p-3 border border-slate-800/80">
              <div className="text-[11px] text-slate-400 uppercase tracking-wider flex items-center gap-1">
                <GraduationCap className="w-3.5 h-3.5 text-violet-400" /> Required Education
              </div>
              <div className="text-sm font-semibold text-slate-100 mt-1">
                {job.required_education || 'Any degree / equivalent'}
              </div>
            </div>

            <div className="bg-slate-950/60 rounded-lg p-3 border border-slate-800/80 col-span-2 sm:col-span-1">
              <div className="text-[11px] text-slate-400 uppercase tracking-wider flex items-center gap-1">
                <Briefcase className="w-3.5 h-3.5 text-cyan-400" /> Job Type
              </div>
              <div className="text-sm font-semibold text-slate-100 mt-1 capitalize">
                {job.job_type}
              </div>
            </div>
          </div>
        </Card>

        {/* Job Details and Skills */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 space-y-6">
            {/* Description */}
            <Card>
              <h2 className="text-base font-semibold text-white mb-3">Job Description</h2>
              <div className="text-sm text-slate-300 leading-relaxed whitespace-pre-line">
                {job.description}
              </div>
            </Card>

            {/* Application Notes if already applied */}
            {existingApplication && existingApplication.recruiter_notes && (
              <Card className="border-indigo-500/30 bg-indigo-950/20">
                <CardHeader
                  title="Recruiter Feedback / Notes"
                  subtitle="Notes left by the hiring team regarding your submission"
                />
                <p className="text-sm text-slate-200 bg-slate-900/80 p-3 rounded-lg border border-slate-800">
                  {existingApplication.recruiter_notes}
                </p>
              </Card>
            )}
          </div>

          {/* Right column: Required & Preferred Skills */}
          <div className="space-y-6">
            <Card>
              <h3 className="text-sm font-semibold text-white mb-3 flex items-center gap-1.5">
                <Sparkles className="w-4 h-4 text-indigo-400" />
                Required Competencies ({(job.required_skills || []).length})
              </h3>
              <div className="flex flex-wrap gap-1.5">
                {(job.required_skills || []).map((skill, idx) => (
                  <span
                    key={idx}
                    className="px-2.5 py-1 rounded-md text-xs font-medium bg-indigo-500/15 text-indigo-300 border border-indigo-500/30"
                  >
                    {skill}
                  </span>
                ))}
              </div>

              {(job.preferred_skills || []).length > 0 && (
                <div className="mt-5 pt-4 border-t border-slate-800">
                  <h3 className="text-xs font-semibold text-slate-300 mb-2 uppercase tracking-wider">
                    Preferred / Nice to Have ({(job.preferred_skills || []).length})
                  </h3>
                  <div className="flex flex-wrap gap-1.5">
                    {(job.preferred_skills || []).map((skill, idx) => (
                      <span
                        key={idx}
                        className="px-2 py-0.5 rounded text-xs bg-slate-800 text-slate-300 border border-slate-700/60"
                      >
                        {skill}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </Card>

            {/* Preparation Helper */}
            <Card className="bg-gradient-to-br from-indigo-950/30 to-slate-900 border-indigo-500/20">
              <h3 className="text-sm font-semibold text-indigo-200 mb-2">Practice for this Role</h3>
              <p className="text-xs text-slate-300 leading-relaxed mb-4">
                Test your skills with an AI mock interview tailored to this role's required skills and difficulty.
              </p>
              <Button
                variant="primary"
                size="sm"
                className="w-full"
                onClick={() => navigate(isAuthenticated ? '/candidate/interviews' : '/login')}
              >
                Launch Mock Interview
              </Button>
            </Card>
          </div>
        </div>

        {/* Apply Modal */}
        <Modal
          isOpen={isApplyModalOpen}
          onClose={() => setIsApplyModalOpen(false)}
          title={`Apply for ${job.title}`}
          description={`Submit your verified resume to ${job.company_name}`}
        >
          <form onSubmit={handleApply} className="space-y-4">
            {resumes.length === 0 ? (
              <div className="p-4 rounded-lg bg-amber-500/10 border border-amber-500/20 text-xs text-amber-300">
                <AlertTriangle className="w-4 h-4 inline mr-1 text-amber-400" />
                You haven't uploaded any resumes yet. Please upload a resume first before applying.
                <div className="mt-3">
                  <Button
                    size="sm"
                    variant="primary"
                    onClick={() => navigate('/candidate/resumes')}
                  >
                    Go to Resume Upload
                  </Button>
                </div>
              </div>
            ) : (
              <>
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1.5">
                    Select Resume to Submit <span className="text-rose-400">*</span>
                  </label>
                  <select
                    value={selectedResumeId}
                    onChange={(e) => setSelectedResumeId(Number(e.target.value))}
                    required
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-indigo-500"
                  >
                    {resumes.map((r) => (
                      <option key={r.id} value={r.id}>
                        {r.filename} (Uploaded {new Date(r.created_at).toLocaleDateString()})
                        {r.is_reviewed_by_candidate ? ' — [Verified]' : ''}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1.5">
                    Cover Note / Additional Remarks (Optional)
                  </label>
                  <textarea
                    rows={4}
                    value={coverLetter}
                    onChange={(e) => setCoverLetter(e.target.value)}
                    placeholder="Briefly state why you're a great fit for this position..."
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg p-3 text-xs text-slate-200 focus:outline-none focus:border-indigo-500 placeholder:text-slate-500 resize-none"
                  />
                </div>

                <div className="flex justify-end gap-2 pt-2">
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={() => setIsApplyModalOpen(false)}
                  >
                    Cancel
                  </Button>
                  <Button
                    type="submit"
                    variant="primary"
                    size="sm"
                    isLoading={submitting}
                    disabled={!selectedResumeId}
                  >
                    Confirm Submission
                  </Button>
                </div>
              </>
            )}
          </form>
        </Modal>
      </div>
    </AppLayout>
  );
};
