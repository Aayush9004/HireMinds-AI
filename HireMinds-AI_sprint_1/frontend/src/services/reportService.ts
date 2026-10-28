import { api } from './api';
import { ComprehensiveReport, ResumeDiagnosticReport } from '../types';

export const reportService = {
  // Candidate resume diagnostic
  async getResumeDiagnostic(resumeId: number): Promise<ResumeDiagnosticReport> {
    const res = await api.get<ResumeDiagnosticReport>(`/reports/resume/${resumeId}`);
    return res.data;
  },

  // Candidate unified report
  async getCandidateJobReport(jobId: number, resumeId: number): Promise<ComprehensiveReport> {
    const res = await api.get<ComprehensiveReport>(`/reports/candidate/job/${jobId}/resume/${resumeId}`);
    return res.data;
  },

  // Recruiter applicant report
  async getRecruiterCandidateReport(jobId: number, candidateId: number): Promise<ComprehensiveReport> {
    const res = await api.get<ComprehensiveReport>(`/reports/recruiter/job/${jobId}/candidate/${candidateId}`);
    return res.data;
  },
};
