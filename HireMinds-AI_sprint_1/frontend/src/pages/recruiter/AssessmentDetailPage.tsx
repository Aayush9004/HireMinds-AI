import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { AppLayout } from '../../components/layout/AppLayout';
import { Card, CardHeader } from '../../components/ui/Card';
import { Button } from '../../components/ui/Button';
import { Badge } from '../../components/ui/Badge';
import { Alert } from '../../components/ui/Alert';
import { LoadingSpinner } from '../../components/ui/LoadingSpinner';
import { EmptyState } from '../../components/ui/EmptyState';
import { assessmentService } from '../../services/assessmentService';
import { Assessment, AssessmentAttempt, AssessmentQuestion } from '../../types';
import { getErrorMessage } from '../../services/api';
import {
  Layers,
  ArrowLeft,
  Clock,
  Award,
  CheckCircle2,
  XCircle,
  Code,
  Users,
  BookOpen,
  FileQuestion,
} from 'lucide-react';

export const AssessmentDetailPage: React.FC = () => {
  const { assessmentId } = useParams<{ assessmentId: string }>();
  const navigate = useNavigate();

  const [assessment, setAssessment] = useState<Assessment | null>(null);
  const [attempts, setAttempts] = useState<AssessmentAttempt[]>([]);
  const [activeTab, setActiveTab] = useState<'questions' | 'attempts'>('questions');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!assessmentId) return;
    loadAssessmentDetails();
  }, [assessmentId]);

  const loadAssessmentDetails = async () => {
    setLoading(true);
    setError(null);
    try {
      const id = parseInt(assessmentId!, 10);
      const [assessmentData, attemptsData] = await Promise.all([
        assessmentService.getAssessment(id),
        assessmentService.getAssessmentAttempts(id).catch(() => ({
          assessment_id: id,
          total: 0,
          items: [],
        })),
      ]);
      setAssessment(assessmentData);
      setAttempts((attemptsData as any).items || (attemptsData as any).attempts || []);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <AppLayout>
        <LoadingSpinner fullPage label="Loading assessment specifications and attempts..." />
      </AppLayout>
    );
  }

  if (!assessment) {
    return (
      <AppLayout>
        <div className="text-center py-12">
          <p className="text-slate-400">Assessment not found.</p>
          <Button
            variant="secondary"
            className="mt-4"
            onClick={() => navigate('/recruiter/assessments')}
          >
            Back to Assessments
          </Button>
        </div>
      </AppLayout>
    );
  }

  const questions: AssessmentQuestion[] = assessment.questions || [];

  return (
    <AppLayout>
      <div className="space-y-6">
        {/* Header */}
        <div>
          <button
            onClick={() => navigate('/recruiter/assessments')}
            className="inline-flex items-center gap-1.5 text-xs text-slate-400 hover:text-white transition-colors cursor-pointer mb-2"
          >
            <ArrowLeft className="w-4 h-4" /> Back to assessments
          </button>
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-2xl font-bold text-white flex items-center gap-2">
                  <Layers className="w-6 h-6 text-indigo-400" />
                  {assessment.title}
                </h1>
                <Badge variant={assessment.status === 'active' ? 'success' : 'neutral'}>
                  {assessment.status}
                </Badge>
              </div>
              <div className="flex flex-wrap items-center gap-4 text-xs text-slate-400 mt-1">
                <span>Assessment #{assessment.id}</span>
                <span>•</span>
                <span className="flex items-center gap-1">
                  <Clock className="w-3.5 h-3.5 text-indigo-400" />
                  {assessment.duration_minutes} Minutes
                </span>
                <span>•</span>
                <span className="flex items-center gap-1">
                  <Award className="w-3.5 h-3.5 text-emerald-400" />
                  {assessment.passing_score}% Passing Threshold
                </span>
                <span>•</span>
                <span>{questions.length} Questions</span>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <div className="flex bg-slate-900 border border-slate-800 rounded-lg p-1">
                <button
                  onClick={() => setActiveTab('questions')}
                  className={`px-3 py-1 text-xs font-medium rounded-md transition-colors cursor-pointer ${
                    activeTab === 'questions'
                      ? 'bg-indigo-600 text-white'
                      : 'text-slate-400 hover:text-white'
                  }`}
                >
                  Questions & Solutions ({questions.length})
                </button>
                <button
                  onClick={() => setActiveTab('attempts')}
                  className={`px-3 py-1 text-xs font-medium rounded-md transition-colors cursor-pointer ${
                    activeTab === 'attempts'
                      ? 'bg-indigo-600 text-white'
                      : 'text-slate-400 hover:text-white'
                  }`}
                >
                  Candidate Attempts ({attempts.length})
                </button>
              </div>
            </div>
          </div>
        </div>

        {error && (
          <Alert variant="danger" onClose={() => setError(null)}>
            {error}
          </Alert>
        )}

        {/* TAB 1: Questions & Solution Keys */}
        {activeTab === 'questions' && (
          <div className="space-y-4">
            {questions.map((q, idx) => (
              <Card key={q.id} className="p-5 space-y-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-bold text-slate-200">Question #{idx + 1}</span>
                    <Badge variant={q.question_type === 'mcq' ? 'primary' : 'purple'}>
                      {q.question_type === 'mcq' ? 'Multiple Choice' : 'Coding Challenge'}
                    </Badge>
                    {q.skill_tag && <Badge variant="neutral">{q.skill_tag}</Badge>}
                    <Badge variant="cyan">{q.difficulty}</Badge>
                  </div>
                  <span className="text-xs text-indigo-300 font-semibold">{q.points} Points</span>
                </div>

                <div className="text-sm font-medium text-slate-100 whitespace-pre-line leading-relaxed">
                  {q.prompt}
                </div>

                {/* MCQ Options with marked correct answer */}
                {q.question_type === 'mcq' && q.options && (
                  <div className="space-y-2 pt-2">
                    {q.options.map((opt) => {
                      const isCorrect = opt.key === q.correct_answer;
                      return (
                        <div
                          key={opt.key}
                          className={`p-3 rounded-lg text-xs flex items-start gap-2 border ${
                            isCorrect
                              ? 'bg-emerald-950/30 border-emerald-500/40 text-emerald-200 font-medium'
                              : 'bg-slate-950/60 border-slate-800 text-slate-300'
                          }`}
                        >
                          <span className="font-bold">{opt.key}.</span>
                          <span>{opt.text}</span>
                          {isCorrect && (
                            <span className="ml-auto text-emerald-400 font-bold shrink-0">
                              ✓ Correct Answer
                            </span>
                          )}
                        </div>
                      );
                    })}
                  </div>
                )}

                {/* Coding Details */}
                {q.question_type === 'coding' && (
                  <div className="space-y-3 pt-2">
                    {q.starter_code && (
                      <div className="bg-slate-950 p-3 rounded-lg border border-slate-800">
                        <div className="text-[10px] text-slate-400 font-mono mb-1">Starter Template:</div>
                        <pre className="text-xs font-mono text-slate-300 overflow-x-auto">
                          {q.starter_code}
                        </pre>
                      </div>
                    )}

                    {q.sample_test_cases && q.sample_test_cases.length > 0 && (
                      <div className="bg-slate-950/70 p-3 rounded-lg border border-slate-800 text-xs">
                        <div className="text-[10px] text-slate-400 font-semibold mb-2">
                          Sample Test Cases:
                        </div>
                        <div className="space-y-1.5 font-mono text-[11px]">
                          {q.sample_test_cases.map((tc, i) => (
                            <div key={i} className="flex gap-4 text-slate-300">
                              <span>Input: {JSON.stringify(tc.input)}</span>
                              <span className="text-indigo-400">
                                Expected: {JSON.stringify(tc.expected)}
                              </span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}

                {/* Explanation */}
                {q.explanation && (
                  <div className="bg-indigo-950/20 border border-indigo-500/20 rounded-lg p-3 text-xs text-indigo-200">
                    <strong className="block mb-0.5 text-indigo-300">Explanation & Rubric:</strong>
                    {q.explanation}
                  </div>
                )}
              </Card>
            ))}
          </div>
        )}

        {/* TAB 2: Candidate Attempts */}
        {activeTab === 'attempts' && (
          <Card>
            <CardHeader
              title="Candidate Test Submissions"
              subtitle="Logged attempts, automated scores, and passing records"
            />

            {attempts.length === 0 ? (
              <EmptyState
                icon={Users}
                title="No attempts recorded yet"
                description="When candidates begin or submit this assessment, their scores will be logged here."
              />
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse text-xs">
                  <thead>
                    <tr className="border-b border-slate-800 text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                      <th className="py-3 px-3">Attempt ID</th>
                      <th className="py-3 px-3">Candidate ID</th>
                      <th className="py-3 px-3">Status</th>
                      <th className="py-3 px-3">Overall Score</th>
                      <th className="py-3 px-3">MCQ / Coding</th>
                      <th className="py-3 px-3">Outcome</th>
                      <th className="py-3 px-3">Started At</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60">
                    {attempts.map((att: any) => {
                      const attId = att.attempt_id ?? att.id;
                      const score = att.score !== undefined && att.score !== null ? Math.round(att.score) : null;
                      const isPassed =
                        score !== null && score >= (assessment.passing_score || 60);

                      return (
                        <tr key={attId} className="hover:bg-slate-800/40 transition-colors">
                          <td className="py-3 px-3 font-mono text-slate-300">#{attId}</td>
                          <td className="py-3 px-3 font-semibold text-slate-100">
                            {att.candidate_name || `Candidate #${att.candidate_id}`}
                          </td>
                          <td className="py-3 px-3 capitalize">
                            <Badge variant={att.status === 'evaluated' ? 'primary' : 'neutral'}>
                              {att.status.replace('_', ' ')}
                            </Badge>
                          </td>
                          <td className="py-3 px-3">
                            <span className="text-sm font-bold text-white">
                              {score !== null ? `${score}%` : 'Pending'}
                            </span>
                          </td>
                          <td className="py-3 px-3 text-slate-400">
                            MCQ: {att.mcq_score !== undefined ? `${Math.round(att.mcq_score)}%` : '—'} •{' '}
                            Coding:{' '}
                            {att.coding_score !== undefined
                              ? `${Math.round(att.coding_score)}%`
                              : '—'}
                          </td>
                          <td className="py-3 px-3">
                            {score !== null ? (
                              <Badge variant={isPassed ? 'success' : 'danger'}>
                                {isPassed ? 'Passed' : 'Failed'}
                              </Badge>
                            ) : (
                              <span className="text-slate-500">—</span>
                            )}
                          </td>
                          <td className="py-3 px-3 text-slate-400">
                            {new Date(att.started_at).toLocaleDateString()}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </Card>
        )}
      </div>
    </AppLayout>
  );
};
