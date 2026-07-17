import axios from 'axios';
import type { ScoredPosting, GapReport, GapReportRequest, Application, InterviewNote, DashboardMetrics, ApplicationStatus, UserProfile } from '../types';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const apiClient = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Axios interceptor to attach dynamic authorization bearer token from sessionStorage
apiClient.interceptors.request.use((config) => {
  const token = sessionStorage.getItem('joblens_auth_token') || 'default-user-token';
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export const createStreamTicket = async (): Promise<string> => {
  const response = await apiClient.post<{ ticket: string }>('/api/stream/ticket');
  return response.data.ticket;
};

export const getMatches = async (since?: string): Promise<ScoredPosting[]> => {
  const response = await apiClient.get<ScoredPosting[]>('/api/matches', {
    params: since ? { since } : undefined,
  });
  return response.data;
};

export const getRankedPostings = async (): Promise<ScoredPosting[]> => {
  const response = await apiClient.get<ScoredPosting[]>('/api/postings');
  return response.data;
};

export const generateGapReport = async (request: GapReportRequest): Promise<GapReport> => {
  const response = await apiClient.post<GapReport>('/api/gap-report', request);
  return response.data;
};

// --- Career Workspace API ---

export const getApplications = async (): Promise<Application[]> => {
  const response = await apiClient.get<Application[]>('/api/applications');
  return response.data;
};

export const saveApplication = async (job_id: string): Promise<Application> => {
  const response = await apiClient.post<Application>('/api/applications', { job_id });
  return response.data;
};

export const checkApplicationExists = async (job_id: string): Promise<{ exists: boolean; application?: Application }> => {
  const response = await apiClient.get<{ exists: boolean; application?: Application }>(`/api/applications/check/${job_id}`);
  return response.data;
};

export const updateApplicationStatus = async (app_id: string, status: ApplicationStatus): Promise<Application> => {
  const response = await apiClient.patch<Application>(`/api/applications/${app_id}`, { status });
  return response.data;
};

export const deleteApplication = async (app_id: string): Promise<void> => {
  await apiClient.delete(`/api/applications/${app_id}`);
};

export const getNotes = async (app_id: string): Promise<InterviewNote[]> => {
  const response = await apiClient.get<InterviewNote[]>(`/api/applications/${app_id}/notes`);
  return response.data;
};

export const addNote = async (app_id: string, content: string): Promise<InterviewNote> => {
  const response = await apiClient.post<InterviewNote>(`/api/applications/${app_id}/notes`, { content });
  return response.data;
};

export const updateNote = async (note_id: string, content: string): Promise<InterviewNote> => {
  const response = await apiClient.patch<InterviewNote>(`/api/notes/${note_id}`, { content });
  return response.data;
};

export const deleteNote = async (note_id: string): Promise<void> => {
  await apiClient.delete(`/api/notes/${note_id}`);
};

export const getDashboardMetrics = async (): Promise<DashboardMetrics> => {
  const response = await apiClient.get<DashboardMetrics>('/api/dashboard');
  return response.data;
};

export const getMatchDetail = async (match_id: string): Promise<ScoredPosting> => {
  const response = await apiClient.get<ScoredPosting>(`/api/matches/${match_id}`);
  return response.data;
};

export const getProfile = async (): Promise<UserProfile> => {
  const response = await apiClient.get<UserProfile>('/api/profile');
  return response.data;
};

export const updateProfile = async (profile: Partial<UserProfile>): Promise<UserProfile> => {
  const response = await apiClient.put<UserProfile>('/api/profile', profile);
  return response.data;
};

export const QUERY_CONFIG = {
  staleTime: 5 * 60 * 1000, // 5 minutes as recommended
  refetchOnWindowFocus: false,
};
