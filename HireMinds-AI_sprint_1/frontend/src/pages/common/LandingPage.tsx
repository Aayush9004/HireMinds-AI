import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { AppLayout } from '../../components/layout/AppLayout';
import { Button } from '../../components/ui/Button';
import { Card } from '../../components/ui/Card';
import { Badge } from '../../components/ui/Badge';
import {
  BrainCircuit,
  Sparkles,
  ShieldCheck,
  CheckCircle2,
  Cpu,
  ArrowRight,
  TrendingUp,
  FileCheck2,
  Terminal,
} from 'lucide-react';

export const LandingPage: React.FC = () => {
  const { isAuthenticated, isCandidate, isRecruiter } = useAuth();
  const navigate = useNavigate();

  const handleCta = () => {
    if (!isAuthenticated) {
      navigate('/register');
    } else if (isCandidate) {
      navigate('/candidate/dashboard');
    } else if (isRecruiter) {
      navigate('/recruiter/dashboard');
    }
  };

  return (
    <AppLayout>
      {/* Hero Section */}
      <div className="relative py-12 md:py-20 text-center max-w-4xl mx-auto">
        <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 text-xs font-medium mb-6">
          <Sparkles className="w-3.5 h-3.5" />
          <span>Next-Generation AI Recruitment & Assessment Platform</span>
        </div>

        <h1 className="text-4xl sm:text-5xl md:text-6xl font-extrabold tracking-tight text-white leading-tight md:leading-none">
          Transparent, Explainable <br className="hidden sm:inline" />
          <span className="text-transparent bg-clip-text bg-gradient-to-r from-indigo-400 via-violet-400 to-cyan-400">
            Candidate Assessment
          </span>
        </h1>

        <p className="mt-6 text-base sm:text-lg text-slate-400 max-w-2xl mx-auto leading-relaxed">
          HireMinds AI empowers candidates with actionable resume diagnostics and adaptive
          AI mock interviews, while equipping recruiters with verifiable ATS rankings and
          zero automated rejections.
        </p>

        <div className="mt-8 flex flex-col sm:flex-row items-center justify-center gap-3">
          <Button
            size="lg"
            variant="primary"
            onClick={handleCta}
            rightIcon={<ArrowRight className="w-4 h-4" />}
            className="w-full sm:w-auto"
          >
            {isAuthenticated ? 'Go to Dashboard' : 'Get Started Free'}
          </Button>
          <Button
            size="lg"
            variant="secondary"
            onClick={() => navigate('/jobs')}
            className="w-full sm:w-auto"
          >
            Browse Open Jobs
          </Button>
        </div>

        {/* Ethical Pill */}
        <div className="mt-8 flex items-center justify-center gap-2 text-xs text-slate-500">
          <ShieldCheck className="w-4 h-4 text-emerald-400" />
          <span>Human-in-the-Loop • 100% Explainable Metrics • Zero Automated Rejection</span>
        </div>
      </div>

      {/* Feature Grid */}
      <div className="py-12 border-t border-slate-900 grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card className="flex flex-col justify-between">
          <div>
            <div className="w-10 h-10 rounded-xl bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 flex items-center justify-center mb-4">
              <FileCheck2 className="w-5 h-5" />
            </div>
            <h3 className="text-base font-semibold text-slate-100 mb-2">
              Explainable ATS & Skill Matching
            </h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              Dual TF-IDF lexical and Sentence Transformer semantic matching. Transparent 5-factor
              weighted scoring with supporting sentence evidence and missing-data renormalisation.
            </p>
          </div>
          <div className="mt-6 pt-4 border-t border-slate-800/80 flex items-center justify-between text-xs text-indigo-400 font-medium">
            <span>5-Factor Rubric</span>
            <span className="text-slate-500">K • E • D • P • M</span>
          </div>
        </Card>

        <Card className="flex flex-col justify-between">
          <div>
            <div className="w-10 h-10 rounded-xl bg-violet-500/10 border border-violet-500/20 text-violet-400 flex items-center justify-center mb-4">
              <BrainCircuit className="w-5 h-5" />
            </div>
            <h3 className="text-base font-semibold text-slate-100 mb-2">
              Adaptive AI Mock Interviews
            </h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              Sequential, one-at-a-time interview sessions grounded in job requirements.
              Dynamic contextual follow-ups and 4-dimension rubric evaluations.
            </p>
          </div>
          <div className="mt-6 pt-4 border-t border-slate-800/80 flex items-center justify-between text-xs text-violet-400 font-medium">
            <span>Powered by Gemini</span>
            <span className="text-slate-500">Adaptive Feedback</span>
          </div>
        </Card>

        <Card className="flex flex-col justify-between">
          <div>
            <div className="w-10 h-10 rounded-xl bg-cyan-500/10 border border-cyan-500/20 text-cyan-400 flex items-center justify-center mb-4">
              <Terminal className="w-5 h-5" />
            </div>
            <h3 className="text-base font-semibold text-slate-100 mb-2">
              Personalized Technical Assessments
            </h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              Job-tailored MCQs and code challenges evaluated deterministically.
              Candidate code runs inside an isolated, unprivileged Docker sandbox.
            </p>
          </div>
          <div className="mt-6 pt-4 border-t border-slate-800/80 flex items-center justify-between text-xs text-cyan-400 font-medium">
            <span>Deterministic Scoring</span>
            <span className="text-slate-500">Sandboxed Execution</span>
          </div>
        </Card>
      </div>

      {/* Two Pillars Section */}
      <div className="py-12 border-t border-slate-900 grid grid-cols-1 lg:grid-cols-2 gap-8">
        <div className="p-6 rounded-2xl bg-gradient-to-b from-indigo-950/20 to-slate-900 border border-indigo-500/20">
          <Badge variant="purple" className="mb-3">
            For Candidates
          </Badge>
          <h3 className="text-xl font-bold text-white mb-2">
            Ace Your Next Technical Role
          </h3>
          <p className="text-xs text-slate-400 mb-6 leading-relaxed">
            Gain complete visibility into how your resume matches job descriptions, take realistic
            mock interviews, and receive personalized skill gap roadmaps.
          </p>
          <ul className="space-y-2.5 text-xs text-slate-300">
            <li className="flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
              <span>Verify and correct automatically extracted resume skills</span>
            </li>
            <li className="flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
              <span>Inspect transparent ATS scoring evidence and missing information</span>
            </li>
            <li className="flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
              <span>Practice role-specific mock interviews with rubric evaluations</span>
            </li>
          </ul>
          <Button
            variant="primary"
            size="sm"
            onClick={() => navigate('/register')}
            className="mt-6"
          >
            Create Candidate Account
          </Button>
        </div>

        <div className="p-6 rounded-2xl bg-gradient-to-b from-cyan-950/20 to-slate-900 border border-cyan-500/20">
          <Badge variant="cyan" className="mb-3">
            For Recruiters
          </Badge>
          <h3 className="text-xl font-bold text-white mb-2">
            Evidence-Based Hiring Decisions
          </h3>
          <p className="text-xs text-slate-400 mb-6 leading-relaxed">
            Manage vacancies, generate job-tailored technical evaluations, and rank candidates
            with explainable audit trails while ensuring ethical non-rejection compliance.
          </p>
          <ul className="space-y-2.5 text-xs text-slate-300">
            <li className="flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-cyan-400 shrink-0" />
              <span>Audit candidate rankings backed by rationale and extracted resume quotes</span>
            </li>
            <li className="flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-cyan-400 shrink-0" />
              <span>Generate customized MCQ and coding assessments via Gemini</span>
            </li>
            <li className="flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-cyan-400 shrink-0" />
              <span>Access comprehensive applicant diagnostics across all assessment stages</span>
            </li>
          </ul>
          <Button
            variant="secondary"
            size="sm"
            onClick={() => navigate('/register')}
            className="mt-6 border-cyan-500/30 text-cyan-300 hover:bg-cyan-950/40"
          >
            Create Recruiter Account
          </Button>
        </div>
      </div>
    </AppLayout>
  );
};
