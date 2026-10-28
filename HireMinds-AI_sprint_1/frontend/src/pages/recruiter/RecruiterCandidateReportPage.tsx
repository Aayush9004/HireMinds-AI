import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { AppLayout } from '../../components/layout/AppLayout';
import { Card, CardHeader } from '../../components/ui/Card';
import { Button } from '../../components/ui/Button';
import { Badge } from '../../components/ui/Badge';
import { Alert } from '../../components/ui/Alert';
import { LoadingSpinner } from '../../components/ui/LoadingSpinner';
import { reportService } from '../../services/reportService';
import { ComprehensiveReport } from '../../types';
import { getErrorMessage } from '../../services/api';
import {
  ArrowLeft,
  Users,
  ShieldCheck,
  Award,
  Sparkles,
  CheckCircle2,
  AlertTriangle,
  HelpCircle,
  TrendingUp,
  FileText,
  Quote,
  Target,
} from 'lucide-react';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Cell,
} from 'recharts';

export const RecruiterCandidateReportPage: React.FC = () => {
  const { jobId, candidateId } = useParams<{ jobId: string; candidateId: string }>();
  const navigate = useNavigate();

  const [report, setReport] = useState<ComprehensiveReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!jobId || !candidateId) return;
    loadCandidateReport();
  }, [jobId, candidateId]);

  const loadCandidateReport = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await reportService.getRecruiterCandidateReport(
        Number(jobId),
        Number(candidateId)
      );
      setReport(data);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <AppLayout>
        <LoadingSpinner fullPage label="Compiling applicant diagnostic dossier..." />
      </AppLayout>
    );
  }

  if (error || !report) {
    return (
      <AppLayout>
        <div className="max-w-2xl mx-auto py-12 text-center space-y-4">
          <Alert variant="danger">{error || 'Candidate report not accessible.'}</Alert>
          <Button
            variant="secondary"
            onClick={() => navigate(`/recruiter/jobs/${jobId}/applicants`)}
          >
            Back to Applicants
          </Button>
        </div>
      </AppLayout>
    );
  }

  const chartData = [
    {
      name: 'Resume Format',
      score: report.resume_analysis?.completeness_score || 0,
      color: '#6366f1',
    },
    {
      name: 'ATS Score',
      score: report.ats?.ats_score || 0,
      color: '#8b5cf6',
    },
    {
      name: 'Blended Fit',
      score: report.matching?.blended_score
        ? Math.round(report.matching.blended_score * 100)
        : 0,
      color: '#06b6d4',
    },
    {
      name: 'Assessment',
      score:
        report.assessment?.has_assessment && report.assessment.score !== undefined
          ? Math.round(report.assessment.score)
          : 0,
      color: '#10b981',
    },
    {
      name: 'Mock Interview',
      score:
        report.mock_interview?.has_interview &&
        report.mock_interview.overall_score !== undefined
          ? Math.round(report.mock_interview.overall_score)
          : 0,
      color: '#f59e0b',
    },
  ];

  const plan = report.improvement_plan;

  return (
    <AppLayout>
      <div className="max-w-5xl mx-auto space-y-6">
        {/* Navigation */}
        <div>
          <button
            onClick={() => navigate(`/recruiter/jobs/${jobId}/applicants`)}
            className="inline-flex items-center gap-1.5 text-xs text-slate-400 hover:text-white transition-colors cursor-pointer mb-2"
          >
            <ArrowLeft className="w-4 h-4" /> Back to applicant rankings
          </button>
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <h1 className="text-2xl font-bold text-white flex items-center gap-2">
                <Users className="w-6 h-6 text-indigo-400" />
                Candidate Evaluation Dossier: {report.candidate_name}
              </h1>
              <p className="text-xs text-slate-400 mt-1">
                Candidate Email: <strong className="text-slate-200">{report.candidate_email}</strong> • Position: {report.job_title} ({report.company_name})
              </p>
            </div>

            <div className="flex items-center gap-2">
              {report.application_status && (
                <Badge variant="purple" size="md">
                  Status: {report.application_status.replace('_', ' ')}
                </Badge>
              )}
            </div>
          </div>
        </div>

        {/* Executive Readiness Card */}
        <Card className="bg-gradient-to-br from-slate-900 via-slate-900 to-indigo-950/40 border-indigo-500/30">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <Badge
                  variant={
                    plan.composite_readiness_score >= 75
                      ? 'success'
                      : plan.composite_readiness_score >= 50
                      ? 'warning'
                      : 'neutral'
                  }
                >
                  {plan.readiness_level} Readiness Tier
                </Badge>
                <span className="text-xs text-slate-400">
                  Target: {report.job_title}
                </span>
              </div>
              <h2 className="text-xl font-bold text-white">Comprehensive Candidate Synthesis</h2>
              <p className="text-xs text-slate-300 max-w-2xl leading-relaxed">
                {plan.executive_summary}
              </p>
            </div>

            <div className="bg-slate-950/80 p-5 rounded-2xl border border-slate-800 text-center shrink-0 min-w-[160px]">
              <div className="text-[11px] font-semibold uppercase text-slate-400 tracking-wider">
                Readiness Score
              </div>
              <div className="text-4xl font-extrabold text-white mt-1">
                {Math.round(plan.composite_readiness_score)}
              </div>
              <div className="text-[10px] text-slate-500 mt-0.5">out of 100</div>
            </div>
          </div>
        </Card>

        {/* Multi-Signal Performance Chart */}
        <Card>
          <CardHeader
            title="Competency Dimensions Across Modules"
            subtitle="Normalized visual comparison of resume, ATS alignment, technical assessment, and mock interview"
          />
          <div className="h-64 w-full pt-4">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData} margin={{ top: 10, right: 20, left: -10, bottom: 20 }}>
                <XAxis dataKey="name" stroke="#94a3b8" fontSize={11} tickLine={false} />
                <YAxis stroke="#94a3b8" fontSize={11} domain={[0, 100]} tickLine={false} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#0f172a',
                    borderColor: '#334155',
                    borderRadius: '8px',
                    fontSize: '12px',
                    color: '#f8fafc',
                  }}
                  formatter={(val: any) => [`${val}%`, 'Score']}
                />
                <Bar dataKey="score" radius={[6, 6, 0, 0]}>
                  {chartData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>

        {/* 2-Column Module Breakdowns */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Resume & ATS Pillar */}
          <Card>
            <CardHeader
              title={
                <span className="flex items-center gap-1.5 text-sm">
                  <ShieldCheck className="w-4 h-4 text-indigo-400" />
                  Explainable ATS Alignment & Evidence
                </span>
              }
            />
            <div className="space-y-3 text-xs text-slate-300">
              <div className="flex justify-between items-center py-1 border-b border-slate-800">
                <span className="text-slate-400">ATS Composite Score:</span>
                <strong className="text-white font-bold">
                  {report.ats?.ats_score ?? 'N/A'}/100
                </strong>
              </div>
              <div className="flex justify-between items-center py-1 border-b border-slate-800">
                <span className="text-slate-400">Confidence Metric:</span>
                <strong className="text-indigo-300">
                  {report.ats?.confidence || 'Normal'}
                </strong>
              </div>
              <div className="flex justify-between items-center py-1 border-b border-slate-800">
                <span className="text-slate-400">Candidate-Verified Resume:</span>
                <strong className="text-emerald-400">
                  {report.resume_analysis.is_reviewed_by_candidate ? 'Yes (Verified)' : 'Pending'}
                </strong>
              </div>

              {/* Component Scores */}
              {report.ats?.component_scores && (
                <div className="pt-2">
                  <div className="font-semibold text-slate-200 mb-2">Component Scores:</div>
                  <div className="grid grid-cols-2 gap-2 text-[11px]">
                    {Object.entries(report.ats.component_scores).map(([k, v]) => (
                      <div
                        key={k}
                        className="bg-slate-950 p-2 rounded border border-slate-800 flex justify-between"
                      >
                        <span className="capitalize text-slate-400">{k}:</span>
                        <strong className="text-white">
                          {v !== null ? `${Math.round(v)}%` : 'N/A'}
                        </strong>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </Card>

          {/* Assessment & Mock Interview Pillar */}
          <Card>
            <CardHeader
              title={
                <span className="flex items-center gap-1.5 text-sm">
                  <Award className="w-4 h-4 text-emerald-400" />
                  Testing & Interview Rubric
                </span>
              }
            />
            <div className="space-y-3 text-xs text-slate-300">
              <div className="flex justify-between items-center py-1 border-b border-slate-800">
                <span className="text-slate-400">Assessment Status:</span>
                <strong className="text-white">
                  {report.assessment?.has_assessment
                    ? `${Math.round(report.assessment.score || 0)}% — ${
                        report.assessment.passed ? 'PASSED' : 'NEEDS PRACTICE'
                      }`
                    : 'No assessment taken'}
                </strong>
              </div>

              <div className="flex justify-between items-center py-1 border-b border-slate-800">
                <span className="text-slate-400">Mock Interview Score:</span>
                <strong className="text-white">
                  {report.mock_interview?.has_interview
                    ? `${Math.round(report.mock_interview.overall_score || 0)}/100`
                    : 'No mock interview recorded'}
                </strong>
              </div>

              {report.mock_interview?.has_interview && (
                <div className="pt-2 space-y-2">
                  <div className="font-semibold text-slate-200">Demonstrated Strengths:</div>
                  <ul className="space-y-1">
                    {report.mock_interview.strengths.slice(0, 3).map((str, i) => (
                      <li key={i} className="text-slate-400 flex items-start gap-1.5">
                        <span className="text-emerald-400">✓</span>
                        <span>{str}</span>
                      </li>
                    ))}
                  </ul>

                  <div className="font-semibold text-slate-200 pt-1">Growth Opportunities:</div>
                  <ul className="space-y-1">
                    {report.mock_interview.weaknesses.slice(0, 3).map((w, i) => (
                      <li key={i} className="text-slate-400 flex items-start gap-1.5">
                        <span className="text-rose-400">!</span>
                        <span>{w}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          </Card>
        </div>

        {/* Priority Skill Gaps & Coaching Points */}
        <Card>
          <CardHeader
            title="Candidate Skill Gaps & Interview Coaching"
            subtitle="Recruiter insights into candidate technical proficiencies and conversational depth"
          />
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <div className="text-xs font-semibold text-rose-400 uppercase tracking-wider mb-2 flex items-center gap-1">
                <AlertTriangle className="w-3.5 h-3.5" /> Identified Skill Deficits
              </div>
              {plan.priority_skill_gaps.length > 0 ? (
                <div className="flex flex-wrap gap-1.5">
                  {plan.priority_skill_gaps.map((skill, i) => (
                    <span
                      key={i}
                      className="px-2.5 py-1 rounded text-xs bg-rose-500/10 text-rose-300 border border-rose-500/20"
                    >
                      {skill}
                    </span>
                  ))}
                </div>
              ) : (
                <p className="text-xs text-slate-400 italic">No significant skill gaps identified.</p>
              )}
            </div>

            <div>
              <div className="text-xs font-semibold text-indigo-400 uppercase tracking-wider mb-2 flex items-center gap-1">
                <Sparkles className="w-3.5 h-3.5" /> Coaching Highlights
              </div>
              {plan.interview_coaching_points.length > 0 ? (
                <div className="space-y-1.5">
                  {plan.interview_coaching_points.map((pt, i) => (
                    <div
                      key={i}
                      className="text-xs text-slate-300 bg-slate-950/70 p-2.5 rounded-lg border border-slate-800"
                    >
                      • {pt}
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-xs text-slate-400 italic">No specific interview notes logged.</p>
              )}
            </div>
          </div>
        </Card>

        {/* Recruiter Legal / Compliance Disclaimer */}
        <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 text-xs text-slate-400 flex items-start gap-2.5">
          <HelpCircle className="w-4 h-4 text-indigo-400 shrink-0 mt-0.5" />
          <p className="text-[11px] leading-relaxed">
            {report.ats?.disclaimer ||
              'HireMinds AI candidate reports are provided as transparent assistive information for authorized hiring teams. Hiring decisions must always be made by human evaluators.'}
          </p>
        </div>
      </div>
    </AppLayout>
  );
};
