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
import { assessmentService } from '../../services/assessmentService';
import { jobService } from '../../services/jobService';
import { Assessment, Job } from '../../types';
import { getErrorMessage } from '../../services/api';
import {
  Layers,
  Plus,
  Sparkles,
  Clock,
  Award,
  ArrowRight,
  Code,
  FileQuestion,
  HelpCircle,
} from 'lucide-react';

export const AssessmentManagementPage: React.FC = () => {
  const navigate = useNavigate();

  const [assessments, setAssessments] = useState<Assessment[]>([]);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Generate Modal state
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [selectedJobId, setSelectedJobId] = useState<number | ''>('');
  const [title, setTitle] = useState('');
  const [mcqCount, setMcqCount] = useState<number>(5);
  const [codingCount, setCodingCount] = useState<number>(1);
  const [durationMinutes, setDurationMinutes] = useState<number>(45);
  const [passingScore, setPassingScore] = useState<number>(70);
  const [difficulty, setDifficulty] = useState<string>('mid');
  const [instructions, setInstructions] = useState<string>('');

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [assessmentsData, jobsData] = await Promise.all([
        assessmentService.getMyAssessments(),
        jobService.getMyJobs(),
      ]);
      const assList = Array.isArray(assessmentsData)
        ? assessmentsData
        : assessmentsData?.items || [];
      const jList = Array.isArray(jobsData)
        ? jobsData
        : (jobsData as any)?.items || [];
      setAssessments(assList);
      setJobs(jList);
      if (jList.length > 0 && (!selectedJobId || !jList.some((j: Job) => j.id === selectedJobId))) {
        setSelectedJobId(jList[0].id);
      }
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  const handleGenerateAssessment = async (e: React.FormEvent) => {
    e.preventDefault();
    let jobIdToUse = selectedJobId;
    if (!jobIdToUse && jobs.length > 0) {
      jobIdToUse = jobs[0].id;
      setSelectedJobId(jobs[0].id);
    }

    if (!jobIdToUse) {
      setError('Please select or post a job opening before generating an assessment.');
      return;
    }

    setGenerating(true);
    setError(null);
    try {
      const newAssessment = await assessmentService.generateAssessment({
        job_id: Number(jobIdToUse),
        title: title.trim() || undefined,
        mcq_count: Number(mcqCount),
        coding_count: Number(codingCount),
        duration_minutes: Number(durationMinutes),
        passing_score: Number(passingScore),
        difficulty,
        additional_instructions: instructions.trim() || undefined,
      });

      setIsModalOpen(false);
      setAssessments([newAssessment, ...assessments]);
      navigate(`/recruiter/assessments/${newAssessment.id}`);
    } catch (err) {
      setError(getErrorMessage(err));
      setGenerating(false);
    }
  };

  return (
    <AppLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-white flex items-center gap-2.5">
              <Layers className="w-6 h-6 text-indigo-400" />
              Technical Assessment Studio
            </h1>
            <p className="text-sm text-slate-400 mt-1">
              Generate role-specific technical evaluations (MCQ & Coding sandbox), monitor candidate attempts, and review automated grades.
            </p>
          </div>

          <Button
            variant="primary"
            onClick={() => setIsModalOpen(true)}
            leftIcon={<Sparkles className="w-4 h-4" />}
          >
            Generate AI Assessment
          </Button>
        </div>

        {error && (
          <Alert variant="danger" onClose={() => setError(null)}>
            {error}
          </Alert>
        )}

        {/* Assessments Grid */}
        {loading ? (
          <LoadingSpinner label="Loading assessments..." />
        ) : assessments.length === 0 ? (
          <EmptyState
            icon={Layers}
            title="No assessments generated yet"
            description="Use AI to generate tailored multiple-choice and coding assessments aligned with your job requirements."
            action={
              <Button
                variant="primary"
                onClick={() => setIsModalOpen(true)}
                leftIcon={<Sparkles className="w-4 h-4" />}
              >
                Generate First Assessment
              </Button>
            }
          />
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {assessments.map((item) => {
              const matchedJob = jobs.find((j) => j.id === item.job_id);

              return (
                <Card
                  key={item.id}
                  className="flex flex-col justify-between hover:border-slate-700 transition-colors"
                >
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <Badge variant="cyan">Assessment #{item.id}</Badge>
                      <Badge variant={item.status === 'active' ? 'success' : 'neutral'}>
                        {item.status}
                      </Badge>
                    </div>

                    <h3 className="text-base font-bold text-white mt-1">{item.title}</h3>
                    <p className="text-xs text-slate-400 mt-0.5">
                      Role: {matchedJob?.title || `Job #${item.job_id}`}
                    </p>

                    <div className="grid grid-cols-2 gap-2 mt-4 text-xs text-slate-300">
                      <div className="bg-slate-950/60 p-2.5 rounded-lg border border-slate-800 flex items-center gap-2">
                        <Clock className="w-4 h-4 text-indigo-400 shrink-0" />
                        <div>
                          <div className="text-[10px] text-slate-500">Duration</div>
                          <div className="font-semibold text-slate-200">
                            {item.duration_minutes} min
                          </div>
                        </div>
                      </div>

                      <div className="bg-slate-950/60 p-2.5 rounded-lg border border-slate-800 flex items-center gap-2">
                        <Award className="w-4 h-4 text-emerald-400 shrink-0" />
                        <div>
                          <div className="text-[10px] text-slate-500">Pass Score</div>
                          <div className="font-semibold text-slate-200">
                            {item.passing_score}%
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>

                  <div className="pt-4 mt-4 border-t border-slate-800">
                    <Button
                      variant="secondary"
                      size="sm"
                      className="w-full"
                      onClick={() => navigate(`/recruiter/assessments/${item.id}`)}
                      rightIcon={<ArrowRight className="w-3.5 h-3.5" />}
                    >
                      Inspect Questions & Attempts
                    </Button>
                  </div>
                </Card>
              );
            })}
          </div>
        )}

        {/* Generate Modal */}
        <Modal
          isOpen={isModalOpen}
          onClose={() => setIsModalOpen(false)}
          title="Generate AI Technical Assessment"
          description="Synthesize multiple choice questions and coding challenges tailored to role requirements"
        >
          <form onSubmit={handleGenerateAssessment} className="space-y-4">
            {jobs.length === 0 ? (
              <div className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/20 text-xs text-amber-200 space-y-2">
                <p className="font-semibold text-amber-300">No Job Openings Available</p>
                <p className="text-slate-400 leading-relaxed">
                  Technical assessments are synthesized by AI based on a job's required skills and competencies.
                  You must have at least one active job posting before generating an assessment.
                </p>
                <Button
                  variant="secondary"
                  size="sm"
                  className="mt-2"
                  onClick={() => {
                    setIsModalOpen(false);
                    navigate('/recruiter/jobs/new');
                  }}
                  leftIcon={<Plus className="w-3.5 h-3.5" />}
                >
                  Create Your First Job Posting
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

            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1.5">
                Assessment Title
              </label>
              <input
                type="text"
                placeholder="e.g. Senior Backend Python & System Architecture Test"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-indigo-500"
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1.5">
                  MCQ Count
                </label>
                <input
                  type="number"
                  min={1}
                  max={20}
                  value={mcqCount}
                  onChange={(e) => setMcqCount(Number(e.target.value))}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1.5">
                  Coding Challenges Count
                </label>
                <input
                  type="number"
                  min={0}
                  max={5}
                  value={codingCount}
                  onChange={(e) => setCodingCount(Number(e.target.value))}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-indigo-500"
                />
              </div>
            </div>

            <div className="grid grid-cols-3 gap-3">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1.5">
                  Duration (mins)
                </label>
                <input
                  type="number"
                  min={10}
                  max={180}
                  value={durationMinutes}
                  onChange={(e) => setDurationMinutes(Number(e.target.value))}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1.5">
                  Passing Score (%)
                </label>
                <input
                  type="number"
                  min={1}
                  max={100}
                  value={passingScore}
                  onChange={(e) => setPassingScore(Number(e.target.value))}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1.5">
                  Difficulty
                </label>
                <select
                  value={difficulty}
                  onChange={(e) => setDifficulty(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-indigo-500"
                >
                  <option value="junior">Junior</option>
                  <option value="mid">Mid-Level</option>
                  <option value="senior">Senior</option>
                  <option value="lead">Lead</option>
                </select>
              </div>
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1.5">
                Special Focus or Instructions (Optional)
              </label>
              <textarea
                rows={3}
                value={instructions}
                onChange={(e) => setInstructions(e.target.value)}
                placeholder="e.g. Focus on concurrency, database indexing, and REST API design..."
                className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-xs text-slate-200 focus:outline-none focus:border-indigo-500 resize-none"
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
                isLoading={generating}
                leftIcon={<Sparkles className="w-3.5 h-3.5" />}
              >
                Generate Assessment
              </Button>
            </div>
          </form>
        </Modal>
      </div>
    </AppLayout>
  );
};
