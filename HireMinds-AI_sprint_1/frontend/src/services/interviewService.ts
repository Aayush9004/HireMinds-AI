import { api } from './api';
import {
  InterviewAnswer,
  InterviewEvaluation,
  InterviewQuestion,
  InterviewSession,
} from '../types';

export const interviewService = {
  // Start or resume
  async startInterview(params: {
    job_id: number;
    resume_id?: number;
    target_question_count?: number;
    difficulty?: string;
    focus_areas?: string[];
    title?: string;
  }): Promise<InterviewSession> {
    const res = await api.post<InterviewSession>('/interviews/start', params);
    return res.data;
  },

  // List sessions
  async getSessions(params?: { job_id?: number; status?: string }): Promise<{
    items: InterviewSession[];
    total: number;
  }> {
    const res = await api.get('/interviews', { params });
    return res.data;
  },

  // Get session transcript
  async getSession(sessionId: number): Promise<InterviewSession> {
    const res = await api.get<InterviewSession>(`/interviews/${sessionId}`);
    return res.data;
  },

  // Get active question
  async getCurrentQuestion(sessionId: number): Promise<{
    session_id: number;
    session_status: string;
    current_question: InterviewQuestion | null;
    answered_count: number;
    target_question_count: number;
    is_completed: boolean;
  }> {
    const res = await api.get(`/interviews/${sessionId}/current-question`);
    return res.data;
  },

  // Submit answer
  async submitAnswer(
    sessionId: number,
    questionId: number,
    answerText: string
  ): Promise<{
    answer: InterviewAnswer;
    session_status: string;
    has_next_question: boolean;
    next_question: InterviewQuestion | null;
    is_completed: boolean;
    message: string;
  }> {
    const res = await api.post(`/interviews/${sessionId}/questions/${questionId}/answer`, {
      answer_text: answerText,
    });
    return res.data;
  },

  // Complete session manually
  async completeInterview(sessionId: number): Promise<InterviewSession> {
    const res = await api.post<InterviewSession>(`/interviews/${sessionId}/complete`);
    return res.data;
  },

  // Get evaluation
  async getEvaluation(sessionId: number): Promise<InterviewEvaluation> {
    const res = await api.get<InterviewEvaluation>(`/interviews/${sessionId}/evaluation`);
    return res.data;
  },
};
