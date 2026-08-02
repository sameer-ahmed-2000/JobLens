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
      <div className="bg-surface rounded-2xl border border-gray-800 p-6">
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
    return (
      <EmptyState
        type="report"
        title="RESOLVING AI FOCUS..."
        message="Please wait while LangGraph filters the signal and performs gap analysis."
      />
    );
  }

  const { job_title, company, gaps = [], overall_fit_summary, overall_recommendation } = report;
  const summaryText = overall_fit_summary || overall_recommendation;

  // Group skills
  const strongMatches = gaps.filter((g) => g.classification === 'have');
  const partialMatches = gaps.filter((g) => g.classification === 'partial');
  const missingSkills = gaps.filter((g) => g.classification === 'missing');

  const handleOpenOriginal = () => {
    if (selectedPosting?.posting.url) {
      window.open(selectedPosting.posting.url, '_blank', 'noopener,noreferrer');
    }
  };

  return (
    <div className="bg-surface rounded-2xl border border-gray-800 shadow-md p-6 space-y-6 max-h-[800px] overflow-y-auto pr-2 font-body text-text-warm">
      
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-gray-850 pb-4">
        <div>
          <h2 className="text-xl font-extrabold text-text-warm font-display tracking-tight">{job_title}</h2>
          <div className="flex items-center gap-1.5 text-sm text-gray-400 mt-1 font-mono">
            <BuildingIcon size={16} className="text-gray-500" />
            <span>{company.toUpperCase()}</span>
            {selectedPosting?.posting.source && (
              <span className="bg-base border border-gray-850 text-gray-450 px-2 py-0.5 rounded text-[10px] font-bold">
                {selectedPosting.posting.source.toUpperCase()}
              </span>
            )}
          </div>
        </div>

        <div className="flex items-center gap-3 shrink-0 self-start sm:self-center">
          {selectedPosting?.posting.id && (
            saveCheck?.exists ? (
              <span className="inline-flex items-center gap-1.5 px-3 py-2 bg-focus-confirm/10 text-focus-confirm rounded-xl text-xs font-bold border border-focus-confirm/20 font-mono">
                <CheckCircleIcon size={14} />
                <span>SAVED TO WORKSPACE</span>
              </span>
            ) : (
              <button
                type="button"
                onClick={() => !saveMutation.isPending && saveMutation.mutate()}
                disabled={saveMutation.isPending}
                className="inline-flex items-center gap-1.5 px-3 py-2 bg-base text-gray-300 hover:text-focus-confirm rounded-xl text-xs font-bold border border-gray-800 transition-colors cursor-pointer focus:outline-none disabled:opacity-50 font-mono"
              >
                <span>⭐ {saveMutation.isPending ? 'SAVING...' : 'SAVE JOB'}</span>
              </button>
            )
          )}

          {selectedPosting?.posting.url && (
            <button
              type="button"
              onClick={handleOpenOriginal}
              className="inline-flex items-center gap-1.5 px-3 py-2 bg-focus-confirm/10 text-focus-confirm hover:bg-focus-confirm/20 border border-focus-confirm/20 rounded-xl text-xs font-bold transition-all cursor-pointer focus:outline-none font-mono"
            >
              <span>OPEN ORIGINAL</span>
              <ExternalLinkIcon size={14} />
            </button>
          )}
        </div>
      </div>

      {/* Confidence Card (Aperture-themed inside) */}
      <ConfidenceCard report={report} />

      {/* AI Fit Summary Narrative */}
      {summaryText && (
        <div className="bg-base/30 rounded-xl p-4 border border-gray-850 shadow-sm font-body">
          <div className="flex items-center space-x-2 text-focus-confirm font-bold text-xs uppercase tracking-wider mb-2 font-mono">
            <SparklesIcon size={16} className="text-focus-confirm" />
            <span>AI LENS SIGNAL ANALYSIS SUMMARY</span>
          </div>
          <p className="text-sm text-gray-300 leading-relaxed font-medium">
            {summaryText}
          </p>
        </div>
      )}

      {/* Grouped Skills List */}
      <div className="space-y-6 pt-2">
        
        {/* Strong Matches */}
        {strongMatches.length > 0 && (
          <div>
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-xs font-bold text-focus-confirm tracking-wider uppercase font-mono flex items-center gap-1.5">
                <span>✅ RESOLVED SIGNALS (STRONG)</span>
                <span className="bg-focus-confirm/10 text-focus-confirm text-xs px-2 py-0.5 rounded-full font-extrabold border border-focus-confirm/20">
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
            <div className="flex items-center justify-between mb-3 pt-2 border-t border-gray-850">
              <h3 className="text-xs font-bold text-signal-amber tracking-wider uppercase font-mono flex items-center gap-1.5">
                <span>⚠ DRIFTING SIGNALS (PARTIAL)</span>
                <span className="bg-signal-amber/10 text-signal-amber text-xs px-2 py-0.5 rounded-full font-extrabold border border-signal-amber/20">
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
            <div className="flex items-center justify-between mb-3 pt-2 border-t border-gray-850">
              <h3 className="text-xs font-bold text-alert-red tracking-wider uppercase font-mono flex items-center gap-1.5">
                <span>❌ OUT OF FOCUS (MISSING GAPS)</span>
                <span className="bg-alert-red/10 text-alert-red text-xs px-2 py-0.5 rounded-full font-extrabold border border-alert-red/20">
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
          <p className="text-sm text-gray-500 italic text-center py-4 font-mono">
            NO GAP PROFILE SIGNALS CAPTURED.
          </p>
        )}

      </div>
    </div>
  );
};
