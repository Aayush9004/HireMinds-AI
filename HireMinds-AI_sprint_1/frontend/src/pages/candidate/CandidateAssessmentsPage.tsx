import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { AppLayout } from '../../components/layout/AppLayout';
import { Card, CardHeader } from '../../components/ui/Card';
import { Button } from '../../components/ui/Button';
import { Badge } from '../../components/ui/Badge';
import { Alert } from '../../components/ui/Alert';
import { LoadingSpinner } from '../../components/ui/LoadingSpinner';
import { EmptyState } from '../../components/ui/EmptyState';
import { assessmentService } from '../../services/assessmentService';
import { getErrorMessage } from '../../services/api';
import {
  Layers,
  Clock,
  Award,
  ArrowRight,
  CheckCircle2,
  Play,
  Briefcase,
  Building,
  MapPin,
  Sparkles,
  RotateCcw,
  Code,
} from 'lucide-react';

export const CandidateAssessmentsPage: React.FC = () => {
  const navigate = useNavigate();

  const [assessments, setAssessments] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<'all' | 'pending' | 'completed'>('all');

  useEffect(() => {
    loadAssessments();
  }, []);

  const loadAssessments = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await assessmentService.getCandidateAssessments();
      setAssessments(data);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  const filteredAssessments = assessments.filter((a) => {
    const isCompleted = a.attempt_status === 'evaluated' || a.attempt_status === 'submitted';
    if (filter === 'completed') return isCompleted;
    if (filter === 'pending') return !isCompleted;
    return true;
  });

  const pendingCount = assessments.filter(
    (a) => a.attempt_status !== 'evaluated' && a.attempt_status !== 'submitted'
  ).length;
  const completedCount = assessments.filter(
    (a) => a.attempt_status === 'evaluated' || a.attempt_status === 'submitted'
  ).length;

  return (
    <AppLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-white flex items-center gap-2.5">
              <Layers className="w-6 h-6 text-indigo-400" />
              Technical Assessments
            </h1>
            <p className="text-sm text-slate-400 mt-1">
              Take job-specific technical evaluations (MCQs & automated Python coding sandboxes) created by recruiters.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <Button
              variant="secondary"
              size="sm"
              onClick={() => navigate('/candidate/jobs')}
              leftIcon={<Briefcase className="w-4 h-4 text-slate-400" />}
            >
              Browse Open Jobs
            </Button>
          </div>
        </div>

        {error && (
          <Alert variant="danger" onClose={() => setError(null)}>
            {error}
          </Alert>
        )}

        {/* Filter Tabs */}
        <div className="flex items-center gap-2 border-b border-slate-800 pb-3">
          <button
            onClick={() => setFilter('all')}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
              filter === 'all'
                ? 'bg-indigo-600/15 text-indigo-400 border border-indigo-500/30'
                : 'text-slate-400 hover:text-white hover:bg-slate-800/60'
            }`}
          >
            All Assessments ({assessments.length})
          </button>
          <button
            onClick={() => setFilter('pending')}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
              filter === 'pending'
                ? 'bg-indigo-600/15 text-indigo-400 border border-indigo-500/30'
                : 'text-slate-400 hover:text-white hover:bg-slate-800/60'
            }`}
          >
            Available / In Progress ({pendingCount})
          </button>
          <button
            onClick={() => setFilter('completed')}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
              filter === 'completed'
                ? 'bg-indigo-600/15 text-indigo-400 border border-indigo-500/30'
                : 'text-slate-400 hover:text-white hover:bg-slate-800/60'
            }`}
          >
            Completed ({completedCount})
          </button>
        </div>

        {/* Assessment Cards */}
        {loading ? (
          <LoadingSpinner label="Loading assessments..." />
        ) : filteredAssessments.length === 0 ? (
          <EmptyState
            icon={Layers}
            title={filter === 'all' ? 'No technical assessments available yet' : `No ${filter} assessments`}
            description={
              filter === 'all'
                ? 'When recruiters publish custom MCQ and coding assessments for vacancies, they will appear here.'
                : 'Check back or explore new job openings.'
            }
            action={
              <Button variant="primary" onClick={() => navigate('/candidate/jobs')}>
                Explore Jobs
              </Button>
            }
          />
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {filteredAssessments.map((ass) => {
              const isCompleted = ass.attempt_status === 'evaluated' || ass.attempt_status === 'submitted';
              const isInProgress = ass.attempt_status === 'in_progress';

              return (
                <Card
                  key={ass.id}
                  className="flex flex-col justify-between hover:border-slate-700 transition-all duration-200"
                >
                  <div className="space-y-3">
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <div className="flex items-center gap-2 mb-1">
                          <span className="text-[11px] font-medium text-indigo-400 flex items-center gap-1">
                            <Building className="w-3 h-3" /> {ass.company_name}
                          </span>
                          <span className="text-slate-600">•</span>
                          <span className="text-[11px] text-slate-400 flex items-center gap-1">
                            <MapPin className="w-3 h-3 text-slate-500" /> {ass.location}
                          </span>
                        </div>
                        <h3 className="text-base font-semibold text-white leading-snug">
                          {ass.title}
                        </h3>
                        <p className="text-xs text-slate-300 mt-0.5">
                          For position:{' '}
                          <span className="text-slate-100 font-medium">{ass.job_title}</span>
                        </p>
                      </div>

                      {/* Status Badge */}
                      {isCompleted ? (
                        <Badge variant={ass.passed ? 'success' : 'warning'}>
                          {ass.passed ? 'Passed' : 'Completed'}
                        </Badge>
                      ) : isInProgress ? (
                        <Badge variant="warning">In Progress</Badge>
                      ) : (
                        <Badge variant="cyan">Available</Badge>
                      )}
                    </div>

                    {/* Metadata chips */}
                    <div className="flex flex-wrap items-center gap-2 pt-2 border-t border-slate-800/80 text-[11px] text-slate-400">
                      <span className="inline-flex items-center gap-1 bg-slate-900 px-2 py-0.5 rounded border border-slate-800">
                        <Clock className="w-3 h-3 text-indigo-400" />
                        {ass.duration_minutes} mins
                      </span>
                      <span className="inline-flex items-center gap-1 bg-slate-900 px-2 py-0.5 rounded border border-slate-800">
                        <Code className="w-3 h-3 text-cyan-400" />
                        {ass.question_count} questions
                      </span>
                      <span className="inline-flex items-center gap-1 bg-slate-900 px-2 py-0.5 rounded border border-slate-800">
                        <Award className="w-3 h-3 text-amber-400" />
                        Passing: {ass.passing_score}%
                      </span>
                      {ass.applied && (
                        <span className="inline-flex items-center gap-1 bg-emerald-950/40 text-emerald-300 px-2 py-0.5 rounded border border-emerald-500/30">
                          <CheckCircle2 className="w-3 h-3 text-emerald-400" /> Applied
                        </span>
                      )}
                    </div>

                    {/* Result preview if completed */}
                    {isCompleted && ass.score !== null && (
                      <div className="p-2.5 rounded-lg bg-slate-950 border border-slate-800 flex items-center justify-between text-xs">
                        <span className="text-slate-400">Your Score:</span>
                        <span
                          className={`font-bold ${
                            ass.passed ? 'text-emerald-400' : 'text-amber-400'
                          }`}
                        >
                          {Math.round(ass.score)}% (Threshold: {ass.passing_score}%)
                        </span>
                      </div>
                    )}
                  </div>

                  {/* Action Button */}
                  <div className="mt-4 pt-3 border-t border-slate-800 flex items-center justify-between">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => navigate(`/jobs/${ass.job_id}`)}
                      className="text-slate-400 hover:text-white"
                    >
                      View Position
                    </Button>

                    {isCompleted ? (
                      <Button
                        variant="secondary"
                        size="sm"
                        onClick={() => navigate(`/candidate/assessments/${ass.id}`)}
                        rightIcon={<ArrowRight className="w-3.5 h-3.5" />}
                      >
                        View Results Breakdown
                      </Button>
                    ) : isInProgress ? (
                      <Button
                        variant="primary"
                        size="sm"
                        onClick={() => navigate(`/candidate/assessments/${ass.id}`)}
                        leftIcon={<RotateCcw className="w-3.5 h-3.5" />}
                        className="bg-amber-600 hover:bg-amber-500"
                      >
                        Resume Assessment
                      </Button>
                    ) : (
                      <Button
                        variant="primary"
                        size="sm"
                        onClick={() => navigate(`/candidate/assessments/${ass.id}`)}
                        leftIcon={<Play className="w-3.5 h-3.5" />}
                      >
                        Start Technical Assessment
                      </Button>
                    )}
                  </div>
                </Card>
              );
            })}
          </div>
        )}
      </div>
    </AppLayout>
  );
};
