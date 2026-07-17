export interface RawPosting {
  id: string;
  title: string;
  company: string;
  description: string;
  url?: string;
  source?: string;
}

export interface ScoredPosting {
  id: string;
  posting: RawPosting;
  overall_score: number;
  fit_rationale: string;
  status?: string;
}

export interface SkillGap {
  skill: string;
  missing_skill: string;
  classification: 'have' | 'partial' | 'missing' | string;
  importance: 'required' | 'nice_to_have' | 'preferred' | string;
  suggestion: string;
  bridge_suggestion: string;
}

export interface GapReport {
  job_title: string;
  company: string;
  match_score: number;
  confidence_score?: number;
  confidence_reasoning?: string;
  gaps: SkillGap[];
  overall_recommendation: string;
  overall_fit_summary?: string;
}

export interface GapReportRequest {
  job_description?: string;
  jd_text?: string;
  posting_url?: string;
}

export type SortOption = 'score_desc' | 'company_asc';

export interface FilterState {
  minMatch: number; // 0, 0.7, 0.8, 0.9
  source: string;   // 'All' or specific source name
  sort: SortOption;
}

export interface QuickStatsData {
  topMatch: number;
  jobsFound: number;
  avgMatch: number;
  missingSkillsCount: number;
}

export type ApplicationStatus =
  | 'Saved'
  | 'Applied'
  | 'Assessment'
  | 'Online Assessment'
  | 'Technical Interview'
  | 'Manager Interview'
  | 'HR Interview'
  | 'Offer'
  | 'Rejected'
  | 'Withdrawn';

export interface Application {
  id: string;
  user_id: string;
  job_id: string;
  resume_id?: string;
  job_title: string;
  company: string;
  job_url?: string;
  status: ApplicationStatus;
  notes?: string;
  match_score?: number;
  confidence_score?: number;
  created_at: string;
  updated_at: string;
}

export interface InterviewNote {
  id: string;
  application_id: string;
  content: string;
  created_at: string;
  updated_at?: string;
}

export interface DashboardMetrics {
  saved: number;
  applied: number;
  assessments: number;
  interviews: number;
  offers: number;
  rejected: number;
  withdrawn: number;
  total: number;
  success_rate: number;
  average_match_score: number;
  average_confidence: number;
  avg_days_in_pipeline: number;
}

export interface UserProfile {
  id: string;
  name: string;
  email: string;
  whatsapp_number?: string;
  notify_threshold: number;
  display_threshold: number;
}

