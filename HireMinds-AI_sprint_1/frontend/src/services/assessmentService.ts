import { api } from './api';
import { Assessment, AssessmentAttempt } from '../types';

export const assessmentService = {
  // Recruiter: generate assessment
  async generateAssessment(params: {
    job_id: number;
    resume_id?: number;
    mcq_count: number;
    coding_count: number;
    title?: string;
    duration_minutes: number;
    passing_score: number;
    difficulty?: string;
    additional_instructions?: string;
  }): Promise<Assessment> {
    const res = await api.post<Assessment>('/assessments/generate', params);
    return res.data;
  },

  // Recruiter: list assessments
  async getMyAssessments(): Promise<{ items: Assessment[]; total: number }> {
    const res = await api.get<any>('/assessments');
    if (res.data && Array.isArray(res.data.items)) {
      return res.data;
    }
    if (Array.isArray(res.data)) {
      return { items: res.data, total: res.data.length };
    }
    return { items: [], total: 0 };
  },

  // Recruiter: get full assessment with answers
  async getAssessment(assessmentId: number): Promise<Assessment> {
    const res = await api.get<Assessment>(`/assessments/${assessmentId}`);
    return res.data;
  },

  // Recruiter: get assessment candidate attempts
  async getAssessmentAttempts(assessmentId: number): Promise<{
    assessment_id: number;
    total: number;
    items: AssessmentAttempt[];
  }> {
    const res = await api.get<any>(`/assessments/${assessmentId}/attempts`);
    return {
      assessment_id: res.data?.assessment_id ?? assessmentId,
      total: res.data?.total ?? res.data?.total_attempts ?? (res.data?.items?.length || 0),
      items: res.data?.items ?? res.data?.attempts ?? (Array.isArray(res.data) ? res.data : []),
    };
  },

  // Candidate: start or resume attempt
  async startAttempt(assessmentId: number): Promise<{
    attempt_id: number;
    assessment_id: number;
    title: string;
    duration_minutes: number;
    passing_score?: number;
    status: string;
    started_at: string;
    questions: any[];
    instructions?: string;
    assessment?: Assessment;
  }> {
    const res = await api.post(`/assessments/${assessmentId}/start`);
    return res.data;
  },

  // Candidate: submit answers
  async submitAttempt(
    attemptId: number,
    answers: Array<{
      question_id: number;
      selected_option?: string;
      code?: string;
    }>
  ): Promise<AssessmentAttempt> {
    const res = await api.post<AssessmentAttempt>(`/assessments/attempts/${attemptId}/submit`, {
      answers,
    });
    return res.data;
  },

  // Candidate & Recruiter: view attempt result
  async getAttemptResult(attemptId: number): Promise<AssessmentAttempt> {
    const res = await api.get<AssessmentAttempt>(`/assessments/attempts/${attemptId}/result`);
    return res.data;
  },

  // Candidate: list all available assessments for jobs
  async getCandidateAssessments(): Promise<any[]> {
    const res = await api.get<any[]>('/assessments/candidate/my-assessments');
    return Array.isArray(res.data) ? res.data : [];
  },

  // Candidate/Recruiter: get active assessment for a specific job
  async getAssessmentForJob(jobId: number): Promise<any> {
    const res = await api.get<any>(`/assessments/job/${jobId}`);
    return res.data;
  },

  // Candidate: get attempt and results for an assessment
  async getMyAttemptForAssessment(assessmentId: number): Promise<AssessmentAttempt | null> {
    try {
      const res = await api.get<AssessmentAttempt>(`/assessments/${assessmentId}/my-attempt`);
      return res.data;
    } catch {
      return null;
    }
  },
};
