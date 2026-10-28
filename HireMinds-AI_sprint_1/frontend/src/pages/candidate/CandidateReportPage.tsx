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
  Award,
  Sparkles,
  ShieldCheck,
  CheckCircle2,
  AlertTriangle,
  HelpCircle,
  FileText,
  Briefcase,
  Layers,
  TrendingUp,
  Target,
  BookOpen,
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

export const CandidateReportPage: React.FC = () => {
  const { jobId, resumeId } = useParams<{ jobId: string; resumeId: string }>();
  const navigate = useNavigate();

  const [report, setReport] = useState<ComprehensiveReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!jobId || !resumeId) return;
    loadReport();
  }, [jobId, resumeId]);

  const loadReport = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await reportService.getCandidateJobReport(
        Number(jobId),
        Number(resumeId)
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
        <LoadingSpinner fullPage label="Synthesizing multi-signal candidate readiness report..." />
      </AppLayout>
    );
  }

  if (error || !report) {
    return (
      <AppLayout>
        <div className="max-w-2xl mx-auto py-12 text-center space-y-4">
          <Alert variant="danger">{error || 'Could not load readiness report.'}</Alert>
          <Button variant="secondary" onClick={() => navigate('/candidate/jobs')}>
            Back to Positions
          </Button>
        </div>
      </AppLayout>
    );
  }

  // Prepare chart data for readiness dimensions
  const chartData = [
    {
      name: 'Resume Format',
      score: report.resume_analysis?.completeness_score || 0,
      color: '#6366f1',
    },
    {
      name: 'ATS Alignment',
      score: report.ats?.ats_score || 0,
      color: '#8b5cf6',
    },
    {
      name: 'Blended Match',
      score: report.matching?.blended_score
        ? Math.round(report.matching.blended_score * 100)
        : 0,
      color: '#06b6d4',
    },
    {
      name: 'Tech Assessment',
      score: report.assessment?.has_assessment && report.assessment.score !== undefined
        ? Math.round(report.assessment.score)
        : 0,
      color: '#10b981',
    },
    {
      name: 'Mock Interview',
      score: report.mock_interview?.has_interview && report.mock_interview.overall_score !== undefined
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
            onClick={() => navigate(`/candidate/jobs/${jobId}/match`)}
            className="inline-flex items-center gap-1.5 text-xs text-slate-400 hover:text-white transition-colors cursor-pointer mb-2"
          >
            <ArrowLeft className="w-4 h-4" /> Back to ATS match
          </button>
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <h1 className="text-2xl font-bold text-white flex items-center gap-2">
                <Target className="w-6 h-6 text-indigo-400" />
                Comprehensive Candidate Readiness Report
              </h1>
              <p className="text-xs text-slate-400 mt-1">
                Target Role: <strong className="text-slate-200">{report.job_title}</strong> at{' '}
                {report.company_name}
              </p>
            </div>
            <div className="text-right">
              <span className="text-[11px] text-slate-500">
                Generated: {new Date(report.generated_at).toLocaleDateString()}
              </span>
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
                  {plan.readiness_level} Readiness
                </Badge>
                <span className="text-xs text-slate-400">
                  Candidate: {report.candidate_name}
                </span>
              </div>
              <h2 className="text-xl font-bold text-white">Executive Readiness Evaluation</h2>
              <p className="text-xs text-slate-300 max-w-2xl leading-relaxed">
                {plan.executive_summary}
              </p>
            </div>

            <div className="bg-slate-950/80 p-5 rounded-2xl border border-slate-800 text-center shrink-0 min-w-[160px]">
              <div className="text-[11px] font-semibold uppercase text-slate-400 tracking-wider">
                Composite Score
              </div>
              <div className="text-4xl font-extrabold text-white mt-1">
                {Math.round(plan.composite_readiness_score)}
              </div>
              <div className="text-[10px] text-slate-500 mt-0.5">out of 100</div>
            </div>
          </div>
        </Card>

        {/* Readiness Chart by Dimension */}
        <Card>
          <CardHeader
            title="Readiness Dimensions Overview"
            subtitle="Normalized scores across resume quality, ATS fit, matching, assessment, and interview"
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
                  formatter={(value: any) => [`${value}%`, 'Score']}
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

        {/* 4 Pillar Breakdown */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Resume & ATS */}
          <Card>
            <CardHeader
              title={
                <span className="flex items-center gap-1.5 text-sm">
                  <ShieldCheck className="w-4 h-4 text-indigo-400" /> Resume & ATS Breakdown
                </span>
              }
            />
            <div className="space-y-3 text-xs text-slate-300">
              <div className="flex justify-between items-center py-1 border-b border-slate-800">
                <span className="text-slate-400">Resume Completeness:</span>
                <strong className="text-white">
                  {report.resume_analysis.completeness_score}%
                </strong>
              </div>
              <div className="flex justify-between items-center py-1 border-b border-slate-800">
                <span className="text-slate-400">Explainable ATS Score:</span>
                <strong className="text-white">{report.ats?.ats_score ?? 'N/A'}/100</strong>
              </div>
              <div className="flex justify-between items-center py-1 border-b border-slate-800">
                <span className="text-slate-400">Semantic Fit:</span>
                <strong className="text-white">
                  {report.matching?.semantic_score
                    ? `${Math.round(report.matching.semantic_score * 100)}%`
                    : 'N/A'}
                </strong>
              </div>

              {plan.resume_action_items.length > 0 && (
                <div className="pt-2">
                  <div className="font-semibold text-slate-200 mb-1.5">
                    Resume Action Items:
                  </div>
                  <ul className="space-y-1">
                    {plan.resume_action_items.map((item, i) => (
                      <li key={i} className="text-slate-400 flex items-start gap-1.5">
                        <span className="text-indigo-400">•</span>
                        <span>{item}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          </Card>

          {/* Assessment & Mock Interview */}
          <Card>
            <CardHeader
              title={
                <span className="flex items-center gap-1.5 text-sm">
                  <Award className="w-4 h-4 text-emerald-400" /> Assessment & Interview
                </span>
              }
            />
            <div className="space-y-3 text-xs text-slate-300">
              <div className="flex justify-between items-center py-1 border-b border-slate-800">
                <span className="text-slate-400">Technical Assessment:</span>
                <strong className="text-white">
                  {report.assessment?.has_assessment
                    ? `${Math.round(report.assessment.score || 0)}% (${
                        report.assessment.passed ? 'Passed' : 'Needs Practice'
                      })`
                    : 'Not Attempted'}
                </strong>
              </div>
              <div className="flex justify-between items-center py-1 border-b border-slate-800">
                <span className="text-slate-400">AI Mock Interview:</span>
                <strong className="text-white">
                  {report.mock_interview?.has_interview
                    ? `${Math.round(report.mock_interview.overall_score || 0)}/100`
                    : 'Not Completed'}
                </strong>
              </div>

              {plan.interview_coaching_points.length > 0 && (
                <div className="pt-2">
                  <div className="font-semibold text-slate-200 mb-1.5">
                    Interview Coaching Highlights:
                  </div>
                  <ul className="space-y-1">
                    {plan.interview_coaching_points.map((pt, i) => (
                      <li key={i} className="text-slate-400 flex items-start gap-1.5">
                        <span className="text-emerald-400">•</span>
                        <span>{pt}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          </Card>
        </div>

        {/* Priority Skill Gaps & Technical Focus */}
        <Card>
          <CardHeader
            title="Targeted Skill Gap & Study Strategy"
            subtitle="Prioritized recommendations to boost candidate competitive edge for this role"
          />
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <div className="text-xs font-semibold text-rose-400 uppercase tracking-wider mb-2 flex items-center gap-1">
                <AlertTriangle className="w-3.5 h-3.5" /> Priority Skill Gaps
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
                <p className="text-xs text-slate-400 italic">No significant skill gaps detected.</p>
              )}
            </div>

            <div>
              <div className="text-xs font-semibold text-indigo-400 uppercase tracking-wider mb-2 flex items-center gap-1">
                <BookOpen className="w-3.5 h-3.5" /> Recommended Technical Focus
              </div>
              {plan.technical_focus_areas.length > 0 ? (
                <div className="flex flex-wrap gap-1.5">
                  {plan.technical_focus_areas.map((tech, i) => (
                    <span
                      key={i}
                      className="px-2.5 py-1 rounded text-xs bg-indigo-500/10 text-indigo-300 border border-indigo-500/20"
                    >
                      {tech}
                    </span>
                  ))}
                </div>
              ) : (
                <p className="text-xs text-slate-400 italic">Continue general technical review.</p>
              )}
            </div>
          </div>
        </Card>

        {/* Decision Support Disclaimer */}
        <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 text-xs text-slate-400 flex items-start gap-2.5">
          <HelpCircle className="w-4 h-4 text-indigo-400 shrink-0 mt-0.5" />
          <p className="text-[11px] leading-relaxed">
            {report.ats?.disclaimer ||
              'HireMinds AI candidate readiness reports are designed to assist skill development and interview preparation. They do not constitute automated employment decisions or guarantees of job placement.'}
          </p>
        </div>
      </div>
    </AppLayout>
  );
};
