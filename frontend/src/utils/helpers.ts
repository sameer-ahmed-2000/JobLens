import type { ScoredPosting, GapReport, QuickStatsData } from '../types';

export const formatPercentage = (val: number | undefined): string => {
  if (val === undefined || val === null || isNaN(val)) return '0%';
  // If value is <= 1 (like 0.84), multiply by 100
  const pct = val <= 1.0 && val > 0 ? val * 100 : val;
  return `${Math.round(pct)}%`;
};

export const getScoreValue = (val: number | undefined): number => {
  if (val === undefined || val === null || isNaN(val)) return 0;
  return val <= 1.0 && val > 0 ? val * 100 : val;
};

const COMMON_TECH_SKILLS = [
  'FastAPI', 'LangGraph', 'Python', 'RAG', 'AWS', 'Kafka', 'Kubernetes',
  'React', 'TypeScript', 'Docker', 'LangChain', 'SQL', 'LLMs', 'Generative AI',
  'Node.js', 'PostgreSQL', 'Vector DB', 'PyTorch', 'TensorFlow', 'NLP', 'Git'
];

export const extractSkillChips = (rationale: string = '', title: string = '', desc: string = ''): string[] => {
  const combinedText = `${title} ${rationale} ${desc}`.toLowerCase();
  const matchedChips: string[] = [];

  for (const skill of COMMON_TECH_SKILLS) {
    if (combinedText.includes(skill.toLowerCase())) {
      matchedChips.push(skill);
      if (matchedChips.length >= 4) break; // Keep cards clean with max 4 chips
    }
  }

  // Fallback if no specific tech skills matched
  if (matchedChips.length === 0) {
    if (title.toLowerCase().includes('ai') || title.toLowerCase().includes('llm')) {
      matchedChips.push('AI Systems', 'Python');
    } else {
      matchedChips.push('Software Eng', 'System Design');
    }
  }

  return matchedChips;
};

export const calculateQuickStats = (
  postings: ScoredPosting[] = [],
  currentReport?: GapReport | null
): QuickStatsData => {
  if (!postings.length) {
    return {
      topMatch: 0,
      jobsFound: 0,
      avgMatch: 0,
      missingSkillsCount: 0,
    };
  }

  const scores = postings.map(p => getScoreValue(p.overall_score));
  const topMatch = Math.max(...scores);
  const sum = scores.reduce((acc, curr) => acc + curr, 0);
  const avgMatch = Math.round(sum / scores.length);

  // Missing skills count from current active report or default fallback
  let missingSkillsCount = 0;
  if (currentReport && currentReport.gaps) {
    missingSkillsCount = currentReport.gaps.filter(
      g => g.classification.toLowerCase() === 'missing'
    ).length;
  } else {
    // estimate from average gap ratio if no report active yet
    missingSkillsCount = Math.max(1, Math.round((100 - avgMatch) / 8));
  }

  return {
    topMatch: Math.round(topMatch),
    jobsFound: postings.length,
    avgMatch,
    missingSkillsCount,
  };
};

export const getScoreColorClass = (score: number) => {
  const val = getScoreValue(score);
  if (val >= 80) {
    return {
      bg: 'bg-emerald-50',
      text: 'text-emerald-700',
      border: 'border-emerald-200',
      badge: 'bg-emerald-100 text-emerald-800 border-emerald-300',
    };
  }
  if (val >= 70) {
    return {
      bg: 'bg-indigo-50',
      text: 'text-indigo-700',
      border: 'border-indigo-200',
      badge: 'bg-indigo-100 text-indigo-800 border-indigo-300',
    };
  }
  return {
    bg: 'bg-gray-50',
    text: 'text-gray-700',
    border: 'border-gray-200',
    badge: 'bg-gray-100 text-gray-800 border-gray-300',
  };
};
