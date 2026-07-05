import axios from 'axios';
import type { ScoredPosting, GapReport, GapReportRequest } from '../types';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const apiClient = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const getRankedPostings = async (): Promise<ScoredPosting[]> => {
  const response = await apiClient.get<ScoredPosting[]>('/api/postings');
  return response.data;
};

export const generateGapReport = async (request: GapReportRequest): Promise<GapReport> => {
  const response = await apiClient.post<GapReport>('/api/gap-report', request);
  return response.data;
};

export const QUERY_CONFIG = {
  staleTime: 5 * 60 * 1000, // 5 minutes as recommended
  refetchOnWindowFocus: false,
};
