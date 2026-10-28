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
  Clock,
  CheckCircle2,
  XCircle,
  Code,
  ListOrdered,
  AlertTriangle,
  ArrowRight,
  ArrowLeft,
  Send,
  Award,
} from 'lucide-react';

export const AssessmentRunnerPage: React.FC = () => {
  const { assessmentId } = useParams<{ assessmentId: string }>();
  const navigate = useNavigate();

  const [assessment, setAssessment] = useState<Assessment | null>(null);
  const [attemptId, setAttemptId] = useState<number | null>(null);
  const [attemptStatus, setAttemptStatus] = useState<string>('not_started');
  const [attemptResult, setAttemptResult] = useState<AssessmentAttempt | null>(null);

  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Active question index
  const [currentIdx, setCurrentIdx] = useState(0);

  // Candidate answers: map of questionId -> { selected_option?: string, code?: string }
  const [userAnswers, setUserAnswers] = useState<Record<number, { selected_option?: string; code?: string }>>({});

  useEffect(() => {
    if (!assessmentId) return;
    initAssessment();
  }, [assessmentId]);

  const initAssessment = async () => {
    setLoading(true);
    setError(null);
    try {
      const id = parseInt(assessmentId!, 10);
      const res = await assessmentService.startAttempt(id);
      setAttemptId(res.attempt_id);
      setAssessment(res.assessment);
      setAttemptStatus(res.status);

      // If already submitted/evaluated, load the results
      if (res.status === 'submitted' || res.status === 'evaluated') {
        const resultData = await assessmentService.getAttemptResult(res.attempt_id);
        setAttemptResult(resultData);
      }
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  const handleSelectOption = (questionId: number, optionKey: string) => {
    setUserAnswers((prev) => ({
      ...prev,
      [questionId]: {
        ...prev[questionId],
        selected_option: optionKey,
      },
    }));
  };

  const handleCodeChange = (questionId: number, code: string) => {
    setUserAnswers((prev) => ({
      ...prev,
      [questionId]: {
        ...prev[questionId],
        code,
      },
    }));
  };

  const handleSubmit = async () => {
    if (!attemptId || !assessment) return;

    if (!window.confirm('Are you ready to submit your assessment? You cannot change your answers after submission.')) {
      return;
    }

    setSubmitting(true);
    setError(null);
    try {
      const formattedAnswers = (assessment.questions || []).map((q) => ({
        question_id: q.id,
        selected_option: userAnswers[q.id]?.selected_option,
        code: userAnswers[q.id]?.code,
      }));

      const res = await assessmentService.submitAttempt(attemptId, formattedAnswers);
      setAttemptResult(res);
      setAttemptStatus(res.status);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <AppLayout>
        <LoadingSpinner fullPage label="Initializing technical assessment sandbox..." />
      </AppLayout>
    );
  }

  if (!assessment) {
    return (
      <AppLayout>
        <div className="text-center py-12">
          <p className="text-slate-400">Assessment not found or expired.</p>
          <Button variant="secondary" className="mt-4" onClick={() => navigate('/candidate/jobs')}>
            Browse Jobs
          </Button>
        </div>
      </AppLayout>
    );
  }

  const questions = assessment.questions || [];
  const currentQ: AssessmentQuestion | undefined = questions[currentIdx];

  // If assessment has been completed/evaluated, show result review
  if (attemptStatus === 'submitted' || attemptStatus === 'evaluated' || attemptResult) {
    const isPassed =
      attemptResult?.score !== undefined && attemptResult.score >= (assessment.passing_score || 60);

    return (
      <AppLayout>
        <div className="max-w-3xl mx-auto space-y-6">
          <Card className="text-center py-8">
            <div className="w-16 h-16 rounded-full bg-slate-800 flex items-center justify-center mx-auto mb-4">
              <Award
                className={`w-8 h-8 ${isPassed ? 'text-emerald-400' : 'text-amber-400'}`}
              />
            </div>
            <h1 className="text-2xl font-bold text-white mb-1">{assessment.title}</h1>
            <p className="text-xs text-slate-400 mb-6">Assessment Evaluation Completed</p>

            <div className="inline-flex items-center gap-6 bg-slate-950 p-5 rounded-2xl border border-slate-800">
              <div>
                <div className="text-xs text-slate-400 uppercase tracking-wider font-semibold">
                  Overall Score
                </div>
                <div className="text-3xl font-extrabold text-white mt-1">
                  {attemptResult?.score !== undefined ? Math.round(attemptResult.score) : 0}%
                </div>
              </div>
              <div className="w-px h-10 bg-slate-800" />
              <div>
                <div className="text-xs text-slate-400 uppercase tracking-wider font-semibold">
                  Passing Threshold
                </div>
                <div className="text-3xl font-extrabold text-slate-300 mt-1">
                  {assessment.passing_score}%
                </div>
              </div>
              <div className="w-px h-10 bg-slate-800" />
              <div>
                <div className="text-xs text-slate-400 uppercase tracking-wider font-semibold">
                  Outcome
                </div>
                <div className="mt-1">
                  <Badge variant={isPassed ? 'success' : 'danger'}>
                    {isPassed ? 'Passed' : 'Needs Practice'}
                  </Badge>
                </div>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4 max-w-md mx-auto mt-6 text-xs text-slate-300">
              <div className="bg-slate-900 p-3 rounded-lg border border-slate-800">
                MCQ Score:{' '}
                <strong className="text-white">
                  {attemptResult?.mcq_score !== undefined
                    ? `${Math.round(attemptResult.mcq_score)}%`
                    : 'N/A'}
                </strong>
              </div>
              <div className="bg-slate-900 p-3 rounded-lg border border-slate-800">
                Coding Score:{' '}
                <strong className="text-white">
                  {attemptResult?.coding_score !== undefined
                    ? `${Math.round(attemptResult.coding_score)}%`
                    : 'N/A'}
                </strong>
              </div>
            </div>

            <div className="flex justify-center gap-3 mt-8">
              <Button variant="secondary" onClick={() => navigate('/candidate/dashboard')}>
                Return to Dashboard
              </Button>
              <Button variant="primary" onClick={() => navigate('/candidate/jobs')}>
                Explore More Jobs
              </Button>
            </div>
          </Card>
        </div>
      </AppLayout>
    );
  }

  // Active testing interface
  const answeredCount = Object.keys(userAnswers).length;
  const progressPct = questions.length > 0 ? (answeredCount / questions.length) * 100 : 0;

  return (
    <AppLayout>
      <div className="max-w-4xl mx-auto space-y-6">
        {/* Top Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-slate-900 border border-slate-800 rounded-xl p-4">
          <div>
            <h1 className="text-lg font-bold text-white">{assessment.title}</h1>
            <div className="flex items-center gap-3 text-xs text-slate-400 mt-1">
              <span>
                Question {currentIdx + 1} of {questions.length}
              </span>
              <span>•</span>
              <span className="flex items-center gap-1">
                <Clock className="w-3.5 h-3.5 text-indigo-400" />
                Duration: {assessment.duration_minutes} min
              </span>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <Button
              variant="success"
              size="sm"
              onClick={handleSubmit}
              isLoading={submitting}
              leftIcon={<Send className="w-4 h-4" />}
            >
              Finish & Submit
            </Button>
          </div>
        </div>

        {error && (
          <Alert variant="danger" onClose={() => setError(null)}>
            {error}
          </Alert>
        )}

        {/* Progress bar */}
        <div className="w-full bg-slate-800 rounded-full h-1.5 overflow-hidden">
          <div
            className="bg-indigo-500 h-full transition-all duration-300"
            style={{ width: `${progressPct}%` }}
          />
        </div>

        {/* Question Area */}
        {currentQ ? (
          <Card className="p-6">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <Badge variant={currentQ.question_type === 'mcq' ? 'primary' : 'purple'}>
                  {currentQ.question_type === 'mcq' ? 'Multiple Choice' : 'Coding Challenge'}
                </Badge>
                {currentQ.skill_tag && <Badge variant="neutral">{currentQ.skill_tag}</Badge>}
                <Badge variant="cyan">{currentQ.difficulty}</Badge>
              </div>
              <span className="text-xs text-slate-400 font-medium">
                {currentQ.points} Points
              </span>
            </div>

            {/* Prompt */}
            <h2 className="text-base font-medium text-slate-100 mb-6 leading-relaxed whitespace-pre-line">
              {currentQ.prompt}
            </h2>

            {/* MCQ Options */}
            {currentQ.question_type === 'mcq' && currentQ.options && (
              <div className="space-y-3">
                {currentQ.options.map((option) => {
                  const isSelected = userAnswers[currentQ.id]?.selected_option === option.key;
                  return (
                    <label
                      key={option.key}
                      onClick={() => handleSelectOption(currentQ.id, option.key)}
                      className={`flex items-start gap-3 p-3.5 rounded-xl border transition-all cursor-pointer ${
                        isSelected
                          ? 'bg-indigo-600/15 border-indigo-500 text-white shadow-sm'
                          : 'bg-slate-950/70 border-slate-800 text-slate-300 hover:border-slate-700 hover:bg-slate-900/60'
                      }`}
                    >
                      <input
                        type="radio"
                        name={`question-${currentQ.id}`}
                        checked={isSelected}
                        onChange={() => handleSelectOption(currentQ.id, option.key)}
                        className="mt-1 text-indigo-600 focus:ring-indigo-500"
                      />
                      <div className="text-sm">
                        <strong className="text-slate-200 mr-2">{option.key}.</strong>
                        {option.text}
                      </div>
                    </label>
                  );
                })}
              </div>
            )}

            {/* Coding Challenge Area */}
            {currentQ.question_type === 'coding' && (
              <div className="space-y-4">
                <div className="bg-slate-950 border border-slate-800 rounded-lg p-3">
                  <div className="flex items-center justify-between text-xs text-slate-400 mb-2 pb-2 border-b border-slate-800">
                    <span className="flex items-center gap-1 font-mono">
                      <Code className="w-3.5 h-3.5 text-indigo-400" /> Language:{' '}
                      {currentQ.language || 'python'}
                    </span>
                    {currentQ.function_name && (
                      <span className="font-mono text-indigo-300">
                        Target function: {currentQ.function_name}()
                      </span>
                    )}
                  </div>
                  <textarea
                    rows={12}
                    value={userAnswers[currentQ.id]?.code ?? currentQ.starter_code ?? ''}
                    onChange={(e) => handleCodeChange(currentQ.id, e.target.value)}
                    placeholder="# Write your solution here..."
                    className="w-full bg-slate-900 text-slate-200 font-mono text-xs p-3 rounded border border-slate-800 focus:outline-none focus:border-indigo-500 resize-y"
                    spellCheck={false}
                  />
                </div>

                {/* Sample Test Cases */}
                {currentQ.sample_test_cases && currentQ.sample_test_cases.length > 0 && (
                  <div className="bg-slate-950/60 border border-slate-800/80 rounded-lg p-3">
                    <div className="text-xs font-semibold text-slate-400 mb-2 uppercase tracking-wider">
                      Sample Test Cases:
                    </div>
                    <div className="space-y-2">
                      {currentQ.sample_test_cases.map((tc, i) => (
                        <div
                          key={i}
                          className="text-xs font-mono bg-slate-900/90 p-2 rounded border border-slate-800 text-slate-300 flex items-center justify-between"
                        >
                          <div>
                            <span className="text-slate-500">Input:</span>{' '}
                            {JSON.stringify(tc.input)}
                          </div>
                          <div>
                            <span className="text-slate-500">Expected:</span>{' '}
                            <span className="text-indigo-300">{JSON.stringify(tc.expected)}</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Navigation buttons */}
            <div className="flex items-center justify-between gap-4 mt-8 pt-4 border-t border-slate-800">
              <Button
                variant="secondary"
                size="sm"
                onClick={() => setCurrentIdx((prev) => Math.max(0, prev - 1))}
                disabled={currentIdx === 0}
                leftIcon={<ArrowLeft className="w-4 h-4" />}
              >
                Previous
              </Button>

              <div className="flex gap-1.5 overflow-x-auto max-w-xs">
                {questions.map((q, idx) => {
                  const isAnswered =
                    userAnswers[q.id]?.selected_option !== undefined ||
                    Boolean(userAnswers[q.id]?.code);
                  const isCurrent = idx === currentIdx;

                  return (
                    <button
                      key={q.id}
                      onClick={() => setCurrentIdx(idx)}
                      className={`w-7 h-7 rounded text-xs font-medium transition-all ${
                        isCurrent
                          ? 'bg-indigo-600 text-white font-bold ring-2 ring-indigo-400 ring-offset-1 ring-offset-slate-900'
                          : isAnswered
                          ? 'bg-emerald-950/80 text-emerald-400 border border-emerald-500/40'
                          : 'bg-slate-800 text-slate-400 hover:text-white'
                      }`}
                    >
                      {idx + 1}
                    </button>
                  );
                })}
              </div>

              <Button
                variant="primary"
                size="sm"
                onClick={() =>
                  setCurrentIdx((prev) => Math.min(questions.length - 1, prev + 1))
                }
                disabled={currentIdx === questions.length - 1}
                rightIcon={<ArrowRight className="w-4 h-4" />}
              >
                Next
              </Button>
            </div>
          </Card>
        ) : (
          <EmptyState
            icon={ListOrdered}
            title="No questions in this assessment"
            description="The assessment doesn't appear to contain any questions."
          />
        )}
      </div>
    </AppLayout>
  );
};
