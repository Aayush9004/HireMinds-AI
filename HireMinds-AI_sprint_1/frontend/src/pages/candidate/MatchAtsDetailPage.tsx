import React, { useEffect, useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { AppLayout } from '../../components/layout/AppLayout';
import { Card, CardHeader } from '../../components/ui/Card';
import { Button } from '../../components/ui/Button';
import { Badge } from '../../components/ui/Badge';
import { Alert } from '../../components/ui/Alert';
import { LoadingSpinner } from '../../components/ui/LoadingSpinner';
import { jobService } from '../../services/jobService';
import { resumeService } from '../../services/resumeService';
import { matchingService } from '../../services/matchingService';
import { Job, Resume, MatchResult, AtsExplanation } from '../../types';
import { getErrorMessage } from '../../services/api';
import {
  ArrowLeft,
  Sparkles,
  ShieldCheck,
  CheckCircle2,
  XCircle,
  FileText,
  Briefcase,
  HelpCircle,
  Quote,
  AlertCircle,
  BarChart3,
  TrendingUp,
} from 'lucide-react';

export const MatchAtsDetailPage: React.FC = () => {
  const { jobId } = useParams<{ jobId: string }>();
  const navigate = useNavigate();

  const [job, setJob] = useState<Job | null>(null);
  const [resumes, setResumes] = useState<Resume[]>([]);
  const [selectedResumeId, setSelectedResumeId] = useState<number | null>(null);

  const [matchResult, setMatchResult] = useState<MatchResult | null>(null);
  const [atsData, setAtsData] = useState<AtsExplanation | null>(null);

  const [loading, setLoading] = useState(true);
  const [computing, setComputing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!jobId) return;
    initData();
  }, [jobId]);

  const initData = async () => {
    setLoading(true);
    setError(null);
    try {
      const id = parseInt(jobId!, 10);
      const [jobData, resumesData] = await Promise.all([
        jobService.getJob(id),
        resumeService.getMyResumes(),
      ]);
      setJob(jobData);
      setResumes(resumesData);

      if (resumesData.length > 0) {
        const initialResumeId = resumesData[0].id;
        setSelectedResumeId(initialResumeId);
        await runMatchAndAts(initialResumeId, id);
      }
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  const runMatchAndAts = async (resumeId: number, jId: number) => {
    setComputing(true);
    setError(null);
    try {
      const [mRes, aRes] = await Promise.all([
        matchingService.computeMatch(resumeId, jId),
        matchingService.computeAts(resumeId, jId),
      ]);
      setMatchResult(mRes);
      setAtsData(aRes);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setComputing(false);
    }
  };

  const handleResumeChange = async (e: React.ChangeEvent<HTMLSelectElement>) => {
    const newResumeId = Number(e.target.value);
    setSelectedResumeId(newResumeId);
    if (job) {
      await runMatchAndAts(newResumeId, job.id);
    }
  };

  if (loading) {
    return (
      <AppLayout>
        <LoadingSpinner fullPage label="Calculating ATS alignment and multi-signal match..." />
      </AppLayout>
    );
  }

  if (!job) {
    return (
      <AppLayout>
        <div className="text-center py-12">
          <p className="text-slate-400">Position not found.</p>
          <Button variant="secondary" className="mt-4" onClick={() => navigate('/candidate/jobs')}>
            Back to Jobs
          </Button>
        </div>
      </AppLayout>
    );
  }

  if (resumes.length === 0) {
    return (
      <AppLayout>
        <div className="max-w-2xl mx-auto text-center py-16 space-y-4">
          <FileText className="w-12 h-12 text-slate-500 mx-auto" />
          <h2 className="text-xl font-bold text-white">No Resume Found</h2>
          <p className="text-sm text-slate-400">
            Please upload a resume first to evaluate ATS alignment against this role.
          </p>
          <Button variant="primary" onClick={() => navigate('/candidate/resumes')}>
            Upload Resume
          </Button>
        </div>
      </AppLayout>
    );
  }

  const overallMatchPct = matchResult?.overall_score
    ? Math.round(matchResult.overall_score * 100)
    : 0;

  const atsScore = atsData?.ats_score ?? matchResult?.ats_score ?? 0;

  return (
    <AppLayout>
      <div className="max-w-5xl mx-auto space-y-6">
        {/* Navigation & Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <button
              onClick={() => navigate(`/candidate/jobs/${job.id}`)}
              className="inline-flex items-center gap-1.5 text-xs text-slate-400 hover:text-white transition-colors cursor-pointer mb-2"
            >
              <ArrowLeft className="w-4 h-4" /> Back to job details
            </button>
            <h1 className="text-2xl font-bold text-white flex items-center gap-2">
              <Sparkles className="w-6 h-6 text-indigo-400" />
              ATS & Fit Diagnostic
            </h1>
            <p className="text-xs text-slate-400 mt-1">
              Position: <strong className="text-slate-200">{job.title}</strong> at {job.company_name}
            </p>
          </div>

          {/* Select Resume dropdown */}
          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-400 shrink-0">Evaluate Resume:</span>
            <select
              value={selectedResumeId || ''}
              onChange={handleResumeChange}
              disabled={computing}
              className="bg-slate-900 border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-indigo-500"
            >
              {resumes.map((r) => (
                <option key={r.id} value={r.id}>
                  {r.filename} {r.is_reviewed_by_candidate ? '(Verified)' : ''}
                </option>
              ))}
            </select>
          </div>
        </div>

        {error && (
          <Alert variant="danger" onClose={() => setError(null)}>
            {error}
          </Alert>
        )}

        {/* Recomputation loading overlay or indicator */}
        {computing && (
          <div className="p-4 rounded-xl bg-indigo-950/40 border border-indigo-500/30 text-indigo-300 text-xs flex items-center gap-2">
            <LoadingSpinner size="sm" />
            Analyzing resume text, TF-IDF lexical density, and semantic embeddings...
          </div>
        )}

        {/* Primary Scores Banner */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* ATS Score Card */}
          <Card className="bg-gradient-to-br from-slate-900 via-slate-900 to-indigo-950/40 border-indigo-500/30">
            <div className="flex items-center justify-between text-xs text-slate-400">
              <span className="font-semibold uppercase tracking-wider flex items-center gap-1.5">
                <ShieldCheck className="w-4 h-4 text-indigo-400" />
                Explainable ATS Score
              </span>
              <Badge variant={atsScore >= 70 ? 'success' : atsScore >= 50 ? 'warning' : 'neutral'}>
                {atsData?.confidence || 'Confidence: Normal'}
              </Badge>
            </div>
            <div className="mt-4 flex items-baseline gap-2">
              <span className="text-4xl font-extrabold text-white">{atsScore}</span>
              <span className="text-slate-400 text-sm">/ 100</span>
            </div>
            <div className="w-full bg-slate-800 rounded-full h-2 mt-3 overflow-hidden">
              <div
                className={`h-full rounded-full transition-all duration-500 ${
                  atsScore >= 70
                    ? 'bg-emerald-500'
                    : atsScore >= 50
                    ? 'bg-amber-500'
                    : 'bg-indigo-500'
                }`}
                style={{ width: `${Math.min(100, Math.max(0, atsScore))}%` }}
              />
            </div>
            <p className="text-[11px] text-slate-400 mt-3 leading-relaxed">
              Weighted composite of skills, experience, education, and project relevance.
            </p>
          </Card>

          {/* Semantic & Blended Match Score Card */}
          <Card>
            <div className="flex items-center justify-between text-xs text-slate-400">
              <span className="font-semibold uppercase tracking-wider flex items-center gap-1.5">
                <BarChart3 className="w-4 h-4 text-violet-400" />
                Blended Match Fit
              </span>
              <Badge variant="purple">{overallMatchPct}% Overall</Badge>
            </div>
            <div className="mt-4 flex items-baseline gap-2">
              <span className="text-4xl font-extrabold text-white">{overallMatchPct}%</span>
            </div>
            <div className="w-full bg-slate-800 rounded-full h-2 mt-3 overflow-hidden">
              <div
                className="h-full rounded-full bg-violet-500 transition-all duration-500"
                style={{ width: `${Math.min(100, Math.max(0, overallMatchPct))}%` }}
              />
            </div>
            <div className="grid grid-cols-2 gap-2 mt-3 text-[11px] text-slate-400 border-t border-slate-800/80 pt-2">
              <div>
                TF-IDF Lexical:{' '}
                <strong className="text-slate-200">
                  {matchResult?.tfidf_score ? Math.round(matchResult.tfidf_score * 100) : 0}%
                </strong>
              </div>
              <div>
                Semantic Embeddings:{' '}
                <strong className="text-slate-200">
                  {matchResult?.semantic_score ? Math.round(matchResult.semantic_score * 100) : 0}%
                </strong>
              </div>
            </div>
          </Card>

          {/* Report Link Card */}
          <Card className="flex flex-col justify-between">
            <div>
              <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
                <TrendingUp className="w-4 h-4 text-emerald-400" />
                Unified Readiness Report
              </div>
              <h3 className="text-sm font-semibold text-white mt-2">
                Deep-Dive Candidate Diagnostic
              </h3>
              <p className="text-xs text-slate-400 mt-1 leading-relaxed">
                Review complete readiness breakdown including mock interviews, coding assessments, and personalized study plan.
              </p>
            </div>

            {selectedResumeId && (
              <Button
                variant="secondary"
                size="sm"
                className="w-full mt-4"
                onClick={() => navigate(`/candidate/reports/${job.id}/${selectedResumeId}`)}
              >
                Open Unified Report
              </Button>
            )}
          </Card>
        </div>

        {/* Skill Match Breakdown */}
        {matchResult?.skill_match_details && (
          <Card>
            <CardHeader
              title="Skill Alignment Analysis"
              subtitle="Comparison of your extracted resume skills against job requirements"
            />
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Matched Skills */}
              <div className="bg-emerald-950/20 border border-emerald-500/20 rounded-xl p-4">
                <div className="flex items-center gap-2 text-xs font-semibold text-emerald-400 mb-2">
                  <CheckCircle2 className="w-4 h-4" />
                  Matched Competencies ({matchResult.skill_match_details.matched?.length || 0})
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {matchResult.skill_match_details.matched &&
                  matchResult.skill_match_details.matched.length > 0 ? (
                    matchResult.skill_match_details.matched.map((skill, idx) => (
                      <span
                        key={idx}
                        className="px-2.5 py-1 rounded-md text-xs font-medium bg-emerald-500/15 text-emerald-300 border border-emerald-500/30"
                      >
                        ✓ {skill}
                      </span>
                    ))
                  ) : (
                    <span className="text-xs text-slate-400 italic">No direct overlap detected</span>
                  )}
                </div>
              </div>

              {/* Missing Skills */}
              <div className="bg-rose-950/20 border border-rose-500/20 rounded-xl p-4">
                <div className="flex items-center gap-2 text-xs font-semibold text-rose-400 mb-2">
                  <XCircle className="w-4 h-4" />
                  Unmatched Job Requirements ({matchResult.skill_match_details.missing?.length || 0})
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {matchResult.skill_match_details.missing &&
                  matchResult.skill_match_details.missing.length > 0 ? (
                    matchResult.skill_match_details.missing.map((skill, idx) => (
                      <span
                        key={idx}
                        className="px-2.5 py-1 rounded-md text-xs font-medium bg-rose-500/15 text-rose-300 border border-rose-500/30"
                      >
                        ✗ {skill}
                      </span>
                    ))
                  ) : (
                    <span className="text-xs text-emerald-400 font-medium">
                      All required skills matched!
                    </span>
                  )}
                </div>
              </div>
            </div>
          </Card>
        )}

        {/* Explainable ATS Component Breakdown */}
        {atsData && (
          <Card>
            <CardHeader
              title="Explainable ATS Rubric Breakdown"
              subtitle="Component-by-component scoring, weights, and verifiable resume evidence"
            />

            {/* Component Cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
              {Object.entries(atsData.component_scores).map(([compName, compScore]) => {
                const weight = atsData.effective_weights[compName] ?? 0;
                const rationale = atsData.rationales[compName];
                const evidenceList = atsData.evidence[compName] || [];
                const missing = atsData.missing_information[compName];

                return (
                  <div
                    key={compName}
                    className="bg-slate-950/70 border border-slate-800 rounded-xl p-4 flex flex-col justify-between"
                  >
                    <div>
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-bold text-slate-200 capitalize">
                          {compName} Match
                        </span>
                        <span className="text-[10px] text-indigo-400 font-medium bg-indigo-500/10 px-1.5 py-0.5 rounded border border-indigo-500/20">
                          {Math.round(weight * 100)}% Weight
                        </span>
                      </div>

                      <div className="mt-2 flex items-baseline gap-1.5">
                        <span className="text-2xl font-extrabold text-white">
                          {compScore !== null ? Math.round(compScore) : 'N/A'}
                        </span>
                        {compScore !== null && (
                          <span className="text-xs text-slate-500">/ 100</span>
                        )}
                      </div>

                      {rationale && (
                        <p className="text-[11px] text-slate-300 mt-2 leading-relaxed">
                          {rationale}
                        </p>
                      )}

                      {/* Evidence Quotes */}
                      {evidenceList.length > 0 && (
                        <div className="mt-3 pt-2.5 border-t border-slate-800/80">
                          <div className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-1 mb-1">
                            <Quote className="w-3 h-3 text-indigo-400" /> Extracted Evidence:
                          </div>
                          <ul className="space-y-1">
                            {evidenceList.slice(0, 2).map((ev, i) => (
                              <li
                                key={i}
                                className="text-[10px] text-slate-400 italic bg-slate-900/90 p-1.5 rounded border border-slate-800/60"
                              >
                                "{ev}"
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}

                      {/* Missing info warning */}
                      {missing && (
                        <div className="mt-2 text-[10px] text-amber-400 flex items-start gap-1">
                          <AlertCircle className="w-3 h-3 shrink-0 mt-0.5" />
                          <span>{missing}</span>
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Legal / Ethical ATS Disclaimer */}
            <div className="mt-6 p-4 rounded-xl bg-slate-950 border border-slate-800 text-xs text-slate-400 space-y-1.5">
              <div className="font-semibold text-slate-200 flex items-center gap-1.5">
                <HelpCircle className="w-4 h-4 text-indigo-400" />
                Transparency & Decision-Support Notice
              </div>
              <p className="text-[11px] leading-relaxed">
                {atsData.disclaimer ||
                  'HireMinds AI provides explainable applicant-job alignment diagnostics for human decision support. It does not perform automated screening rejections or predict guaranteed job performance.'}
              </p>
            </div>
          </Card>
        )}
      </div>
    </AppLayout>
  );
};
