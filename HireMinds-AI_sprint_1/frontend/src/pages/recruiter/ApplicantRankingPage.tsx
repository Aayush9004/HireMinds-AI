import React, { useEffect, useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { AppLayout } from '../../components/layout/AppLayout';
import { Card, CardHeader } from '../../components/ui/Card';
import { Button } from '../../components/ui/Button';
import { Badge } from '../../components/ui/Badge';
import { Modal } from '../../components/ui/Modal';
import { Alert } from '../../components/ui/Alert';
import { LoadingSpinner } from '../../components/ui/LoadingSpinner';
import { EmptyState } from '../../components/ui/EmptyState';
import { jobService } from '../../services/jobService';
import { matchingService } from '../../services/matchingService';
import { Job, AtsCandidateRanking, ApplicationStatus } from '../../types';
import { getErrorMessage } from '../../services/api';
import {
  Users,
  ArrowLeft,
  Sparkles,
  ShieldCheck,
  FileText,
  Clock,
  CheckCircle2,
  HelpCircle,
  TrendingUp,
  MessageSquare,
  Building,
} from 'lucide-react';

export const ApplicantRankingPage: React.FC = () => {
  const { jobId } = useParams<{ jobId: string }>();
  const navigate = useNavigate();

  const [job, setJob] = useState<Job | null>(null);
  const [rankings, setRankings] = useState<AtsCandidateRanking[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Notes Modal state
  const [isNotesModalOpen, setIsNotesModalOpen] = useState(false);
  const [activeRanking, setActiveRanking] = useState<AtsCandidateRanking | null>(null);
  const [recruiterNotes, setRecruiterNotes] = useState('');
  const [updatingStatus, setUpdatingStatus] = useState(false);

  useEffect(() => {
    if (!jobId) return;
    loadRankings();
  }, [jobId]);

  const loadRankings = async () => {
    setLoading(true);
    setError(null);
    try {
      const id = parseInt(jobId!, 10);
      const [jobData, rankingsData] = await Promise.all([
        jobService.getJob(id),
        matchingService.getJobRankings(id),
      ]);
      setJob(jobData);
      const items = (rankingsData as any).items || (rankingsData as any).rankings || [];
      setRankings(items);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  const handleStatusChange = async (
    ranking: AtsCandidateRanking,
    newStatus: ApplicationStatus
  ) => {
    setError(null);
    try {
      await jobService.updateApplicationStatus(ranking.application_id, newStatus);
      setRankings((prev) =>
        prev.map((r) =>
          r.application_id === ranking.application_id
            ? { ...r, application_status: newStatus }
            : r
        )
      );
      setSuccessMsg(`Updated ${ranking.candidate_name}'s status to ${newStatus.replace('_', ' ')}.`);
    } catch (err) {
      setError(getErrorMessage(err));
    }
  };

  const handleSaveNotes = async () => {
    if (!activeRanking) return;
    setUpdatingStatus(true);
    setError(null);
    try {
      await jobService.updateApplicationStatus(
        activeRanking.application_id,
        activeRanking.application_status,
        recruiterNotes.trim()
      );
      setIsNotesModalOpen(false);
      setSuccessMsg(`Saved notes for ${activeRanking.candidate_name}.`);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setUpdatingStatus(false);
    }
  };

  if (loading) {
    return (
      <AppLayout>
        <LoadingSpinner fullPage label="Evaluating ATS ranking leaderboard for applicants..." />
      </AppLayout>
    );
  }

  if (!job) {
    return (
      <AppLayout>
        <div className="text-center py-12">
          <p className="text-slate-400">Position not found.</p>
          <Button variant="secondary" className="mt-4" onClick={() => navigate('/recruiter/jobs')}>
            Back to Jobs
          </Button>
        </div>
      </AppLayout>
    );
  }

  return (
    <AppLayout>
      <div className="space-y-6">
        {/* Header */}
        <div>
          <button
            onClick={() => navigate('/recruiter/jobs')}
            className="inline-flex items-center gap-1.5 text-xs text-slate-400 hover:text-white transition-colors cursor-pointer mb-2"
          >
            <ArrowLeft className="w-4 h-4" /> Back to job postings
          </button>
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-2xl font-bold text-white flex items-center gap-2">
                  <Users className="w-6 h-6 text-indigo-400" />
                  Applicant Leaderboard & ATS Rankings
                </h1>
                <Badge variant={job.is_active ? 'success' : 'neutral'}>
                  {job.is_active ? 'Active' : 'Closed'}
                </Badge>
              </div>
              <p className="text-xs text-slate-400 mt-1">
                Role: <strong className="text-slate-200">{job.title}</strong> at {job.company_name} •{' '}
                <span className="text-indigo-400 font-semibold">{rankings.length} total applicants</span>
              </p>
            </div>

            <div className="flex items-center gap-2">
              <Button
                variant="secondary"
                size="sm"
                onClick={loadRankings}
                leftIcon={<Sparkles className="w-3.5 h-3.5 text-indigo-400" />}
              >
                Re-calculate Rankings
              </Button>
            </div>
          </div>
        </div>

        {successMsg && (
          <Alert variant="success" onClose={() => setSuccessMsg(null)}>
            {successMsg}
          </Alert>
        )}

        {error && (
          <Alert variant="danger" onClose={() => setError(null)}>
            {error}
          </Alert>
        )}

        {/* Explainability & Notice Banner */}
        <div className="p-3.5 rounded-xl bg-slate-900 border border-slate-800 text-xs text-slate-400 flex items-start gap-2.5">
          <HelpCircle className="w-4 h-4 text-indigo-400 shrink-0 mt-0.5" />
          <p className="text-[11px] leading-relaxed">
            Candidates are ordered strictly by their transparent, multi-signal ATS alignment score (skills, experience, education, projects, semantic fit). HireMinds AI is designed for human decision-support: review each candidate's comprehensive evidence before making recruitment decisions.
          </p>
        </div>

        {/* Rankings Table */}
        <Card>
          <CardHeader
            title="Ranked Candidate Pipeline"
            subtitle="Transparent ATS scores, stage management, and diagnostic dossiers"
          />

          {rankings.length === 0 ? (
            <EmptyState
              icon={Users}
              title="No candidates have applied yet"
              description="When candidates apply to this position, they will automatically appear here ranked by ATS alignment."
            />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="border-b border-slate-800 text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                    <th className="py-3 px-3 w-12 text-center">Rank</th>
                    <th className="py-3 px-3">Candidate</th>
                    <th className="py-3 px-3">ATS Score</th>
                    <th className="py-3 px-3">Skill Fit</th>
                    <th className="py-3 px-3">Application Stage</th>
                    <th className="py-3 px-3 text-right">Dossier & Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60 text-xs">
                  {rankings.map((cand) => {
                    const score = cand.ats_score !== null ? Math.round(cand.ats_score) : 0;
                    const rankNum = cand.rank ?? '-';

                    return (
                      <tr key={cand.application_id} className="hover:bg-slate-800/40 transition-colors">
                        {/* Rank */}
                        <td className="py-3 px-3 text-center">
                          <span
                            className={`inline-flex items-center justify-center w-6 h-6 rounded-full text-xs font-bold ${
                              rankNum === 1
                                ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40'
                                : rankNum === 2
                                ? 'bg-slate-300/20 text-slate-200 border border-slate-400/40'
                                : rankNum === 3
                                ? 'bg-amber-700/20 text-amber-400 border border-amber-700/40'
                                : 'text-slate-500 font-normal'
                            }`}
                          >
                            #{rankNum}
                          </span>
                        </td>

                        {/* Candidate details */}
                        <td className="py-3 px-3">
                          <div className="font-semibold text-slate-100">
                            {cand.candidate_name || `Candidate #${cand.candidate_id}`}
                          </div>
                          <div className="text-[11px] text-slate-400">{cand.candidate_email || 'Applicant'}</div>
                          <div className="text-[10px] text-slate-500 mt-0.5">
                            {cand.applied_at ? `Applied ${new Date(cand.applied_at).toLocaleDateString()}` : 'Applied recently'}
                          </div>
                        </td>

                        {/* ATS Score */}
                        <td className="py-3 px-3">
                          <div className="flex items-center gap-2">
                            <span className="text-base font-extrabold text-white">
                              {cand.ats_score !== null ? `${score}/100` : 'Pending'}
                            </span>
                            {cand.confidence && (
                              <Badge
                                size="sm"
                                variant={score >= 70 ? 'success' : score >= 50 ? 'warning' : 'neutral'}
                              >
                                {cand.confidence}
                              </Badge>
                            )}
                          </div>
                          <div className="w-24 bg-slate-800 rounded-full h-1 mt-1.5 overflow-hidden">
                            <div
                              className={`h-full rounded-full ${
                                score >= 70
                                  ? 'bg-emerald-500'
                                  : score >= 50
                                  ? 'bg-amber-500'
                                  : 'bg-indigo-500'
                              }`}
                              style={{ width: `${Math.min(100, Math.max(0, score))}%` }}
                            />
                          </div>
                        </td>

                        {/* Skill Fit */}
                        <td className="py-3 px-3 text-slate-300">
                          {cand.skill_score !== null && cand.skill_score !== undefined ? (
                            <span className="font-medium text-slate-200">
                              {Math.round(cand.skill_score)}% overlap
                            </span>
                          ) : cand.component_scores && cand.component_scores.skill !== null && cand.component_scores.skill !== undefined ? (
                            <span className="font-medium text-slate-200">
                              {Math.round(cand.component_scores.skill)}% overlap
                            </span>
                          ) : (
                            <span className="text-slate-500">—</span>
                          )}
                        </td>

                        {/* Status Dropdown */}
                        <td className="py-3 px-3">
                          <select
                            value={cand.application_status || (cand.status as any) || 'applied'}
                            onChange={(e) =>
                              handleStatusChange(cand, e.target.value as ApplicationStatus)
                            }
                            className="bg-slate-950 border border-slate-800 rounded-lg px-2 py-1 text-xs text-slate-200 focus:outline-none focus:border-indigo-500"
                          >
                            <option value="applied">Applied</option>
                            <option value="under_review">Under Review</option>
                            <option value="shortlisted">Shortlisted</option>
                            <option value="assessment_pending">Assessment Pending</option>
                            <option value="interview_scheduled">Interview Scheduled</option>
                            <option value="accepted">Accepted</option>
                            <option value="rejected">Rejected</option>
                          </select>
                        </td>

                        {/* Actions */}
                        <td className="py-3 px-3 text-right">
                          <div className="flex items-center justify-end gap-1.5">
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => {
                                setActiveRanking(cand);
                                setRecruiterNotes('');
                                setIsNotesModalOpen(true);
                              }}
                              title="Add/Edit Recruiter Notes"
                            >
                              <MessageSquare className="w-3.5 h-3.5 text-slate-400" />
                            </Button>

                            <Button
                              variant="secondary"
                              size="sm"
                              onClick={() =>
                                navigate(
                                  `/recruiter/reports/jobs/${job.id}/candidates/${cand.candidate_id}`
                                )
                              }
                              rightIcon={<TrendingUp className="w-3.5 h-3.5" />}
                            >
                              Inspect Dossier
                            </Button>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </Card>

        {/* Notes Modal */}
        <Modal
          isOpen={isNotesModalOpen}
          onClose={() => setIsNotesModalOpen(false)}
          title={`Recruiter Feedback — ${activeRanking?.candidate_name}`}
          description="Record hiring decision notes or feedback visible on the candidate application."
        >
          <div className="space-y-4">
            <textarea
              rows={5}
              value={recruiterNotes}
              onChange={(e) => setRecruiterNotes(e.target.value)}
              placeholder="e.g. Candidate exhibited strong Python fundamentals. Advancing to round 2 technical interview..."
              className="w-full bg-slate-950 border border-slate-800 rounded-xl p-3 text-xs text-slate-200 focus:outline-none focus:border-indigo-500 resize-none"
            />
            <div className="flex justify-end gap-2">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setIsNotesModalOpen(false)}
              >
                Cancel
              </Button>
              <Button
                variant="primary"
                size="sm"
                isLoading={updatingStatus}
                onClick={handleSaveNotes}
              >
                Save Notes
              </Button>
            </div>
          </div>
        </Modal>
      </div>
    </AppLayout>
  );
};
