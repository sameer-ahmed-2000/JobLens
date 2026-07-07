import React from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import type { GapReport as GapReportType, ScoredPosting } from '../types';
import { checkApplicationExists, saveApplication } from '../services/api';
import { ConfidenceCard } from './ConfidenceCard';
import { SkillBadge } from './SkillBadge';
import { GapReportSkeleton } from './SkeletonLoader';
import { ErrorBanner } from './ErrorBanner';
import { EmptyState } from './EmptyState';
import { BuildingIcon, ExternalLinkIcon, SparklesIcon, CheckCircleIcon } from './icons';

interface GapReportProps {
  report?: GapReportType | null;
  isLoading: boolean;
  isError: boolean;
  error?: Error | null;
  selectedPosting?: ScoredPosting | null;
  onRetry?: () => void;
}

export const GapReport: React.FC<GapReportProps> = ({
  report,
  isLoading,
  isError,
  error,
  selectedPosting,
  onRetry,
}) => {
  const queryClient = useQueryClient();

  // Check if saved
  const { data: saveCheck } = useQuery({
    queryKey: ['check_saved', selectedPosting?.posting.id],
    queryFn: () => checkApplicationExists(selectedPosting!.posting.id),
    enabled: !!selectedPosting?.posting.id,
    staleTime: Infinity,
  });

  // Save mutation
  const saveMutation = useMutation({
    mutationFn: () => saveApplication(selectedPosting!.posting.id),
    onSuccess: () => {
      if (selectedPosting) {
        queryClient.invalidateQueries({ queryKey: ['check_saved', selectedPosting.posting.id] });
      }
      queryClient.invalidateQueries({ queryKey: ['applications'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard_metrics'] });
    },
  });
  if (isLoading) {
    return <GapReportSkeleton />;
  }

  if (isError) {
    return (
      <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-6">
        <ErrorBanner
          title="Report Generation Failed"
          message={error?.message || 'Unable to generate gap report. Please try again.'}
          onRetry={onRetry}
        />
      </div>
    );
  }

  if (!report && !selectedPosting) {
    return <EmptyState type="report" />;
  }

  if (!report) {
    return <EmptyState type="report" title="Generating AI Report..." message="Please wait while LangGraph analyzes your skills against this job description." />;
  }

  const { job_title, company, gaps = [], overall_fit_summary, overall_recommendation } = report;
  const summaryText = overall_fit_summary || overall_recommendation;

  // Group skills (Refinement #4)
  const strongMatches = gaps.filter((g) => g.classification === 'have');
  const partialMatches = gaps.filter((g) => g.classification === 'partial');
  const missingSkills = gaps.filter((g) => g.classification === 'missing');

  const handleOpenOriginal = () => {
    if (selectedPosting?.posting.url) {
      window.open(selectedPosting.posting.url, '_blank', 'noopener,noreferrer');
    }
  };

  return (
    <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-6 space-y-6 max-h-[800px] overflow-y-auto pr-2">
      
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-gray-100 pb-4">
        <div>
          <h2 className="text-xl font-extrabold text-gray-900">{job_title}</h2>
          <div className="flex items-center gap-1.5 text-sm text-gray-600 font-medium mt-1">
            <BuildingIcon size={16} className="text-gray-400" />
            <span>{company}</span>
            {selectedPosting?.posting.source && (
              <span className="bg-gray-100 text-gray-600 px-2 py-0.5 rounded text-xs ml-1">
                {selectedPosting.posting.source}
              </span>
            )}
          </div>
        </div>

        <div className="flex items-center gap-3 shrink-0 self-start sm:self-center">
          {selectedPosting?.posting.id && (
            saveCheck?.exists ? (
              <span className="inline-flex items-center gap-1.5 px-3.5 py-2 bg-emerald-50 text-emerald-700 rounded-xl text-xs font-bold border border-emerald-100">
                <CheckCircleIcon size={14} />
                <span>Saved to Workspace</span>
              </span>
            ) : (
              <button
                type="button"
                onClick={() => !saveMutation.isPending && saveMutation.mutate()}
                disabled={saveMutation.isPending}
                className="inline-flex items-center gap-1.5 px-3.5 py-2 bg-gray-100 text-gray-700 hover:bg-gray-200 hover:text-indigo-700 rounded-xl text-xs font-bold transition-colors cursor-pointer focus:outline-none disabled:opacity-50"
              >
                <span>⭐ {saveMutation.isPending ? 'Saving...' : 'Save Job'}</span>
              </button>
            )
          )}

          {selectedPosting?.posting.url && (
            <button
              type="button"
              onClick={handleOpenOriginal}
              className="inline-flex items-center gap-1.5 px-3.5 py-2 bg-indigo-50 text-indigo-700 hover:bg-indigo-100 rounded-xl text-xs font-bold transition-colors cursor-pointer focus:outline-none"
            >
              <span>Open Original Job</span>
              <ExternalLinkIcon size={14} />
            </button>
          )}
        </div>
      </div>

      {/* Confidence Card (Refinement #5) */}
      <ConfidenceCard report={report} />

      {/* AI Fit Summary Narrative */}
      {summaryText && (
        <div className="bg-gradient-to-r from-blue-50/80 via-indigo-50/80 to-purple-50/80 rounded-xl p-4 border border-indigo-100 shadow-2xs">
          <div className="flex items-center space-x-2 text-indigo-900 font-bold text-xs uppercase tracking-wider mb-2">
            <SparklesIcon size={16} className="text-indigo-600" />
            <span>AI Career Advisor Executive Summary</span>
          </div>
          <p className="text-sm text-gray-800 leading-relaxed font-medium">
            {summaryText}
          </p>
        </div>
      )}

      {/* Grouped Skills List (Refinement #4) */}
      <div className="space-y-6 pt-2">
        
        {/* Strong Matches */}
        {strongMatches.length > 0 && (
          <div>
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-bold text-emerald-800 flex items-center gap-1.5">
                <span>✅ Strong Matches</span>
                <span className="bg-emerald-100 text-emerald-800 text-xs px-2 py-0.5 rounded-full font-extrabold">
                  {strongMatches.length}
                </span>
              </h3>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {strongMatches.map((gap, idx) => (
                <SkillBadge key={idx} gap={gap} />
              ))}
            </div>
          </div>
        )}

        {/* Partial Matches */}
        {partialMatches.length > 0 && (
          <div>
            <div className="flex items-center justify-between mb-3 pt-2 border-t border-gray-100">
              <h3 className="text-sm font-bold text-amber-800 flex items-center gap-1.5">
                <span>⚠ Partial Matches & Experience Bridges</span>
                <span className="bg-amber-100 text-amber-800 text-xs px-2 py-0.5 rounded-full font-extrabold">
                  {partialMatches.length}
                </span>
              </h3>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {partialMatches.map((gap, idx) => (
                <SkillBadge key={idx} gap={gap} />
              ))}
            </div>
          </div>
        )}

        {/* Missing Skills */}
        {missingSkills.length > 0 && (
          <div>
            <div className="flex items-center justify-between mb-3 pt-2 border-t border-gray-100">
              <h3 className="text-sm font-bold text-rose-800 flex items-center gap-1.5">
                <span>❌ Missing Skills & Learning Priorities</span>
                <span className="bg-rose-100 text-rose-800 text-xs px-2 py-0.5 rounded-full font-extrabold">
                  {missingSkills.length}
                </span>
              </h3>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {missingSkills.map((gap, idx) => (
                <SkillBadge key={idx} gap={gap} />
              ))}
            </div>
          </div>
        )}

        {gaps.length === 0 && (
          <p className="text-sm text-gray-500 italic text-center py-4">
            No skill gap data reported for this position.
          </p>
        )}

      </div>
    </div>
  );
};
