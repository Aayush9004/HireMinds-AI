import { api } from './api';
import { ApplicationStatus, Job, JobApplication } from '../types';

export const jobService = {
  async getJobs(params?: { search?: string; location?: string; job_type?: string }): Promise<Job[]> {
    const res = await api.get<any>('/jobs', { params });
    if (res.data && Array.isArray(res.data.items)) {
      return res.data.items;
    }
    return Array.isArray(res.data) ? res.data : [];
  },

  async getMyJobs(): Promise<Job[]> {
    const res = await api.get<any>('/jobs/my-postings');
    if (res.data && Array.isArray(res.data.items)) {
      return res.data.items;
    }
    return Array.isArray(res.data) ? res.data : [];
  },

  async getJob(jobId: number): Promise<Job> {
    const res = await api.get<Job>(`/jobs/${jobId}`);
    return res.data;
  },

  async createJob(jobData: Partial<Job>): Promise<Job> {
    const res = await api.post<Job>('/jobs', jobData);
    return res.data;
  },

  async updateJob(jobId: number, jobData: Partial<Job>): Promise<Job> {
    const res = await api.put<Job>(`/jobs/${jobId}`, jobData);
    return res.data;
  },

  async deleteJob(jobId: number): Promise<{ message: string }> {
    const res = await api.delete<{ message: string }>(`/jobs/${jobId}`);
    return res.data;
  },

  async applyToJob(jobId: number, resumeId: number, coverLetter?: string): Promise<JobApplication> {
    const res = await api.post<JobApplication>(`/jobs/${jobId}/apply`, {
      resume_id: resumeId,
      cover_letter: coverLetter,
    });
    return res.data;
  },

  async getMyApplications(): Promise<JobApplication[]> {
    const res = await api.get<any>('/jobs/applications/my-applications');
    if (res.data && Array.isArray(res.data.items)) {
      return res.data.items;
    }
    return Array.isArray(res.data) ? res.data : [];
  },

  async getJobApplications(jobId: number): Promise<JobApplication[]> {
    const res = await api.get<any>(`/jobs/${jobId}/applications`);
    if (res.data && Array.isArray(res.data.items)) {
      return res.data.items;
    }
    return Array.isArray(res.data) ? res.data : [];
  },

  async updateApplicationStatus(applicationId: number, newStatus: ApplicationStatus, notes?: string): Promise<JobApplication> {
    const res = await api.patch<JobApplication>(`/jobs/applications/${applicationId}/status`, {
      status: newStatus,
      recruiter_notes: notes,
    });
    return res.data;
  },
};
