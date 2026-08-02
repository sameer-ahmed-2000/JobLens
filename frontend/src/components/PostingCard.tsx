import React from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import type { ScoredPosting } from '../types';
import { extractSkillChips } from '../utils/helpers';
import { checkApplicationExists, saveApplication } from '../services/api';
import { BuildingIcon, ExternalLinkIcon, CheckCircleIcon } from './icons';
import { ApertureRing } from './ApertureRing';

const formatLastSeen = (dateStr?: string): string => {
  if (!dateStr) return '';
  try {
    const date = new Date(dateStr);
    const now = new Date();
    const diffTime = now.getTime() - date.getTime();
    if (diffTime < 0) return 'Just now';
    const diffDays = Math.floor(diffTime / (1000 * 60 * 60 * 24));
    if (diffDays < 1) {
      const diffHours = Math.floor(diffTime / (1000 * 60 * 60));
      if (diffHours < 1) {
        return 'Just now';
      }
      return `${diffHours}h ago`;
    }
    if (diffDays === 1) return 'Yesterday';
    return `${diffDays}d ago`;
  } catch (e) {
    return '';
  }
};

interface PostingCardProps {
  scoredPosting: ScoredPosting;
  isSelected: boolean;
  onSelect: (posting: ScoredPosting) => void;
  disabled?: boolean;
  isHighlighted?: boolean;
}

export const PostingCard: React.FC<PostingCardProps> = ({
  scoredPosting,
  isSelected,
  onSelect,
  disabled = false,
  isHighlighted = false,
}) => {
  const queryClient = useQueryClient();
  const { posting, overall_score, fit_rationale } = scoredPosting;
  const skillChips = extractSkillChips(fit_rationale, posting.title, posting.description);

  const { data: saveCheck } = useQuery({
    queryKey: ['check_saved', posting.id],
    queryFn: () => checkApplicationExists(posting.id),
    staleTime: Infinity,
  });

  const saveMutation = useMutation({
    mutationFn: () => saveApplication(posting.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['check_saved', posting.id] });
      queryClient.invalidateQueries({ queryKey: ['applications'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard_metrics'] });
    },
  });

  const handleCardClick = () => {
    if (!disabled) {
      onSelect(scoredPosting);
    }
  };

  const handleOpenJob = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (posting.url) {
      window.open(posting.url, '_blank', 'noopener,noreferrer');
    }
  };

  return (
    <div
      onClick={handleCardClick}
      className={`viewfinder-bracket-container p-5 rounded-xl border text-left transition-all duration-150 cursor-pointer relative ${
        isHighlighted
          ? 'animate-rack-focus border-signal-amber bg-surface shadow-lg z-10'
          : isSelected
            ? 'viewfinder-active bg-surface border-gray-800 shadow-md'
            : 'bg-surface border-gray-850 hover:border-gray-800 hover:shadow-sm'
      } ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`}
    >
      {/* Corner bracket layout sub-element */}
      <div className="viewfinder-bracket-sub" />

      {/* Top row: Title, Company, Score Badge */}
      <div className="flex items-start justify-between gap-3 mb-2">
        <div className="flex-1 min-w-0">
          <h3 className="text-base font-bold text-text-warm truncate transition-colors">
            {posting.title}
          </h3>
          <div className="flex items-center gap-2 text-xs text-gray-400 mt-0.5 font-mono">
            <span className="flex items-center gap-1 font-medium text-gray-300">
              <BuildingIcon size={13} className="text-gray-500" />
              {posting.company}
            </span>
            {posting.source && (
              <>
                <span className="text-gray-700">•</span>
                <span className="bg-base border border-gray-800 text-gray-400 px-2 py-0.5 rounded text-[10px] font-bold">
                  {posting.source.toUpperCase()}
                </span>
              </>
            )}
            {posting.last_seen_at && (
              <>
                <span className="text-gray-700">•</span>
                <span className="text-gray-500 text-[10px] font-medium" title={`Last confirmed active: ${new Date(posting.last_seen_at).toLocaleString()}`}>
                  ACT: {formatLastSeen(posting.last_seen_at).toUpperCase()}
                </span>
              </>
            )}
          </div>
        </div>

        {/* Custom SVG Aperture Ring Score Visualizer */}
        <ApertureRing score={overall_score * 100} size="normal" className="mt-0.5" />
      </div>

      {/* Skill Chips */}
      <div className="flex flex-wrap gap-1.5 my-3">
        {skillChips.map((chip, idx) => (
          <span
            key={idx}
            className="inline-flex items-center px-2 py-0.5 rounded-md text-[11px] font-semibold bg-base text-gray-300 border border-gray-850 font-mono"
          >
            {chip.toUpperCase()}
          </span>
        ))}
      </div>

      {/* Fit Rationale */}
      <p className="text-xs text-gray-400 line-clamp-2 leading-relaxed mb-3 bg-base/40 p-2.5 rounded-lg border border-gray-850 italic">
        "{fit_rationale || 'Strong overall match based on skill alignment and experience.'}"
      </p>

      {/* Bottom row: Status & Actions */}
      <div className="flex items-center justify-between pt-2 border-t border-gray-850 text-xs font-mono">
        <span className={isSelected ? 'text-focus-confirm font-bold' : 'text-gray-500'}>
          {isSelected ? '◉ VIEW VIEWPORT' : 'SELECT TO RANGE'}
        </span>

        <div className="flex items-center gap-3">
          {saveCheck?.exists ? (
            <span className="inline-flex items-center gap-1 text-focus-confirm font-bold bg-focus-confirm/10 px-2 py-0.5 rounded-md border border-focus-confirm/20 text-[11px]">
              <CheckCircleIcon size={12} />
              SAVED
            </span>
          ) : (
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                if (!saveMutation.isPending) saveMutation.mutate();
              }}
              disabled={saveMutation.isPending}
              className="inline-flex items-center gap-1 text-gray-400 hover:text-focus-confirm font-bold transition-colors disabled:opacity-50 focus:outline-none cursor-pointer"
              title="Save to Workspace"
            >
              ⭐ {saveMutation.isPending ? 'SAVING...' : 'SAVE'}
            </button>
          )}

          {posting.url && (
            <button
              type="button"
              onClick={handleOpenJob}
              className="inline-flex items-center gap-1 text-focus-confirm hover:text-focus-confirm/80 hover:underline font-bold focus:outline-none cursor-pointer"
              title="Open original job posting in new tab"
            >
              <span>OPEN</span>
              <ExternalLinkIcon size={12} />
            </button>
          )}
        </div>
      </div>
    </div>
  );
};
