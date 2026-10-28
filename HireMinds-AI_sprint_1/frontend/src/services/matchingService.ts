import { api } from './api';
import { AtsCandidateRanking, AtsExplanation, MatchResult } from '../types';

export const matchingService = {
  // Matching Engine
  async computeMatch(resumeId: number, jobId: number): Promise<MatchResult> {
    const res = await api.post<MatchResult>(`/matching/compute/${resumeId}/${jobId}`);
    return res.data;
  },

  async getCachedMatch(resumeId: number, jobId: number): Promise<MatchResult> {
    const res = await api.get<MatchResult>(`/matching/${resumeId}/${jobId}`);
    return res.data;
  },

  // ATS Scoring
  async computeAts(resumeId: number, jobId: number): Promise<AtsExplanation> {
    const res = await api.post<AtsExplanation>(`/ats/compute/${resumeId}/${jobId}`);
    return res.data;
  },

  async getAtsScore(resumeId: number, jobId: number): Promise<AtsExplanation> {
    const res = await api.get<AtsExplanation>(`/ats/${resumeId}/${jobId}`);
    return res.data;
  },

  async getAtsWeights(): Promise<{
    weights: Record<string, number>;
    formula: string;
    missing_data_policy: string;
    limitations: string[];
    disclaimer: string;
  }> {
    const res = await api.get('/ats/weights');
    return res.data;
  },

  async getJobRankings(jobId: number): Promise<{
    job_id: number;
    total_candidates: number;
    rankings: AtsCandidateRanking[];
  }> {
    const res = await api.get(`/ats/rankings/${jobId}`);
    return res.data;
  },
};
