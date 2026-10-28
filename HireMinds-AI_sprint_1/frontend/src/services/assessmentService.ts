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
    assessment: Assessment;
    status: string;
    duration_minutes: number;
    started_at: string;
    resumed: boolean;
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
};
