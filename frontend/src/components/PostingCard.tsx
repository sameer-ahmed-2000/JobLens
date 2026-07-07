import React from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import type { ScoredPosting } from '../types';
import { formatPercentage, extractSkillChips, getScoreColorClass } from '../utils/helpers';
import { checkApplicationExists, saveApplication } from '../services/api';
import { BuildingIcon, ExternalLinkIcon, CheckCircleIcon } from './icons';

interface PostingCardProps {
  scoredPosting: ScoredPosting;
  isSelected: boolean;
  onSelect: (posting: ScoredPosting) => void;
  disabled?: boolean;
}

export const PostingCard: React.FC<PostingCardProps> = ({
  scoredPosting,
  isSelected,
  onSelect,
  disabled = false,
}) => {
  const queryClient = useQueryClient();
  const { posting, overall_score, fit_rationale } = scoredPosting;
  const scoreClass = getScoreColorClass(overall_score);
  const formattedScore = formatPercentage(overall_score);
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
      className={`p-5 rounded-xl border text-left transition-all duration-150 cursor-pointer ${
        isSelected
          ? 'bg-indigo-50/60 border-indigo-500 shadow-md ring-2 ring-indigo-500/20'
          : 'bg-white border-gray-200 hover:border-gray-300 hover:shadow-md'
      } ${disabled ? 'opacity-70 cursor-not-allowed' : ''}`}
    >
      {/* Top row: Title, Company, Score Badge */}
      <div className="flex items-start justify-between gap-3 mb-2">
        <div className="flex-1 min-w-0">
          <h3 className="text-base font-bold text-gray-900 truncate group-hover:text-indigo-600 transition-colors">
            {posting.title}
          </h3>
          <div className="flex items-center gap-2 text-xs text-gray-600 mt-0.5">
            <span className="flex items-center gap-1 font-medium text-gray-700">
              <BuildingIcon size={13} className="text-gray-400" />
              {posting.company}
            </span>
            {posting.source && (
              <>
                <span className="text-gray-300">•</span>
                <span className="bg-gray-100 text-gray-600 px-2 py-0.5 rounded text-[11px] font-medium">
                  {posting.source}
                </span>
              </>
            )}
          </div>
        </div>

        {/* Match Score Badge */}
        <div
          className={`flex items-center px-2.5 py-1 rounded-lg font-extrabold text-sm border shadow-2xs ${scoreClass.badge}`}
        >
          {formattedScore}
        </div>
      </div>

      {/* Skill Chips (Refinement #3) */}
      <div className="flex flex-wrap gap-1.5 my-3">
        {skillChips.map((chip, idx) => (
          <span
            key={idx}
            className="inline-flex items-center px-2 py-0.5 rounded-md text-[11px] font-semibold bg-gray-100 text-gray-700 border border-gray-200"
          >
            {chip}
          </span>
        ))}
      </div>

      {/* Fit Rationale */}
      <p className="text-xs text-gray-600 line-clamp-2 leading-relaxed mb-3 bg-gray-50/80 p-2.5 rounded-lg border border-gray-100 italic">
        "{fit_rationale || 'Strong overall match based on skill alignment and experience.'}"
      </p>

      {/* Bottom row: Status & Actions (Refinement #10) */}
      <div className="flex items-center justify-between pt-2 border-t border-gray-100 text-xs font-medium">
        <span className={isSelected ? 'text-indigo-600 font-semibold' : 'text-gray-400'}>
          {isSelected ? '● Active Selection' : 'Click to analyze gaps'}
        </span>

        <div className="flex items-center gap-3">
          {saveCheck?.exists ? (
            <span className="inline-flex items-center gap-1 text-emerald-600 font-bold bg-emerald-50 px-2 py-0.5 rounded-md border border-emerald-100">
              <CheckCircleIcon size={12} />
              Saved
            </span>
          ) : (
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                if (!saveMutation.isPending) saveMutation.mutate();
              }}
              disabled={saveMutation.isPending}
              className="inline-flex items-center gap-1 text-gray-500 hover:text-indigo-600 font-semibold transition-colors disabled:opacity-50 focus:outline-none"
              title="Save to Workspace"
            >
              ⭐ {saveMutation.isPending ? 'Saving...' : 'Save'}
            </button>
          )}

          {posting.url && (
            <button
              type="button"
              onClick={handleOpenJob}
              className="inline-flex items-center gap-1 text-indigo-600 hover:text-indigo-800 hover:underline font-semibold focus:outline-none"
              title="Open original job posting in new tab"
            >
              <span>Open Job</span>
              <ExternalLinkIcon size={12} />
            </button>
          )}
        </div>
      </div>
    </div>
  );
};
