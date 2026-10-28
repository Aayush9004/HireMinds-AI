import { api } from './api';
import { Resume } from '../types';

export const resumeService = {
  async upload(file: File): Promise<Resume> {
    const formData = new FormData();
    formData.append('file', file);
    const res = await api.post<Resume>('/resumes/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return res.data;
  },

  async getMyResumes(): Promise<Resume[]> {
    const res = await api.get<any>('/resumes/my-resumes');
    if (res.data && Array.isArray(res.data.items)) {
      return res.data.items;
    }
    return Array.isArray(res.data) ? res.data : [];
  },

  async getResume(resumeId: number): Promise<Resume> {
    const res = await api.get<Resume>(`/resumes/${resumeId}`);
    return res.data;
  },

  async reviewAndCorrect(
    resumeId: number,
    correctedData: { skills?: string[]; experience_years?: number; education_level?: string }
  ): Promise<Resume> {
    const res = await api.put<Resume>(`/resumes/${resumeId}/correct`, correctedData);
    return res.data;
  },

  async deleteResume(resumeId: number): Promise<{ message: string }> {
    const res = await api.delete<{ message: string }>(`/resumes/${resumeId}`);
    return res.data;
  },
};
