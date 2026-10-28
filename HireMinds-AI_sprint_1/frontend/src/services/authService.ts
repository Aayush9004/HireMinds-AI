import { api } from './api';
import { AuthResponse, User, UserRole } from '../types';

export const authService = {
  async register(email: string, password: string, fullName: string, role: UserRole): Promise<User> {
    const res = await api.post<User>('/auth/register', {
      email,
      password,
      full_name: fullName,
      role,
    });
    return res.data;
  },

  async login(email: string, password: string): Promise<AuthResponse> {
    const res = await api.post<AuthResponse>('/auth/login', {
      email,
      password,
    });
    return res.data;
  },

  async getMe(): Promise<User> {
    const res = await api.get<User>('/auth/me');
    return res.data;
  },
};
