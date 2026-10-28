import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { AppLayout } from '../../components/layout/AppLayout';
import { Card, CardHeader } from '../../components/ui/Card';
import { Button } from '../../components/ui/Button';
import { Badge } from '../../components/ui/Badge';
import { Modal } from '../../components/ui/Modal';
import { Alert } from '../../components/ui/Alert';
import { LoadingSpinner } from '../../components/ui/LoadingSpinner';
import { EmptyState } from '../../components/ui/EmptyState';
import { interviewService } from '../../services/interviewService';
import { jobService } from '../../services/jobService';
import { resumeService } from '../../services/resumeService';
import { InterviewSession, Job, Resume } from '../../types';
import { getErrorMessage } from '../../services/api';
import {
  Sparkles,
  Plus,
  Play,
  CheckCircle2,
  Clock,
  ArrowRight,
  HelpCircle,
  Award,
  Layers,
} from 'lucide-react';

export const MockInterviewListPage: React.FC = () => {
  const navigate = useNavigate();

  const [sessions, setSessions] = useState<InterviewSession[]>([]);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [resumes, setResumes] = useState<Resume[]>([]);

  const [loading, setLoading] = useState(true);
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // New Interview Modal State
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [selectedJobId, setSelectedJobId] = useState<number | ''>('');
  const [selectedResumeId, setSelectedResumeId] = useState<number | ''>('');
  const [targetCount, setTargetCount] = useState<number>(3);
  const [difficulty, setDifficulty] = useState<string>('mid');
  const [focusAreasInput, setFocusAreasInput] = useState<string>('System Design, Python, Algorithms');

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [sessionsData, jobsData, resumesData] = await Promise.all([
        interviewService.getSessions(),
        jobService.getJobs(),
        resumeService.getMyResumes().catch(() => []),
      ]);
      setSessions(sessionsData.items || []);
      setJobs(jobsData);
      setResumes(resumesData);

      if (jobsData.length > 0) {
        if (!selectedJobId || !jobsData.some((j: Job) => j.id === selectedJobId)) {
          setSelectedJobId(jobsData[0].id);
        }
      }
      if (resumesData.length > 0 && selectedResumeId === '') {
        setSelectedResumeId(resumesData[0].id);
      }
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  const handleStartInterview = async (e: React.FormEvent) => {
    e.preventDefault();
    let jobIdToUse = selectedJobId;
    if (!jobIdToUse && jobs.length > 0) {
      jobIdToUse = jobs[0].id;
      setSelectedJobId(jobs[0].id);
    }

    if (!jobIdToUse) {
      setError('Please select or explore a job position to start the interview.');
      return;
    }

    setStarting(true);
    setError(null);
    try {
      const focusAreas = focusAreasInput
        .split(',')
        .map((s) => s.trim())
        .filter(Boolean);

      const session = await interviewService.startInterview({
        job_id: Number(jobIdToUse),
        resume_id: selectedResumeId ? Number(selectedResumeId) : undefined,
        target_question_count: Math.min(10, Math.max(3, targetCount)),
        difficulty,
        focus_areas: focusAreas.length > 0 ? focusAreas : undefined,
      });

      setIsModalOpen(false);
      navigate(`/candidate/interviews/${session.id}`);
    } catch (err) {
      setError(getErrorMessage(err));
      setStarting(false);
    }
  };

  return (
    <AppLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-white flex items-center gap-2.5">
              <Sparkles className="w-6 h-6 text-indigo-400" />
              AI Mock Interview Studio
            </h1>
            <p className="text-sm text-slate-400 mt-1">
              Practice one-at-a-time interactive interview questions with dynamic follow-ups, rubric scoring, and personalized study feedback.
            </p>
          </div>

          <Button
            variant="primary"
            onClick={() => setIsModalOpen(true)}
            leftIcon={<Plus className="w-4 h-4" />}
          >
            Start Practice Interview
          </Button>
        </div>

        {error && (
          <Alert variant="danger" onClose={() => setError(null)}>
            {error}
          </Alert>
        )}

        {/* Sessions list */}
        {loading ? (
          <LoadingSpinner label="Loading your mock interview sessions..." />
        ) : sessions.length === 0 ? (
          <EmptyState
            icon={Sparkles}
            title="No mock interviews conducted yet"
            description="Start an interactive AI mock interview to test your responses against real job competencies and receive rubric scoring."
            action={
              <Button
                variant="primary"
                onClick={() => setIsModalOpen(true)}
              >
                Launch Your First Interview
              </Button>
            }
          />
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {sessions.map((sess) => {
              const isCompleted = sess.status === 'completed';
              const jobMatch = jobs.find((j) => j.id === sess.job_id);

              return (
                <Card
                  key={sess.id}
                  className="flex flex-col justify-between hover:border-slate-700 transition-colors"
                >
                  <div>
                    <div className="flex items-center justify-between mb-3">
                      <Badge variant={isCompleted ? 'success' : 'purple'}>
                        {isCompleted ? 'Completed' : 'In Progress'}
                      </Badge>
                      <Badge variant="neutral">{sess.difficulty}</Badge>
                    </div>

                    <h3 className="text-base font-bold text-white">
                      {sess.title || jobMatch?.title || `Session #${sess.id}`}
                    </h3>
                    <p className="text-xs text-slate-400 mt-0.5">
                      Target: {jobMatch?.company_name || 'Technical Role'}
                    </p>

                    <div className="mt-4 space-y-2 text-xs text-slate-300">
                      <div className="flex items-center justify-between">
                        <span className="text-slate-400">Questions:</span>
                        <span className="font-medium text-slate-200">
                          {sess.target_question_count} Planned
                        </span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-slate-400">Date:</span>
                        <span className="text-slate-200">
                          {new Date(sess.created_at).toLocaleDateString()}
                        </span>
                      </div>
                    </div>

                    {sess.focus_areas && sess.focus_areas.length > 0 && (
                      <div className="mt-3 flex flex-wrap gap-1">
                        {sess.focus_areas.map((fa, i) => (
                          <span
                            key={i}
                            className="px-1.5 py-0.5 rounded text-[10px] bg-slate-800 text-slate-300"
                          >
                            {fa}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>

                  <div className="pt-4 mt-4 border-t border-slate-800 flex items-center justify-between">
                    {isCompleted ? (
                      <Button
                        variant="secondary"
                        size="sm"
                        className="w-full"
                        onClick={() => navigate(`/candidate/interviews/${sess.id}`)}
                        rightIcon={<ArrowRight className="w-3.5 h-3.5" />}
                      >
                        View Rubric Evaluation
                      </Button>
                    ) : (
                      <Button
                        variant="primary"
                        size="sm"
                        className="w-full"
                        onClick={() => navigate(`/candidate/interviews/${sess.id}`)}
                        rightIcon={<Play className="w-3.5 h-3.5" />}
                      >
                        Resume Interview
                      </Button>
                    )}
                  </div>
                </Card>
              );
            })}
          </div>
        )}

        {/* Start Interview Modal */}
        <Modal
          isOpen={isModalOpen}
          onClose={() => setIsModalOpen(false)}
          title="Configure AI Mock Interview"
          description="Tailor questions to a specific position and choose target competencies"
        >
          <form onSubmit={handleStartInterview} className="space-y-4">
            {jobs.length === 0 ? (
              <div className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/20 text-xs text-amber-200">
                <p className="font-semibold mb-1">No Active Positions Available</p>
                <p className="text-slate-400">
                  Mock interviews require a target job role to tailor technical questions and follow-ups.
                </p>
                <Button
                  variant="secondary"
                  size="sm"
                  className="mt-3"
                  onClick={() => {
                    setIsModalOpen(false);
                    navigate('/jobs');
                  }}
                >
                  Explore Job Positions
                </Button>
              </div>
            ) : (
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1.5">
                  Target Job Position <span className="text-rose-400">*</span>
                </label>
                <select
                  value={selectedJobId}
                  onChange={(e) => setSelectedJobId(Number(e.target.value))}
                  required
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-indigo-500"
                >
                  {jobs.map((j) => (
                    <option key={j.id} value={j.id}>
                      {j.title} — {j.company_name}
                    </option>
                  ))}
                </select>
              </div>
            )}

            {resumes.length > 0 && (
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1.5">
                  Contextual Resume (Optional)
                </label>
                <select
                  value={selectedResumeId}
                  onChange={(e) =>
                    setSelectedResumeId(e.target.value ? Number(e.target.value) : '')
                  }
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-indigo-500"
                >
                  <option value="">No resume (Role only)</option>
                  {resumes.map((r) => (
                    <option key={r.id} value={r.id}>
                      {r.filename}
                    </option>
                  ))}
                </select>
              </div>
            )}

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1.5">
                  Target Question Count
                </label>
                <input
                  type="number"
                  min={3}
                  max={10}
                  value={targetCount}
                  onChange={(e) => setTargetCount(Number(e.target.value))}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-indigo-500"
                />
                <span className="text-[10px] text-slate-500">Between 3 and 10 questions</span>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1.5">
                  Seniority Level
                </label>
                <select
                  value={difficulty}
                  onChange={(e) => setDifficulty(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-indigo-500"
                >
                  <option value="entry">Entry Level</option>
                  <option value="junior">Junior</option>
                  <option value="mid">Mid-Level</option>
                  <option value="senior">Senior</option>
                  <option value="lead">Lead / Staff</option>
                </select>
              </div>
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1.5">
                Focus Areas (comma separated)
              </label>
              <input
                type="text"
                value={focusAreasInput}
                onChange={(e) => setFocusAreasInput(e.target.value)}
                placeholder="e.g. FastAPI, Database Indexing, System Design"
                className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-indigo-500"
              />
            </div>

            <div className="flex justify-end gap-2 pt-2">
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={() => setIsModalOpen(false)}
              >
                Cancel
              </Button>
              <Button
                type="submit"
                variant="primary"
                size="sm"
                isLoading={starting}
              >
                Start Session
              </Button>
            </div>
          </form>
        </Modal>
      </div>
    </AppLayout>
  );
};
