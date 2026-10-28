import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { AppLayout } from '../../components/layout/AppLayout';
import { Card, CardHeader } from '../../components/ui/Card';
import { Button } from '../../components/ui/Button';
import { Badge } from '../../components/ui/Badge';
import { Alert } from '../../components/ui/Alert';
import { LoadingSpinner } from '../../components/ui/LoadingSpinner';
import { interviewService } from '../../services/interviewService';
import {
  InterviewSession,
  InterviewQuestion,
  InterviewAnswer,
  InterviewEvaluation,
} from '../../types';
import { getErrorMessage } from '../../services/api';
import {
  Sparkles,
  ArrowRight,
  ArrowLeft,
  Send,
  CheckCircle2,
  AlertTriangle,
  HelpCircle,
  Award,
  Layers,
  MessageSquare,
  BookOpen,
  TrendingUp,
} from 'lucide-react';

export const MockInterviewRunnerPage: React.FC = () => {
  const { sessionId } = useParams<{ sessionId: string }>();
  const navigate = useNavigate();

  const [session, setSession] = useState<InterviewSession | null>(null);
  const [currentQuestion, setCurrentQuestion] = useState<InterviewQuestion | null>(null);
  const [answeredCount, setAnsweredCount] = useState(0);
  const [targetCount, setTargetCount] = useState(3);
  const [isCompleted, setIsCompleted] = useState(false);

  // Evaluation (if completed)
  const [evaluation, setEvaluation] = useState<InterviewEvaluation | null>(null);

  // Active answer input
  const [answerText, setAnswerText] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [completing, setCompleting] = useState(false);

  // Immediate rubric feedback for the latest submitted answer
  const [latestAnswerFeedback, setLatestAnswerFeedback] = useState<InterviewAnswer | null>(null);
  const [hasNextQuestion, setHasNextQuestion] = useState(false);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!sessionId) return;
    loadSession();
  }, [sessionId]);

  const loadSession = async () => {
    setLoading(true);
    setError(null);
    try {
      const id = parseInt(sessionId!, 10);
      const sessionData = await interviewService.getSession(id);
      setSession(sessionData);
      setIsCompleted(sessionData.status === 'completed');
      setTargetCount(sessionData.target_question_count || 3);

      if (sessionData.status === 'completed') {
        const evalData = await interviewService.getEvaluation(id).catch(() => null);
        if (evalData) setEvaluation(evalData);
      } else {
        const currentData = await interviewService.getCurrentQuestion(id);
        setCurrentQuestion(currentData.current_question);
        setAnsweredCount(currentData.answered_count);
        setIsCompleted(currentData.is_completed);

        if (currentData.is_completed) {
          const evalData = await interviewService.getEvaluation(id).catch(() => null);
          if (evalData) setEvaluation(evalData);
        }
      }
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  const handleSubmitAnswer = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!sessionId || !currentQuestion || !answerText.trim()) return;

    setSubmitting(true);
    setError(null);
    try {
      const res = await interviewService.submitAnswer(
        Number(sessionId),
        currentQuestion.id,
        answerText.trim()
      );

      setLatestAnswerFeedback(res.answer);
      setHasNextQuestion(res.has_next_question);
      setAnsweredCount((prev) => prev + 1);

      if (res.is_completed) {
        setIsCompleted(true);
        // Load evaluation
        const evalData = await interviewService.getEvaluation(Number(sessionId)).catch(() => null);
        if (evalData) setEvaluation(evalData);
      }
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setSubmitting(false);
    }
  };

  const handleNextQuestion = async () => {
    if (!sessionId) return;
    setLatestAnswerFeedback(null);
    setAnswerText('');
    setLoading(true);
    try {
      const currentData = await interviewService.getCurrentQuestion(Number(sessionId));
      setCurrentQuestion(currentData.current_question);
      setIsCompleted(currentData.is_completed);

      if (currentData.is_completed) {
        const evalData = await interviewService.getEvaluation(Number(sessionId)).catch(() => null);
        if (evalData) setEvaluation(evalData);
      }
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  const handleCompleteEarly = async () => {
    if (!sessionId) return;
    if (!window.confirm('Are you sure you want to finalize and grade the interview now?')) return;

    setCompleting(true);
    setError(null);
    try {
      await interviewService.completeInterview(Number(sessionId));
      await loadSession();
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setCompleting(false);
    }
  };

  if (loading) {
    return (
      <AppLayout>
        <LoadingSpinner fullPage label="Preparing AI interview environment..." />
      </AppLayout>
    );
  }

  if (!session) {
    return (
      <AppLayout>
        <div className="text-center py-12">
          <p className="text-slate-400">Interview session not found.</p>
          <Button
            variant="secondary"
            className="mt-4"
            onClick={() => navigate('/candidate/interviews')}
          >
            Back to Mock Interviews
          </Button>
        </div>
      </AppLayout>
    );
  }

  // COMPLETED VIEW: Full Rubric Evaluation and Transcript
  if (isCompleted || session.status === 'completed') {
    return (
      <AppLayout>
        <div className="max-w-4xl mx-auto space-y-6">
          <div>
            <button
              onClick={() => navigate('/candidate/interviews')}
              className="inline-flex items-center gap-1.5 text-xs text-slate-400 hover:text-white transition-colors cursor-pointer mb-2"
            >
              <ArrowLeft className="w-4 h-4" /> Back to mock interviews
            </button>
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <div>
                <h1 className="text-2xl font-bold text-white flex items-center gap-2">
                  <Award className="w-6 h-6 text-indigo-400" />
                  Interview Evaluation & Rubric Feedback
                </h1>
                <p className="text-xs text-slate-400 mt-1">
                  Session #{session.id}: {session.title || 'Technical Candidate Interview'}
                </p>
              </div>

              <Button
                variant="secondary"
                size="sm"
                onClick={() => navigate('/candidate/interviews')}
              >
                Start Another Session
              </Button>
            </div>
          </div>

          {evaluation ? (
            <>
              {/* Primary Evaluation Scores Card */}
              <Card className="bg-gradient-to-br from-slate-900 via-slate-900 to-indigo-950/40 border-indigo-500/30">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-indigo-300 uppercase tracking-wider flex items-center gap-1.5">
                    <Sparkles className="w-4 h-4 text-indigo-400" />
                    Overall Rubric Performance
                  </span>
                  <Badge variant="purple">Rubric {evaluation.rubric_version || 'v1.0'}</Badge>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-5 gap-4 mt-6 text-center">
                  <div className="md:col-span-1 bg-slate-950/80 p-4 rounded-xl border border-slate-800">
                    <div className="text-[11px] text-slate-400 uppercase tracking-wider">
                      Overall Score
                    </div>
                    <div className="text-4xl font-extrabold text-white mt-1">
                      {Math.round(evaluation.overall_score)}
                    </div>
                    <div className="text-[10px] text-slate-500 mt-0.5">out of 100</div>
                  </div>

                  <div className="bg-slate-950/50 p-3 rounded-xl border border-slate-800">
                    <div className="text-[11px] text-slate-400">Technical Correctness</div>
                    <div className="text-2xl font-bold text-slate-200 mt-1">
                      {Number(evaluation.technical_correctness).toFixed(1)} / 5
                    </div>
                  </div>

                  <div className="bg-slate-950/50 p-3 rounded-xl border border-slate-800">
                    <div className="text-[11px] text-slate-400">Relevance</div>
                    <div className="text-2xl font-bold text-slate-200 mt-1">
                      {Number(evaluation.relevance).toFixed(1)} / 5
                    </div>
                  </div>

                  <div className="bg-slate-950/50 p-3 rounded-xl border border-slate-800">
                    <div className="text-[11px] text-slate-400">Clarity & Structure</div>
                    <div className="text-2xl font-bold text-slate-200 mt-1">
                      {Number(evaluation.clarity).toFixed(1)} / 5
                    </div>
                  </div>

                  <div className="bg-slate-950/50 p-3 rounded-xl border border-slate-800">
                    <div className="text-[11px] text-slate-400">Reasoning & Depth</div>
                    <div className="text-2xl font-bold text-slate-200 mt-1">
                      {Number(evaluation.reasoning).toFixed(1)} / 5
                    </div>
                  </div>
                </div>

                {evaluation.overall_summary && (
                  <p className="text-xs text-slate-300 mt-6 leading-relaxed bg-slate-950/60 p-4 rounded-xl border border-slate-800/80">
                    {evaluation.overall_summary}
                  </p>
                )}
              </Card>

              {/* Strengths and Weaknesses */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <Card className="border-emerald-500/20 bg-emerald-950/10">
                  <h3 className="text-sm font-bold text-emerald-400 mb-3 flex items-center gap-1.5">
                    <CheckCircle2 className="w-4 h-4" /> Demonstrated Strengths
                  </h3>
                  <ul className="space-y-2">
                    {(evaluation.strengths || []).map((s, i) => (
                      <li key={i} className="text-xs text-slate-200 flex items-start gap-2">
                        <span className="text-emerald-400 font-bold">•</span>
                        <span>{s}</span>
                      </li>
                    ))}
                  </ul>
                </Card>

                <Card className="border-rose-500/20 bg-rose-950/10">
                  <h3 className="text-sm font-bold text-rose-400 mb-3 flex items-center gap-1.5">
                    <AlertTriangle className="w-4 h-4" /> Areas for Growth
                  </h3>
                  <ul className="space-y-2">
                    {(evaluation.weaknesses || []).map((w, i) => (
                      <li key={i} className="text-xs text-slate-200 flex items-start gap-2">
                        <span className="text-rose-400 font-bold">•</span>
                        <span>{w}</span>
                      </li>
                    ))}
                  </ul>
                </Card>
              </div>

              {/* Improvement suggestions & Recommended topics */}
              <Card>
                <CardHeader
                  title="Personalized Study & Improvement Plan"
                  subtitle="Specific coaching pointers and technical concepts to focus on"
                />

                <div className="space-y-4">
                  {(evaluation.improvement_suggestions || []).length > 0 && (
                    <div>
                      <div className="text-xs font-semibold text-slate-300 mb-2">
                        Actionable Practice Recommendations:
                      </div>
                      <div className="space-y-1.5">
                        {(evaluation.improvement_suggestions || []).map((sug, i) => (
                          <div
                            key={i}
                            className="text-xs text-slate-300 bg-slate-950/70 p-2.5 rounded-lg border border-slate-800"
                          >
                            💡 {sug}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {(evaluation.recommended_topics || []).length > 0 && (
                    <div>
                      <div className="text-xs font-semibold text-slate-300 mb-2 flex items-center gap-1.5">
                        <BookOpen className="w-3.5 h-3.5 text-indigo-400" />
                        Recommended Study Topics:
                      </div>
                      <div className="flex flex-wrap gap-2">
                        {(evaluation.recommended_topics || []).map((top, i) => (
                          <span
                            key={i}
                            className="px-2.5 py-1 rounded text-xs font-medium bg-indigo-500/15 text-indigo-300 border border-indigo-500/30"
                          >
                            {top}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </Card>

              {/* Legal Notice */}
              <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 text-xs text-slate-400 flex items-start gap-2.5">
                <HelpCircle className="w-4 h-4 text-indigo-400 shrink-0 mt-0.5" />
                <p className="text-[11px] leading-relaxed">
                  {evaluation.disclaimer ||
                    'HireMinds AI mock interview evaluations are generated solely to assist candidate practice and preparation. The system does not claim perfectly objective assessments or reliably predict future job performance.'}
                </p>
              </div>
            </>
          ) : (
            <div className="p-6 bg-slate-900 border border-slate-800 rounded-xl text-center">
              <LoadingSpinner size="sm" label="Grading interview responses against rubric..." />
            </div>
          )}

          {/* Transcript review */}
          {session.questions && session.questions.length > 0 && (
            <Card>
              <CardHeader
                title="Interview Transcript & Response Breakdown"
                subtitle="Review your submitted answers and corresponding rubric feedback"
              />
              <div className="space-y-4">
                {session.questions.map((q, idx) => {
                  const matchingAnswer = session.answers?.find((a) => a.question_id === q.id);

                  return (
                    <div
                      key={q.id}
                      className="bg-slate-950/70 border border-slate-800 rounded-xl p-4 space-y-3"
                    >
                      <div className="flex items-center justify-between text-xs">
                        <div className="flex items-center gap-2">
                          <span className="font-bold text-slate-200">Question #{idx + 1}</span>
                          {q.is_follow_up && (
                            <Badge variant="purple">Follow-up</Badge>
                          )}
                          {q.skill_tag && <Badge variant="neutral">{q.skill_tag}</Badge>}
                        </div>
                        {matchingAnswer && (
                          <span className="text-slate-400 font-medium">
                            Score: <strong className="text-indigo-300">{Math.round(matchingAnswer.overall_score)}/100</strong>
                          </span>
                        )}
                      </div>

                      <div className="text-sm font-medium text-slate-100">{q.prompt}</div>

                      {matchingAnswer && (
                        <div className="mt-2 space-y-2">
                          <div className="text-xs bg-slate-900/90 p-3 rounded-lg border border-slate-800 text-slate-200 whitespace-pre-line">
                            <span className="text-slate-500 font-semibold block mb-1">Your Answer:</span>
                            {matchingAnswer.answer_text}
                          </div>

                          <div className="text-xs bg-indigo-950/20 p-3 rounded-lg border border-indigo-500/20 text-indigo-200">
                            <span className="font-semibold block mb-1">Feedback:</span>
                            {matchingAnswer.feedback}
                          </div>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </Card>
          )}
        </div>
      </AppLayout>
    );
  }

  // ACTIVE INTERVIEW VIEW: One question at a time
  return (
    <AppLayout>
      <div className="max-w-3xl mx-auto space-y-6">
        {/* Header bar */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-slate-900 border border-slate-800 rounded-xl p-4">
          <div>
            <h1 className="text-base font-bold text-white flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-indigo-400" />
              {session.title || 'Interactive AI Mock Interview'}
            </h1>
            <div className="flex items-center gap-3 text-xs text-slate-400 mt-1">
              <span>
                Progress: <strong className="text-slate-200">{answeredCount}</strong> of{' '}
                <strong className="text-slate-200">{targetCount}</strong> questions
              </span>
              <span>•</span>
              <span className="capitalize text-indigo-400 font-medium">
                {session.difficulty} Level
              </span>
            </div>
          </div>

          <Button
            variant="ghost"
            size="sm"
            onClick={handleCompleteEarly}
            isLoading={completing}
            className="text-slate-400 hover:text-white"
          >
            Finalize Early
          </Button>
        </div>

        {error && (
          <Alert variant="danger" onClose={() => setError(null)}>
            {error}
          </Alert>
        )}

        {/* If immediate answer feedback is available, show it before moving on */}
        {latestAnswerFeedback ? (
          <Card className="border-indigo-500/40 bg-gradient-to-br from-slate-900 via-slate-900 to-indigo-950/30">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <CheckCircle2 className="w-5 h-5 text-emerald-400" />
                <h3 className="text-base font-bold text-white">Answer Rubric Evaluation</h3>
              </div>
              <Badge variant="purple">
                Score: {Math.round(latestAnswerFeedback.overall_score)}/100
              </Badge>
            </div>

            <p className="text-xs text-slate-300 leading-relaxed bg-slate-950/70 p-3 rounded-lg border border-slate-800">
              {latestAnswerFeedback.feedback}
            </p>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 mt-4 text-center">
              <div className="bg-slate-950/60 p-2 rounded border border-slate-800">
                <div className="text-[10px] text-slate-400">Correctness</div>
                <div className="text-sm font-bold text-white mt-0.5">
                  {Number(latestAnswerFeedback.technical_correctness).toFixed(1)} / 5
                </div>
              </div>
              <div className="bg-slate-950/60 p-2 rounded border border-slate-800">
                <div className="text-[10px] text-slate-400">Relevance</div>
                <div className="text-sm font-bold text-white mt-0.5">
                  {Number(latestAnswerFeedback.relevance).toFixed(1)} / 5
                </div>
              </div>
              <div className="bg-slate-950/60 p-2 rounded border border-slate-800">
                <div className="text-[10px] text-slate-400">Clarity</div>
                <div className="text-sm font-bold text-white mt-0.5">
                  {Number(latestAnswerFeedback.clarity).toFixed(1)} / 5
                </div>
              </div>
              <div className="bg-slate-950/60 p-2 rounded border border-slate-800">
                <div className="text-[10px] text-slate-400">Reasoning</div>
                <div className="text-sm font-bold text-white mt-0.5">
                  {Number(latestAnswerFeedback.reasoning).toFixed(1)} / 5
                </div>
              </div>
            </div>

            <div className="pt-4 mt-4 border-t border-slate-800 flex justify-end">
              <Button
                variant="primary"
                onClick={handleNextQuestion}
                rightIcon={<ArrowRight className="w-4 h-4" />}
              >
                {hasNextQuestion ? 'Proceed to Next Question' : 'View Full Session Evaluation'}
              </Button>
            </div>
          </Card>
        ) : currentQuestion ? (
          /* Question Form Card */
          <Card className="p-6">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <span className="text-xs font-bold text-indigo-400 uppercase tracking-wider">
                  Question #{answeredCount + 1}
                </span>
                {currentQuestion.is_follow_up && (
                  <Badge variant="purple" size="sm">
                    Follow-up Question
                  </Badge>
                )}
                {currentQuestion.skill_tag && (
                  <Badge variant="neutral" size="sm">
                    {currentQuestion.skill_tag}
                  </Badge>
                )}
              </div>
            </div>

            <h2 className="text-lg font-semibold text-white mb-6 leading-relaxed">
              {currentQuestion.prompt}
            </h2>

            <form onSubmit={handleSubmitAnswer} className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1.5 flex items-center justify-between">
                  <span>Your Answer:</span>
                  <span className="text-slate-500 font-normal">
                    {answerText.length} characters
                  </span>
                </label>
                <textarea
                  rows={7}
                  value={answerText}
                  onChange={(e) => setAnswerText(e.target.value)}
                  placeholder="Type your structured, in-depth technical response here..."
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl p-4 text-sm text-slate-200 focus:outline-none focus:border-indigo-500 placeholder:text-slate-600 resize-y"
                  required
                />
              </div>

              <div className="flex items-center justify-between pt-2">
                <span className="text-[11px] text-slate-400">
                  Tip: Be specific, explain your reasoning, and discuss trade-offs.
                </span>

                <Button
                  type="submit"
                  variant="primary"
                  isLoading={submitting}
                  disabled={!answerText.trim()}
                  rightIcon={<Send className="w-4 h-4" />}
                >
                  Submit Answer for Rubric Feedback
                </Button>
              </div>
            </form>
          </Card>
        ) : (
          <div className="text-center py-12">
            <p className="text-slate-400">No active question found. You may finalize the interview.</p>
            <Button variant="primary" className="mt-4" onClick={handleCompleteEarly}>
              Complete & Grade Interview
            </Button>
          </div>
        )}
      </div>
    </AppLayout>
  );
};
