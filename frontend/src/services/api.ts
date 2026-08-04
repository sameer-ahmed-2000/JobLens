import axios from 'axios';
import { DEFAULT_USER_TOKEN } from '../constants/auth';
import type { ScoredPosting, GapReport, GapReportRequest, Application, InterviewNote, DashboardMetrics, ApplicationStatus, UserProfile, NotificationItem } from '../types';


const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const apiClient = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Axios interceptor to attach dynamic authorization bearer token from localStorage
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('joblens_auth_token') || DEFAULT_USER_TOKEN;
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

export const refetchJobs = async (): Promise<{ status: string; message: string }> => {
  const response = await apiClient.post<{ status: string; message: string }>('/api/refetch');
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

export interface SignupData {
  name: string;
  email: string;
  password: string;
  invite_code: string;
  whatsapp_number?: string;
  title?: string;
  years_experience?: number;
  skills?: string[];
  projects?: Array<{ name: string; description: string; technologies: string[] }>;
}

export const signupUser = async (data: SignupData): Promise<{ user: UserProfile; raw_token: string }> => {
  const response = await apiClient.post<{ user: UserProfile; raw_token: string }>('/api/auth/signup', data);
  return response.data;
};

export const signinUser = async (data: { email: string; password: string }): Promise<{ user: UserProfile; raw_token: string }> => {
  const response = await apiClient.post<{ user: UserProfile; raw_token: string }>('/api/auth/signin', data);
  return response.data;
};

export const getNotifications = async (): Promise<NotificationItem[]> => {
  const response = await apiClient.get<NotificationItem[]>('/api/notifications');
  return response.data;
};

export interface ResumeFile {
  id: string;
  user_id: string;
  resume_id: string | null;
  storage_provider: string;
  storage_key: string;
  filename: string;
  content_type: string;
  size_bytes: number;
  sha256: string;
  processing_status: 'pending' | 'processing' | 'complete' | 'failed';
  processing_attempts: number;
  error_message: string | null;
  uploaded_at: string;
  processed_at: string | null;
}

export interface UploadResponse {
  resume_file_id: string;
  status: 'pending';
  message: string;
}

export const uploadResume = async (file: File): Promise<UploadResponse> => {
  const formData = new FormData();
  formData.append('file', file);
  const response = await apiClient.post<UploadResponse>('/api/resume/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  return response.data;
};

export const getLatestResumeStatus = async (): Promise<ResumeFile | null> => {
  const response = await apiClient.get<ResumeFile | null>('/api/resume/status');
  return response.data;
};

export const getResumeStatus = async (id: string): Promise<ResumeFile> => {
  const response = await apiClient.get<ResumeFile>(`/api/resume/status/${id}`);
  return response.data;
};

export const reprocessResume = async (id: string): Promise<{ status: string; message: string }> => {
  const response = await apiClient.post<{ status: string; message: string }>(`/api/resume/${id}/reprocess`);
  return response.data;
};

export const getResumeDownloadUrl = async (id: string): Promise<{ url: string }> => {
  const response = await apiClient.get<{ url: string }>(`/api/resume/${id}/download`);
  return response.data;
};

export interface ActiveResume {
  id: string;
  user_id: string;
  title: string;
  years_experience: number;
  skills: string[];
  parsed_skills: string[];
  projects: Array<{
    title: string;
    description: string;
    technologies: string[];
  }>;
  raw_text: string;
  is_active: boolean;
  created_at: string;
}

export const getActiveResume = async (): Promise<ActiveResume | null> => {
  try {
    const response = await apiClient.get<ActiveResume>('/api/resume/active');
    return response.data;
  } catch (err: any) {
    if (err.response?.status === 404) {
      return null;
    }
    throw err;
  }
};


export const QUERY_CONFIG = {
  staleTime: 5 * 60 * 1000, // 5 minutes as recommended
  refetchOnWindowFocus: false,
};

