export interface RawPosting {
  id: string;
  title: string;
  company: string;
  description: string;
  url?: string;
  source?: string;
}

export interface ScoredPosting {
  posting: RawPosting;
  overall_score: number;
  fit_rationale: string;
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
